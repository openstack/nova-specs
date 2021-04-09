..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Integration With Off-path Network Backends
==========================================

https://blueprints.launchpad.net/nova/+spec/integration-with-off-path-network-backends

Off-path SmartNIC DPUs introduce an architecture change where
network agents responsible for NIC switch configuration and representor
interface plugging run on a separate SoC with its own CPU, memory and that runs
a separate OS kernel. The side-effect of that is that hypervisor hostnames no
longer match SmartNIC DPU hostnames which are seen by ovs-vswitchd and OVN [3]_
agents while the existing port binding code relies on that. The goal of this
specification is to introduce changes necessary to extend the existing hardware
offload code to cope with the hostname mismatch and related design challenges
while reusing the rest of the code. To do that, PCI(e) add-in card tracking is
introduced for boards with unique serial numbers so that it can be used to
determine the correct hostname of a SmartNIC DPU which is responsible for a
particular VF. Additionally, more information is suggested to be passed in the
"binding:profile" during a port update to facilitate representor port plugging.


Problem description
===================

Terminology
-----------

* Data Processing Unit (DPU) - an embedded system that includes a CPU, a NIC
  and possibly other components on its board which integrates with the main
  board using some I/O interconnect (e.g. PCIe);
* Off-path SmartNIC DPU architecture [1]_ [2]_ - an architecture where NIC
  cores are responsible for programming a NIC Switch and are bypassed when
  rules programmed into the NIC Switch are enough to make a decision on where
  to deliver packets. Normally, NIC cores only participate in packet forwarding
  for the "slow path" only and the "fast path" is handled in hardware like an
  ASIC;
* On-path SmartNIC DPU architecture [1]_ [2]_ - an architecture where NIC cores
  participate in processing of every packet going through the NIC as a whole.
  In other words, NIC cores are always on the "fast path" of all packets;
* NIC Switch (or eSwitch) - a programmable embedded switch present in various
  types of NICs (SR-IOV-capable NICs, off-path SmartNICs). Typically relies
  on ASICs for packet processing;
* switchdev [4]_ - in-kernel driver model for switch devices which offload the
  forwarding (data) plane from the kernel.
* Representor ports [5]_ - a concept introduced in the switchdev model which
  models netdevs representing switch ports. This applies to NIC switch ports
  (which can be physical uplink ports, PFs or VFs);
* devlink [6]_ - a kernel API to expose device information and resources not
  directly related to any device class, such as chip-wide/switch-ASIC-wide
  configuration;
* PCI/PCIe Vital Product Data (VPD) - a standard capability exposed by PCI(e)
  endpoints which, among other information, includes a unique serial number
  (read-only, persistent, factory-generated) of a card shared by all functions
  exposed by it. Present in PCI local bus 2.1+ and PCIe 4.0+ specifications.

Detailed overview
-----------------

Cross-project changes have been made over time to support SR-IOV VF allocation
and VF allocation in the context of supporting OVS hardware offload [7]_ with
switchdev-capable NICs. However, further work is needed in order to support
off-path SmartNIC DPUs which also expose PCI(e) functions to the hypervisor
hosts.

When working with ports of type "direct", instance creation involves several
key steps, including:

* Creating the necessary context based on a client request (including PCI
  device requests, e.g. based on "direct" ports associated with an instance
  creation request or extra specs of a flavor);
* Selecting the right host for the instance to be scheduled;

  * In the switchdev-capable NIC case: based on availability of devices with
    the "switchdev" capability of PciDevices recorded in the Nova DB;
* Building and running the instance, which involves:

  * Claiming PCI resources via the ResourceTracker at the target host based on
    InstancePCIRequests created beforehand;
  * Building other resource requests and updating Neutron port information,
    specifically:

      * binding_host_id with the hypervisor hostname;
      * binding:profile details with PCI device information,
        namely: pci_vendor_info, pci_slot, physical_network;

* Network device assignment for the newly created instance and vif plugging

  * in the switchdev-capable NIC case this involves plugging a VF representor
    port into the right OVS bridge;
  * programming the necessary flows into the NIC Switch.

The rest of the description will focus on illustrating why this process needs
improvements to support off-path SmartNIC DPUs.

Off-path SmartNIC DPUs provide a dedicated CPU for NIC Switch programming on
which a dedicated OS is set to run which is separate from the OS running on the
main board. A system with one SmartNIC in a multi-CPU system with PCIe
bifurcation used for the add-in card is shown below::

                          ┌──────────────────────────────┐
                          │  Main host (hypervisor)      │
                          │    ┌──────┐      ┌──────┐    │
                          │    │ CPU1 │      │ CPU2 │    │
                          │    │ RC1  │      │ RC2  │    │
                          │    └───┬──┘      └───┬──┘    │
                          │        │             │       │
                          └────────┼─────────────┼───────┘
                                   │             │
                                   │             │
                               ┌───┴────┐    ┌───┴────┐
             IO interconnect 1 │PF NUMA1│    │PF NUMA2│ IO interconnect 2
                  (PCIe)       │VFs     │    │VFs     │    (PCIe)
                               └────┬───┘    └───┬────┘
                                    │            │
   ┌────────────────────────────────┼────────────┼──────────────────────┐
   │SmartNIC DPU Board          ▲   │            │    ▲                 │
   │                            │   │            │    │  Fast path      │
   │      ┌─────────────┐         ┌─┴────────────┴─┐                    │
   │      │ Application │e.g. PCIe│   NIC Switch   │     ┌────────────┐ │
   │      │    CPU      ├─────────┤      ASIC      ├─────┤uplink ports│ │
   │      │    RC3      │         ├────────────────┤     └────────────┘ │
   │ ┌────┴──────┬──────┘   ◄──── │ Management CPU │                    │
   │ │OOB Port   │       Slow path│    Firmware    │                    │
   │ └───────────┘                └────────────────┘                    │
   │                                                                    │
   │                                                                    │
   └────────────────────────────────────────────────────────────────────┘

With off-path SmartNIC DPUs, if a NIC Switch has the necessary flows
programmed and an incoming packet matches those flows, it is delivered to the
destination over the fast path bypassing the "Application CPU". Otherwise, the
packet is processed in software at the Application CPU and then forwarded to
the destination.

There are more sophisticated scenarios as well:

* Two or more SmartNIC DPUs per server attached to different NUMA nodes;
* A blade system with managed PCIe switches providing SR-IOV function sharing
  of PFs/VFs of the same add-in-card to different compute servers:

  * MR-SR-IOV/PCIe Shared IO [8]_.

Networking agents (e.g. ovs-vswitchd and ovn-controller) are expected to run
on the SmartNIC OS which will have a different hostname from the hypervisor
OS which results in a mismatch during port binding (more specifically to the
OVS case, the external_ids["hostname"] field in the Open_vSwitch table differs
from the hypervisor hostname). Likewise, representor plugging and flow
programming happens on the SmartNIC host, not on the hypervisor host. As a
result, Nova (with the help of os-vif) can no longer be responsible for VIF
plugging in the same way. For instance, compared to the OVS hardware offload
scenario, OVS bridges and port representors are no longer exposed to the
hypervisor host OS. In summary, no networking agents are present on the
hypervisor host in this architecture. In this scenario the noop os-vif
plugin can be used to avoid explicit actions at the Nova host side, while
a different service at the SmartNIC DPU side will be responsible for
plugging of representors into the right bridge. However, Nova is still
responsible for passing the device information to the virt driver so that
it can be used when starting an instance.

Since Nova and networking agents run on different hosts, there needs to be a
set of interactions in order to:

* Schedule an instance to a host where a VF with the necessary capability is
  present;
* Select a suitable VF at the hypervisor host side and create a PCI device
  claim for it;
* Run the necessary logic as described in the Neutron specification [19]_.

The SmartNIC DPU selection in particular becomes an issue to address due to
the following:

* PF and VF mac addresses can be reprogrammed so they cannot be used as
  reliable persistent identifiers to refer to SmartNIC DPUs;
* PCI(e) add-in cards themselves do not have entries in sysfs but PCI(e)
  endpoints do;
* When a SmartNIC DPU uses PCIe to access the PCIe endpoints exposed by the
  NIC, hypervisor hosts and SmartNIC DPU hosts do not see the same set of PCIe
  functions as they see **isolated PCIe topologies**. Each host enumerates the
  PCIe topology it is able to observe. While the same NIC is exposed to both
  topologies, the set of functions and config spaces observed by hosts differs.

  * Note that SmartNIC DPUs may have different ways of accessing a
    switchdev-capable NIC: via PCIe, a platform device or other means of I/O.
    The hypervisor host would see PCIe endpoints regardless of that but relying
    on PCI addresses in the implementation to match functions and their
    representors is not feasible.

In order to track SmartNIC DPUs and associations of PFs/VFs with them, there
is a need for a unique and persistent identifier that is discoverable from both
hypervisor hosts and SmartNIC DPU hosts. PCI (2.1+) and PCIe specifications
define the Vital Product Data (VPD) capability which includes a serial number
field which is defined to be unique and read-only for a given add-in card. All
PFs and VFs exposed by a PCI(e) card share the same VPD data (whether it is
exposed on PFs only or VFs is firmware-specific). However, this field is
currently not gathered by the virt drivers or recorded by the Nova
PciResourceTracker (note: SmartNIC DPUs from several major vendors are known
to provide VPD with serial numbers filled in and visible from hypervisor hosts
and SmartNIC DPU hosts).

The serial number information exposed via PCI(e) VPD is also available via
devlink-info - there are no ties to a particular IO standard such as PCI(e) so
other types of devices (e.g. platform devices) could leverage this as well.

For the PCI(e) use-case specifically, there is a need to distinguish the
PFs/VFs that simply expose a VPD from the ones that also need to be associated
with SmartNIC DPUs. In order to address that, PCI devices can be tagged using
the ``pci_passthrough_whitelist`` to show that they are associated with a
SmartNIC DPU.

Reliance on the "switchdev" capability (persisted into the extra_info column
of pci_devices table) is also problematic since the PFs exposed to a hypervisor
host by the NIC on a SmartNIC DPU board do not provide access to the NIC
Switch - it is not possible to query whether the NIC Switch is in the "legacy"
or "switchdev" mode from the hypervisor side. This has to do with NIC internals
and the way the same NIC is exposed to hypervisor host CPUs and the
"application CPU" on the add-in card. Devlink documentation in the kernel
provides an example of that with two PCIe hierarchies: [9]_.

Use Cases
---------

* The main use-case is to support allocation of VFs associated with off-path
  SmartNIC DPUs and their necessary configuration at the SmartNIC DPU side;
* From the operator perspective, being able to use multiple SmartNIC DPUs per
  host is desirable.

Desired Outcome Overview
------------------------

The following points summarize the desired outcome:

* **Off-path** SmartNIC DPUs from various vendors where networking control
  plane components are meant to run on SmartNIC DPU hosts;
* Reuse of the existing VNIC type "smart-nic" (VNIC_SMARTNIC);
* A new tag for PCI devices to indicate that a device is associated with a
  SmartNIC DPU: ``remote_managed=True|False``;
* Support for multiple SmartNIC DPUs per host;
* No expectation that the hypervisor host will be responsible for placing an
  image onto a SmartNIC DPU directly;

  * a security boundary is assumed between the main board host and the
    SmartNIC/DPU;
  * Indirect communication between Nova and software running on the SmartNIC
    DPU;
* Focus on the libvirt virt driver for any related changes initially but make
  the design generic for other virt drivers to follow;

Configuration and deployment of the SmartNIC DPU and its control plane software
on it is outside the scope of this spec.

Proposed change
===============

The scope of this change is in Nova but it is a part of a larger effort that
involves OVN and Neutron.

Largely, the goal is to gather the information necessary for representor
plugging via Nova and pass it to the right place.

In case PCIe used at the SmartNIC DPU for NIC access, both the hypervisor host
and the SmartNIC DPU host that belong to the same physical machine can see
PCI(e) functions exposed by the controllers on the same card, therefore, they
can see the same unique add-in-card serial number exposed via VPD. For other
types of I/O, devlink-info can be relied upon to retrieve the board serial
(if available). This change, however, is focused on the PCI and will use PCI
VPD info as seen by Libvirt.

Nova can store the information about the observed cards and use it later during
the port update process to affect the selection of a SmartNIC DPU host that
will be used for representor plugging.

Device tags in the ``pci_passthrough_whitelist`` will tell Nova which PCI
vendor and device IDs refer to functions belonging to a SmartNIC DPU.

The following needs to be addressed in the implementation:

* Store VPD info from the PCI(e) capability for each PciDevice;

  * card_serial_number - a string of up to 255 bytes since PCI and PCIe specs
    use a 1-byte length field for the SN;
  * ``extra_info: '{"capabilities": "vpd": {"card_serial_number": "<sn>"}]'}``;
* Retrieval of the PCI card serial numbers stored in PCI VPD as presented in
  node device XML format exposed by Libvirt for PFs and VFs.

  * Whether or not PCI VPD is exposed for VFs as well as PFs is specific to
    the device firmware (sometimes there is an NVRAM option to enable to expose
    this data on VFs in addition to PFs) - it might be useful to populate
    VF-specific information based on the PF information in case PCI VPD is not
    exposed for VFs;
* Store the card serial number information (if present) in the PciDevice
  extra_info column under the "vpd" capability;
* Extend the ``pci_passthrough_whitelist`` handling implementation to take
  ``remote_managed=True|False`` tag into account;
* For each function added to an instance, collect a PF MAC and VF logical
  number as seen by the hypervisor host and pass them to Neutron along with
  the card serial number during port update requests that happen during
  instance creation (see the relevant section below for more details);

  * Note that if VFIO is used, this specification assumes that the ``vfio-pci``
    driver will only be bound to VFs, not PFs and that PFs will be utilized for
    hypervisor host purposes (e.g. connecting to the rest of the control
    plane);
  * Storing of VF logical number and PF MAC could be in ``extra_info`` could
    be done to avoid extra database lookups;
* Add logic to handle ports of type ``VNIC_SMARTNIC`` ("smart-nic");
* Add a new Nova service version constant (``SUPPORT_VNIC_TYPE_SMARTNIC``) and
  an instance build-time check (in ``_validate_and_build_base_options``) to
  make sure that instances with this port type are scheduled only when all
  compute services in all cells have this service version;

  * The service version check will need to be triggered only for network
    requests containing port_ids that have ``VNIC_TYPE_SMARTNIC`` port type.
    Nova will need to learn to query the port type by its ID to perform that
    check;
* Add a new compute driver capability called ``supports_remote_managed_ports``
  and a respective ``COMPUTE_REMOTE_MANAGED_PORTS`` trait to ``os-traits``;

  * Only the Libvirt driver will be set to have this trait since this is the
    first driver to support ``remote_managed`` ports;
* Implement a prefilter that will check for the presence of port ids that have
  ``VNIC_TYPE_SMARTNIC`` port type and add the ``COMPUTE_REMOTE_MANAGED_PORTS``
  to the request spec in this case. This will make sure that instances are
  scheduled on compute nodes that have the necessary virt driver supporting
  remote managed ports enabled;
* Add stubs in the Nova API to prevent the following lifecycle operations for
  instances with VNIC_TYPE_SMARTNIC ports:

  * Resize;
  * Shelve;
  * Live migrate;
  * Evacuate;
  * Suspend;
  * Attach/detach a VNIC_TYPE_SMARTNIC port;
  * Rebuild;
* Extend ``VIF.has_bind_time_event`` in Nova to return True for
  VNIC_TYPE_SMARTNIC ports;
* Handle early arrival of ``network-vif-plugged`` in the Libvirt virt driver
  code for ``VNIC_TYPE_SMARTNIC`` ports by extending the
  ``_get_neutron_events`` function to rely on ``VIF.has_bind_time_event`` for
  filtering.

Identifying Port Representors
-----------------------------

This specification makes an assumption that Neutron will be extended to act
upon the additional information passed from Nova. The following set of
information is proposed to be sent during a port update:

* card serial number;
* PF mac address (seen both by the hypervisor host and the SmartNIC DPU host);
* VF logical number.

This is needed to do the following multiplexing decisions:

* Determining the right SmartNIC DPU hostname associated with a chosen VF.
  There may be multiple SmartNIC DPUs per physical host. This can be done by
  associating a card serial number with a SmartNIC DPU hostname at the Neutron
  & OVN side (Nova just needs to pass it in a port update);
* Picking the right NIC Switch at the SmartNIC DPU side. PF logical numbers
  are tied to controllers [9]_ [11]_. Typically there is a single NIC and
  NIC Switch in a SmartNIC but there is no guarantee that there will not be a
  device with multiple of those. As a result, just passing a PF logical number
  from the hypervisor host is not enough to determine the right NIC Switch.
  A PF MAC address could be used as a way to get around the lack of visibility
  of a controller at the hypervisor host side;
* Choosing the right VF representor - a VF logical number tied to a particular
  PF.

PF and controller numbers seen by the SmartNIC DPU are not visible from the
hypervisor host since it does not see the NIC Switch. To further expand on
this, the devlink [10]_ infrastructure in the kernel supports different port
flavors (quoted descriptions originate from linux/uapi/linux/devlink.h [12]_):

* physical - "any kind of a port physically facing the user". PFs on the
  hypervisor side and uplink ports on the SmartNIC DPU will have this flavor;
* virtual - "any virtual port facing the user". VFs on the hypervisor side will
  have this flavor;
* pcipf - an NIC Switch port representing a port of PCI PF;
* pcivf - an NIC Switch port representing a port of PCI VF.

Linux kernel exposes logical numbers via devlink differently for different
port flavors:

* physical and virtual flavors: via DEVLINK_ATTR_PORT_NUMBER - this value is
  driver-specific and depends on how a device driver populates those
  attributes.
* pcipf and pcivf flavors: DEVLINK_ATTR_PORT_PCI_PF_NUMBER and
  DEVLINK_ATTR_PORT_PCI_VF_NUMBER attributes.

For example, for a NIC with 2 uplink ports with sriov_numvfs set to 4 for
both uplink ports at the hypervisor side, the set of interfaces as shown by
``devlink port`` will be as follows::

  pci/0000:05:00.0/1: type eth netdev enp5s0f0 flavour physical port 0
  pci/0000:05:00.1/1: type eth netdev enp5s0f1 flavour physical port 1
  pci/0000:05:02.3/1: type eth netdev enp5s0f1np0v0 flavour virtual port 0
  pci/0000:05:02.4/1: type eth netdev enp5s0f1np0v1 flavour virtual port 0
  pci/0000:05:02.5/1: type eth netdev enp5s0f1np0v2 flavour virtual port 0
  pci/0000:05:02.6/1: type eth netdev enp5s0f1np0v3 flavour virtual port 0
  pci/0000:05:00.3/1: type eth netdev enp5s0f0np0v0 flavour virtual port 0
  pci/0000:05:00.4/1: type eth netdev enp5s0f0np0v1 flavour virtual port 0
  pci/0000:05:00.5/1: type eth netdev enp5s0f0np0v2 flavour virtual port 0
  pci/0000:05:00.6/1: type eth netdev enp5s0f0np0v3 flavour virtual port 0

Notice the virtual port indexes are all set to 0 - in this example the device
driver does not provide any indexing information via devlink attributes for
"virtual" ports.

SmartNIC DPU host ``devlink port`` output::

  pci/0000:03:00.0/262143: type eth netdev p0 flavour physical port 0
  pci/0000:03:00.0/196608: type eth netdev pf0hpf flavour pcipf pfnum 0
  pci/0000:03:00.0/196609: type eth netdev pf0vf0 flavour pcivf pfnum 0 vfnum 0
  pci/0000:03:00.0/196610: type eth netdev pf0vf1 flavour pcivf pfnum 0 vfnum 1
  pci/0000:03:00.0/196611: type eth netdev pf0vf2 flavour pcivf pfnum 0 vfnum 2
  pci/0000:03:00.0/196612: type eth netdev pf0vf3 flavour pcivf pfnum 0 vfnum 3
  pci/0000:03:00.1/327679: type eth netdev p1 flavour physical port 1
  pci/0000:03:00.1/262144: type eth netdev pf1hpf flavour pcipf pfnum 1
  pci/0000:03:00.1/262145: type eth netdev pf1vf0 flavour pcivf pfnum 1 vfnum 0
  pci/0000:03:00.1/262146: type eth netdev pf1vf1 flavour pcivf pfnum 1 vfnum 1
  pci/0000:03:00.1/262147: type eth netdev pf1vf2 flavour pcivf pfnum 1 vfnum 2
  pci/0000:03:00.1/262148: type eth netdev pf1vf3 flavour pcivf pfnum 1 vfnum 3

So the logical numbers for representor flavors are correctly identified at the
SmartNIC DPU but are not visible at the hypervisor host.

VF PCI addresses at the hypervisor side are calculated per the PCIe and SR-IOV
specs using the PF PCI address, "First VF Offset" and "VF Stride" values and
the logical per-PF numbering is maintained by the kernel and exposed via sysfs.
Therefore, we can take logical VF numbers from the following sysfs entries::

  /sys/bus/pci/devices/{pf_pci_addr}/virtfn<vf_logical_num>

They can also be accessed via::

  /sys/bus/pci/devices/{vf_pci_addr}/physfn/virtfn<vf_logical_num>

Finding the right entry via a physfn symlink can be done by resolving virtfn
symlinks one by one and comparing the result with the ``vf_pci_addr`` that
is of interest.

As for finding the right PF representor by a MAC address of hypervisor host PF,
it depends on the availability of information about a mapping of a hypervisor
PF MAC to a PF representor MAC.

VF logical number and PF MAC information can be extracted at runtime right
before a port update since those are done by the Nova Compute manager during
instance creation. Alternatively, it can be stored in the database in
``extra_info`` of a PciDevice.

VF VLAN Programming Considerations
----------------------------------

Besides NIC Switch capability not being exposed to the hypervisor host,
SmartNIC DPUs also prevent VLAN programming by for VFs, therefore, operations
like the following will fail (see, [27]_ for the example driver code causing
it)::

  sudo ip link set enp130s0f0 vf 2 vlan 0 mac de:ad:be:ef:ca:fe
  RTNETLINK answers: Operation not permitted

In this case the VF MAC programming is allowed by the driver, however, VLAN
programming is not.

Nova does not tell Libvirt to program VLANs for VIFs with
``VIFHostDeviceDevType.ETHERNET`` [28]_ (it explicitly passes ``None`` for the
vlan parameter to [29]_) which are going to be used in the implementation.

Libvirt only programs a specific VLAN number for hostdev ports [30]_
(``VIR_DOMAIN_NET_TYPE_HOSTDEV`` [31]_) if one is provided via device XML and
otherwise tries to clear a VLAN by passing a VLAN ID 0 to the ``RTM_SETLINK``
operation (handing of ``EPERM`` in this case is addressed by [22]_).

Nova itself only programs a MAC address and VLAN for ``VNIC_TYPE_MACVTAP``
ports [32]_ [33]_, therefore, the implementation of this specification does
not need to introduce any changes for that.

Alternatives
------------

The main points that were considered when looking for alternatives:

* Code reuse: a lot of work went into the hardware offload implementation and
  extending it without introducing new services and projects would be
  preferable;
* Security and isolation: SmartNICs DPUs are isolated from the hypervisor host
  intentionally to create a security boundary between the hypervisor services
  and network services. Creating agents to drive provisioning and configuration
  from the hypervisor itself would remove that benefit;
* NIC Switch configuration and port plugging: services running on a
  SmartNIC DPU need to participate in port representor plugging and NIC Switch
  programming which is not necessarily specific to Nova or even OpenStack.
  Other infrastructure projects may benefit from that as well so the larger
  effort needs to concentrate on reusability. This is why possible
  introduction of SmartNIC DPU-level services specific to OpenStack needs to be
  avoided (i.e. it is better to extend OVN to do that and handle VF plugging at
  the Nova side).

One alternative approach involves tracking cards using a separate service with
its own API and possibly introducing a different VNIC type: this does not have
a benefit of code reuse and requires another service to be added and integrated
with Nova and Neutron at minimum. Evolving the work that was done to enable
hardware offloaded ports seems like a more effective way to address this
use-case.

Supporting one SmartNIC DPU per host initially and extending it at a later
point has been discarded due to difficulties in the data model extension.

Data model impact
-----------------

PciDevices get additional information associated with them without affecting
the DB model:

* a "vpd" capability which stores the information available in the PCI(e) VPD
  capability (initially, just the board serial number but it may be extended at
  a later point if needed).

Periodic hypervisor resource updates will add newly discovered PciDevices and
get the associated card serial number information. However, old devices will
not get this information without explicit action.


REST API impact
---------------

N/A

Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

N/A

Performance Impact
------------------

* Additional steps need to be performed to extract serial number information of
  PCI(e) add-in cards from the PFs and VFs exposed by them.

Other deployer impact
---------------------

Reading PCI(e) device VPD is supported since kernel 2.6.26
(see kernel commit 94e6108803469a37ee1e3c92dafdd1d59298602f) and devices
that support PCI local bus 2.1+ (and any PCIe revision) use the same binary
format for it. The VPD capability is optional per the PCI(e) specs, however,
production SmartNICs/DPUs observed so far do contain it (engineering samples
may not have VPD so only use generally available hardware for this).

During the deployment planning it is also important to take control traffic
paths into account. Nova compute is expected to pass information to Neutron
for port binding via the control network: Neutron is then responsible for
interacting with OVN which then propagates the necessary information to
ovn-controllers running at SmartNIC DPU hosts. Also, Placement service updates
from hypervisor nodes happen over the control network. This may happen via
dedicated ports programmed on the eSwitch which needs to be done via some form
of a deployment automation. Alternatively, LoMs on many motherboards may be
used for that communication but the overall goal is to remove the need for
that. The OOB port on the SmartNIC DPU (if present) may be used for control
communication too but it is assumed that it will be used for PXE boot of an OS
running on the application CPU and for initial NIC Switch configuration. Which
interfaces to use for control traffic is outside of the scope of this
specification and the purpose of this comment is to illustrate the possible
indirect communication paths between components running on different hosts
within the same physical machine and remote services::


                           ┌────────────────────────────────────┐
                           │  Hypervisor                        │    LoM Ports
                           │  ┌───────────┐       ┌───────────┐ │   (on-board,
                           │  │ Instance  │       │  Nova     │ ├──┐ optional)
                           │  │ (QEMU)    │       │ Compute   │ │  ├─────────┐
                           │  │           │       │           │ ├──┘         │
                           │  └───────────┘       └───────────┘ │            │
                           │                                    │            │
                           └────────────────┬─┬───────┬─┬──┬────┘            │
                                            │ │       │ │  │                 │
                                            │ │       │ │  │ Control Traffic │
                               Instance VF  │ │       │ │  │ PF associated   │
                                            │ │       │ │  │ with an uplink  │
                                            │ │       │ │  │ port or a VF.   │
                                            │ │       │ │  │ (used to replace│
                                            │ │       │ │  │  LoM)           │
       ┌────────────────────────────────────┼─┼───────┼─┼──┼─┐               │
       │   SmartNIC DPU Board               │ │       │ │  │ │               │
       │                                    │ │       │ │  │ │               │
       │  ┌──────────────┐ Control traffic  │ │       │ │  │ │               │
       │  │   App. CPU   │ via PFs or VFs  ┌┴─┴───────┴─┴┐ │ │               │
       │  ├──────────────┤  (DC Fabric)    │             │ │ │               │
       │  │ovn-controller├─────────────────┼─┐           │ │ │               │
       │  ├──────────────┤                 │ │           │ │ │               │
       │  │ovs-vswitchd  │     Port        │ │NIC Switch │ │ │               │
       │  ├──────────────┤   Representors  │ │  ASIC     │ │ │               │
       │  │    br-int    ├─────────────────┤ │           │ │ │               │
       │  │              ├─────────────────┤ │           │ │ │               │
       │  └──────────────┘                 │ │           │ │ │               │
       │                                   │ │           │ │ │               │
       │                                   └─┼───┬─┬─────┘ │ │               │
     ┌─┴──────┐Initial NIC Switch            │   │ │       │ │               │
    ─┤OOB Port│configuration is done via     │   │ │uplink │ │               │
     └─┬──────┘the OOB port to create        │   │ │       │ │               │
       │       ports for control traffic.    │   │ │       │ │               │
       └─────────────────────────────────────┼───┼─┼───────┼─┘               │
                                             │   │ │       │                 │
                                          ┌──┼───┴─┴───────┼────────┐        │
                                          │  │             │        │        │
                                          │  │   DC Fabric ├────────┼────────┘
                                          │  │             │        │
                                          └──┼─────────────┼────────┘
                                             │             │
                                             │         ┌───┴──────┐
                                             │         │          │
                                         ┌───▼──┐  ┌───▼───┐ ┌────▼────┐
                                         │OVN SB│  │Neutron│ │Placement│
                                         └──────┘  │Server │ │         │
                                                   └───────┘ └─────────┘

Processes on the hypervisor host would use the PF associated with an uplink
port or a bond (or VLAN interfaces on top of those) in order to communicate
with control processes.

SmartNIC DPUs themselves do not typically have a BMC themselves and draw
primary power from a PCIe slot so their power lifecycle is tied to the
main board lifecycle. This should be taken into consideration when performing
power off/power on operations on the hypervisor hosts as it will affect
services running on the SmartNIC DPU (a reboot of the hypervisor host should
not).

Developer impact
----------------

The current specification targets the libvirt driver - other virt drivers
need to gain similar functionality to discover card serial numbers if they
want to support the same workflow.

Upgrade impact
--------------

Nova Service Versions
~~~~~~~~~~~~~~~~~~~~~

The ``Proposed Change`` section discusses adding a service version constant
(``SUPPORT_VNIC_TYPE_SMARTNIC``) and an instance build-time check across all
cells. For operators, the upgrade impact will be such that this feature will
not be possible to use until all Nova Compute services will be upgraded to
support this service version.

Neutron integration
~~~~~~~~~~~~~~~~~~~

This section focuses on operational concerns with regards to Neutron being able
to support instances booted with the ``VNIC_TYPE_SMARTNIC`` port type.

At the time of writing, only the OVS mechanism driver supports [13]_
``VNIC_TYPE_SMARTNIC`` ports but only if a particular configuration option is
set in the Neutron OpenvSwitch Agent (which was done for Ironic purposes, not
Nova [14]_).

Therefore, in the absence of mechanism drivers that would support ports of that
type or when the mechanism driver is not configured to handle ports of that
type, port binding will fail.

This change also relies on the use of ``binding:profile`` [15]_ which
does not have a strict format and documented as::

  A dictionary that enables the application running on the specific host to
  pass and receive vif port information specific to the networking back-end.
  The networking API does not define a specific format of this field.

Therefore, no Neutron API changes are needed to support additional attributes
specified passed by Nova in port updates.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dmitriis

Other contributors:
  fnordahl, james-page

Feature Liaison
---------------

Liaison Needed

Work Items
----------

* Support the PCI ``vpd`` capability exposed by Libvirt via node device XML;
* Implement modifications to store the card serial number information
  associated with PciDevices;
* Modify the ``pci_passthrough_whitelist`` to include the ``remote_managed``
  tag handling;
* Add handling for ``VNIC_SMARTNIC`` VNIC type;
* Implement VF logical number extraction based on virtfn entries in sysfs:
  ``/sys/bus/pci/devices/{pf_pci_addr}/virtfn<vf_logical_num>``;
* Extend the port update procedure to pass an add-in-card serial number,
  PF mac and VF logical number to Neutron in the ``binding:profile`` attribute;
* Implement service version checking for the added functionality;
* Implement a prefilter to avoid scheduling instances to nodes that do not
  support the right compute capability;
* Unit testing coverage;
* Function tests for the added functionality;
* Integration testing with other projects.


Dependencies
============

In order to make this useful overall there are additional cross-project
changes required. Specifically, to make this work with OVN:

* ovn-controller needs to learn how to plug representors into correct bridges
  at the SmartNIC DPU node side since the os-vif-like functionality to hook VFs
  up is still needed;

  * Representor plugging and related OVN changes: [16]_ [17]_ [24]_ (note that
    [24]_ will be hosted at [25]_ shortly per [26]_ and a follow-up discussion
    that happened in the #openvswitch IRC channel);
* The OVN driver code in Neutron needs to learn about SmartNIC DPU node
  hostnames and respective PCIe add-in-card serial numbers gathered via VPD:

  * Port binding needs to be aware of the hypervisor and SmartNIC DPU
    hostname mismatches and mappings between card serial numbers and SmartNIC
    DPU node hostnames. The relevant Neutron RFE is in the ``rfe-approved``
    state [18]_ the relevant Neutron specification is published at
    [19]_, while the code for it is tracked in [20]_);
* Libvirt supports parsing PCI/PCIe VPD and as of October 2021 [21]_ and
  exposes a serial number if it is present in the VPD;
* Libvirt tries to clear a VLAN if one is not specified (trying to set VLAN ID
  to 0), however, some SmartNIC DPUs do not allow the hypervisor host to do
  that since the privileged NIC switch control is not provided to it. A patch
  to Libvirt [22]_ addresses this issue.

Future Work
-----------

Similar to the hardware offload [7]_ functionality, this specification does
not address operational concerns around the selection of a particular device
family. The specification proposing PCI device tracking in the placement
service [23]_ could be a step in that direction, however, it would likely
require Neutron extensions as well that would allow specifying requested device
traits in metadata associated with ports.

Testing
=======

* Unit testing of the added functionality;
* Functional tests will need to be extended to support additional cases related
  to the added functionality;


Documentation Impact
====================

* Nova admin guide needs to be extended to discuss ``remote_managed`` tags;
* Cross-project documentation needs to be written: Neutron and deployment
  project guides need to be updated to discuss how to deploy a cloud with
  SmartNIC DPUs.

References
==========

.. [1] https://netdevconf.info/0x14/pub/slides/39/Netdev%200x14%20--%20Taking%20Control%20of%20your%20SmartNIC%20v1.pdf
.. [2] https://homes.cs.washington.edu/~arvind/papers/ipipe.pdf
.. [3] https://man7.org/linux/man-pages/man7/ovn-architecture.7.html
.. [4] https://www.kernel.org/doc/Documentation/networking/switchdev.txt
.. [5] https://lwn.net/Articles/692942/
.. [6] https://www.kernel.org/doc/html/latest/networking/devlink/index.html
.. [7] https://docs.openstack.org/neutron/latest/admin/config-ovs-offload.html;
.. [8] https://www.snia.org/sites/default/orig/DSI2015/presentations/Rev/Jeff%20DodsonSNIA_Tutorial_PCIe_Shared_IO_2015_revision.pdf
.. [9] https://www.kernel.org/doc/html/latest/networking/devlink/devlink-port.html#pci-controllers
.. [10] https://www.kernel.org/doc/html/latest/networking/devlink/devlink-port.html#devlink-port
.. [11] https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=66b17082d10a3b806eec3da8fdebe8a9cd2c6612
.. [12] https://github.com/torvalds/linux/blob/v5.12/include/uapi/linux/devlink.h#L191-L206
.. [13] https://opendev.org/openstack/neutron/src/tag/19.0.0/neutron/plugins/ml2/drivers/mech_agent.py#L109-L116
.. [14] https://opendev.org/openstack/ironic-specs/commit/f358fbdde9a1cadc838327b8bf34ee54a7e7f43a
.. [15] https://docs.openstack.org/api-ref/network/v2/index.html?expanded=create-port-detail#id72
.. [16] https://patchwork.ozlabs.org/project/ovn/list/?series=267834&state=3&archive=both
.. [17] https://patchwork.ozlabs.org/project/ovn/list/?series=269965&state=*&archive=both
.. [18] https://bugs.launchpad.net/neutron/+bug/1932154
.. [19] https://review.opendev.org/c/openstack/neutron-specs/+/788821
.. [20] https://review.opendev.org/c/openstack/neutron/+/808961
.. [21] https://gitlab.com/libvirt/libvirt/-/commits/master?search=PCI.*VPD
.. [22] https://listman.redhat.com/archives/libvir-list/2021-November/msg00431.html
.. [23] https://review.opendev.org/c/openstack/nova-specs/+/791047
.. [24] https://github.com/fnordahl/ovn-vif
.. [25] https://github.com/ovn-org/ovn-vif
.. [26] https://mail.openvswitch.org/pipermail/ovs-dev/2021-November/389200.html
.. [27] https://github.com/torvalds/linux/blob/v5.15/drivers/net/ethernet/mellanox/mlx5/core/esw/legacy.c#L427-L434
.. [28] https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/virt/libvirt/vif.py#L479-L485
.. [29] https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/virt/libvirt/designer.py#L97-L105
.. [30] https://github.com/libvirt/libvirt/blob/7e6295cc7db2b11b28af7f4ef644f2dd30ea6840/src/conf/domain_conf.c#L29411-L29425
.. [31] https://github.com/libvirt/libvirt/blob/7e6295cc7db2b11b28af7f4ef644f2dd30ea6840/src/conf/domain_conf.h#L904
.. [32] https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/virt/libvirt/vif.py#L628-L640
.. [33] https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/virt/libvirt/vif.py#L94-L102
