..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
PCI Device Tracking In Placement
================================

https://blueprints.launchpad.net/nova/+spec/pci-device-tracking-in-placement

The OpenStack Placement service was designed to provide tracking
of quantitative resources via resource class inventories and qualitative
characteristics via traits. Over the last few cycles, nova has utilized
Placement to track basic resources such as CPUs, RAM, and disk, and more
complex resources such as Virtual GPUs. This spec describes how Nova can
utilize Placement to track generic PCI devices without going into the details
of the NUMA awareness of such devices.

Problem description
===================

Nova has supported generic stateless PCI passthrough for many releases using a
dedicated PCI tracker in conjunction with a ``PciPassthroughFilter`` scheduler
post filter.

The PCI tracker is responsible for tracking which PCI devices are available,
claimed, and allocated, the capabilities of the device, its consumer when
claimed or allocated as well as the type of PCI device and location.

The ``PciPassthroughFilter`` is responsible for ensuring that devices,
requested by the VM, exist on a host during scheduling. These PCI requests come
from two sources: flavor-based PCI requests that are generated using the
``pci_passthrough:alias`` `flavor extra specs`_ and neutron based PCI requests
generated from SR-IOV backed neutron ports.

.. _`flavor extra specs`: https://docs.openstack.org/nova/latest/configuration/extra-specs.html#pci_passthrough:alias

While the current approach to PCI tracking works there are some limitations
in the current design and there is room for optimization.

.. rubric:: Limitations

* During server creation PCI devices are not claimed until the instance_claim
  is created on the compute node. As a result, it is possible for two
  concurrent server create requests to race for the last device on a host
  resulting in re-schedules.

* While Nova today tracks the capabilities of network interfaces in the
  ``extra_info`` field of the ``pci_devices`` table and the
  ``PciPassthroughFilter`` could match on those capabilities there is no
  user-facing way to express a request for an SR-IOV neutron port with a
  specific network capability e.g. TSO.

* There is no admin-facing interface to check the available and allocated PCI
  resources in the cloud. The only way is to look into the Nova database.

.. rubric:: Optimizations

* Today when the virt driver is assigning a PCI device on the compute hosts
  it needs to look at all available PCI devices on the host and select one that
  fulfills the PCI and NUMA requirements. If we model PCI devices in Placement
  we only need to consider the devices associated with the PCI resource
  allocation in Placement.

* Today when we schedule we perform host filtering of viable hosts based on
  PCI devices in python. By utilizing Placement we can move that filtering to
  SQL.

Use Cases
---------

- As an operator I want instance creation to atomically claim resources to
  decrease the chance of retries.

- As an operator, I want to shorten the time it takes to select a host by
  running fewer filters.

- As an operator, I want to utilize traits and resource classes to model
  PCI aliases and requests for more expressive device management.

- As an operator, I want to be able to associate quotas with PCI device usage.

- As an operator, I want to be able to use the Placement API to query available
  and allocated PCI devices in my cloud.

.. note::

  Device quotas would require unified limits to be implemented. Implementing
  quotas is out of the scope of this spec beyond enabling the use case by
  modeling PCI devices in Placement.

  This spec will also only focus on flavor-based PCI passthrough. Neutron
  SR-IOV port will be addressed in a follow-up spec to limit the scope.

Proposed change
===============

Opt-in reporting of PCI devices in Placement
--------------------------------------------

To support upgrade of existing deployments with PCI passthrough configured
and to be able to deprecate and eventually remove some of the functionality of
the current PCI device tracker the new Placement based PCI device tracking will
be disabled by default in the first release. The new
``[pci]report_in_placement`` config option can be used to enable the
functionality. It will be defaulted to ``False`` first and once it is turned to
``True`` nova-compute will refuse to start if disabled again. In a future
release, after the PCI tracking in Placement is feature complete, the default
will be changed to ``True``.

PCI device_spec configuration
-----------------------------

Below we propose a change to the ``[pci]passthrough_whitelist`` configuration
option. While we are making this change we will take this opportunity to
update the name of the configuration option. The old name of the
``[pci]passthrough_whitelist`` config option will be deprecated for eventual
removal and a new name ``[pci]device_spec`` will be added. Both the
old and the new name will support the newly proposed ``resource_class`` and
``traits`` tags.

The syntax of the `PCI passthrough device list`_ configuration option will be
extended to support two additional standard tags ``resource_class`` and
``traits``. These new tags will only take effect if the
``[pci]report_in_placement`` config option is set to ``True``.

.. code-block:: js

    device_spec = {
      "vendor_id": "1002",
      "product_id": "67FF",
      "resource_class":"CUSTOM_GPU",
      "traits": "CUSTOM_RADEON_RX_560", "CUSTOM_GDDR5"
    }
    device_spec = {
      "address": "0000:82:00.0",
      "resource_class":"CUSTOM_FPGA",
      "traits": "CUSTOM_XILINX_XC7VX690T"
    }


The ``resource_class`` tag will be accepted only when the ``physical_network``
tag is not defined and will enable a PCI device to be associated with a custom
resource class. Each PCI whitelist entry may have at most one resource class
associated with it. Devices that have a ``physical_network`` tag will not be
reported in Placement at this time as Neutron based SR-IOV is out of the
scope of the current spec.

Where a PCI device does not have a ``physical_network`` or a ``resource_class``
tag present it will be reported with a generated custom resource class.
The resource class will be ``CUSTOM_PCI_<vendor_id>_<product_id>``.

The ``traits`` tag will be a comma-separated list of standard or custom trait
names that will be reported for the device RP in Placement.

Nova will normalize and prefix the resource class and trait names with
``CUSTOM_``, if isn't already prefixed, before creating them in Placement.
Nova will first check the provided trait name in os_traits and if it exists
as a standard trait then that will be used instead of creating a custom one.

.. note::

  Initially traits will only be additive, in the future if we need to we can
  allow traits to be removed using a +/- syntax but this is not included
  in the scope of this spec.

  As detailed in the `Modeling PCI devices in Placement`_ section, each
  physical device (PF) will be its own resource provider with inventories of
  the relevant PF and VF resource classes. As such traits cannot vary per VF
  device under the same parent PF. If VFs are individually matched by different
  ``device_spec`` entries, then defining different ``traits``  for different
  VFs under the same PF is a configuration error and will be rejected.

  While it would possible to support defining different ``resource_class``
  names for different VFs under the same parent PF, this is considered bad
  practice and unnecessary complexity. Such configuration will be rejected.

  If different traits need to be supported on a PF than its children VFs
  then it is suggested to match the PF and its VFs in two separate
  ``device_spec`` entries and differentiate the PF and VF traits by namespacing
  them, e.g.: CUSTOM_PCI_PF_XXX and CUSTOM_PCI_VF_YYY

.. note::

  Nova will detect if the ``resource_class`` or ``traits`` configuration of
  an already reported device is changed at a nova-compute service restart. If
  the affected device is free the Nova will apply the change in Placement but
  if the device is already allocated then the nova-compute service will refuse
  to start.

.. note::

  In the future when PCI tracking in Placement will be extended to device_spec
  entries with ``physical_network`` tag, these entries will not allow
  specifying a ``resource_class`` but nova will use the standard
  ``SRIOV_NET_VF``, ``PCI_NETDEV`` and ``VDPA_NETDEV`` classes. This will
  not prevent type-VF and type-PF devices to be consumed via PCI alias, as the
  alias can request these standard resource classes too.

.. _`PCI passthrough device list`: https://docs.openstack.org/nova/latest/configuration/config.html#pci.passthrough_whitelist

The new Placement based PCI tracking feature won't support the ``devname`` tag
in the ``[pci]device_spec`` configuration. Usage of this tag is already limited
as not all PCI devices has a device name. Also ``devname`` only works
properly if the names are kept stable across hypervisor reboots and upgrades.
If the ``[pci]report_in_placement`` is set to ``True`` and the
``[pci]device_spec`` has any entry with ``devname`` tag then the nova-compute
service will refuse to start.

Modeling PCI devices in Placement
----------------------------------

PCI device modeling in Placement will closely mirror that of vGPUs.
Each PCI device of type ``type-PCI`` and ``type-PF`` will be modeled as a
Placement resource provider (RP) with the name
``<hypervisor_hostname>_<pci_address>``. The hypervisor_hostname prefix will be
the same string as the name of the root RP. The pci_address part of the
name will be the full PCI address in the same format of ``DDDD:BB:AA.FF``.

.. note::

  The pGPU RPs are using the libvirt nodedev name but this spec is not try to
  follow that naming scheme as the libvirt nodedev names are not considered
  stable. Also nova always uses the RP UUID to identify and RP instead of its
  name. So these names are only for troubleshooting purposes.

Each PCI device RP will have an inventory of resource class and traits based
on the ``[pci]device_spec`` entry matching with the given device. If the device
has children devices (VFs) matching with any ``device_spec`` entry then the
resource inventory and traits of the children will be reported to the parent PF
RP too.

If a PCI device is matching a ``device_spec`` entry without a
``physical_network`` tag then an inventory of 1 is reported of the
``resource_class`` specified in the matching ``device_spec`` entry or if
``resource_class`` is not specified there then with the generated
``CUSTOM_PCI_<vendor_id>_<product_id>`` resource class.

If a ``type-VF`` device is matching a ``device_spec`` entry then the related
resource inventory will be reported on RP representing its parent PF device.
The PF RP will be created even if the ``type-PF`` device is not matching any
``device_spec`` entry but in that case, only VF inventory will exist on the RP.

If multiple VFs from the same parent PF is matching the ``device_spec`` then
the total resource inventory of VFs will be the total number of matching VF
devices.

Each PCI device RP will have traits reported according to the ``traits`` tag
of the matching ``device_spec`` entry. Nova might report additional traits on
the device RP automatically for scheduling purposes.

Listing both the parent PF device and any of this children VF devices at the
same time will not be support if ``[pci]report_in_placement`` is enabled. See
`Dependent device handling`_ section for more details.

.. note::

  Even though neutron-requested PCI devices are out of the scope of this spec
  the handling of ``type-PF`` and ``type-VF`` devices cannot be ignored as
  those device types can also be requested via PCI alias by setting the
  ``device_type`` tag accordingly.

.. note::

  The PCI alias can only request devices based on ``vendor_id`` and
  ``product_id`` today and that information will be automatically included in
  the Placement inventory as the resource class.

.. note::

  In the future Nova can be extended to automatically report PCI device
  capabilities as custom traits in placement. However this is out of scope of
  the current spec. If needed the deployer can add these traits via the
  ``[pci]device_spec`` configuration manually.


Reporting inventories from libvirt to Placement
-----------------------------------------------

The resource tracker's ``update_available_resource`` periodic task calls the
``update_provider_tree`` method on the libvirt virt driver. The
implementation of ``update_provider_tree`` in the libvirt virt driver will be
extended to create the relevant PF RPs, and report inventories and traits via
the ``provider_tree`` interface to Placement.

When ``update_provider_tree`` is called during compute service startup (via
init_host) the virt driver will do a reshape of the provider tree to make sure
that existing VMs with PCI allocation will have the corresponding resource
allocation in Placement as well.

.. note::

  The compute restart logic needs to handle the case when a device is not
  present any more either due to changes in the ``[pci]device_spec`` config
  option or due to a physical device removal from the hypervisor. The driver
  needs to modify the VF resource inventory on the PF RP (when a VF is removed)
  or delete the PF RP (if the PF is removed and no children VFs matched). Nova
  cannot prevent the removal of a PCI device from the hypervisor while the
  device is allocated to a VM. Still Nova will emit a warning in such case.

PCI alias configuration
-----------------------

The `PCI alias definition`_ in ``[pci]alias`` configuration option will be
extended to support two new tags, ``resource_class``, ``traits``. The
``resource_class`` tag can hold exactly one resource class name. While the
``traits`` tag can hold a comma-separated list of trait names. Also trait names
in ``traits`` can be prefixed with ``!`` to express a forbidden trait.
When the ``resource_class`` is specified, the ``vendor_id`` and ``product_id``
tags will no longer be required.

.. note::

  If both ``resource_class`` and ``vendor_id`` and ``product_id`` fields are
  provided in the alias then Nova will use the ``resource_class`` for the
  Placement query but the ``vendor_id`` and ``product_id`` filtering will
  happen in the ``PciPassthroughFilter``.

.. note::

  Later if more complex trait requirements are needed we can add support for
  multiple ``traits`` tag by adding a free postfix. Also later we can add
  support for ``in:`` prefix in the value of the ``traits`` tag to express
  an OR relationship. E.g.

  .. code-block:: js

    {
        "traits1": "T1,!T2",
        "traits2": "in:T3,T4"
    }

.. _`PCI alias definition`: https://docs.openstack.org/nova/latest/configuration/config.html#pci.alias

Requesting PCI devices
----------------------

The syntax and handling of the ``pci_passthrough:alias`` `flavor extra specs`_
will not change. Also, Nova will continue using the ``InstancePCIRequest`` to
track the requested PCI devices for a VM.

Scheduling
----------

A new prefilter will be added to convert ``InstancePCIRequest`` requests into
Placement resource requests. Each PCI request will be its own Placement named
request group. If a PCI request comes from a PCI alias and the alias does not
have a ``resource_class`` associated with it it will be computed using the
``vendor_id`` and ``product_id`` ``CUSTOM_PCI_<vendor_id>_<product_id>``.

The prefilter will be disabled by default to enable rolling
upgrades. There will be a new config option ``[scheduler]pci_prefilter`` that
can be used to enable the prefilter. Enabling that prefilter has a list of
prerequisites. See the `Upgrade impact`_ section for the full upgrade
procedure.

.. note::

  For now the prefilter will only create request groups from PCI requests
  coming from the flavor. PCI requests coming from Neutron ports will be
  ignored by the prefilter and kept scheduled by the ``PciPassthroughFilter``.


Dependent device handling
-------------------------

Today nova allows matching both a parent PF and its children VFs in the
configuration and these devices are tracked as separate resources. However,
they cannot be consumed independently. When the PF is consumed its children VFs
become unavailable. Also when a VF is consumed its parent PF becomes
unavailable. This dynamic device type selection will be deprecated and the new
Placement based PCI tracking will only allow configuring either the PF device
or its children VF devices. The old PCI tracker will continue support this
functionality but as soon as ``[pci]report_in_placement`` is set to True on a
compute that compute will reject configurations that are enabling both the PF
and in children VFs.

PCI NUMA affinity
-----------------

The PCI NUMA affinity code (mostly in ``hardware.py``) will need to be modified
to limit the PCI devices considered to just those included in the allocation
candidate summary. Also at the same time, this code should provide information
to the scheduler about which allocation candidate is valid from affinity
perspective.

To enable this the allocation candidates will be added to the ``HostState``
object of the filter scheduler. The ``NUMATopologyFilter`` will then need to
pass the allocation candidates to the hardware.py functions which will need to
remove any allocation candidates from that list that do not fulfill the NUMA
requirements. The filter should then pop any invalid allocation candidates
from the ``HostState`` object. At the end of the scheduling process, the filter
scheduler will have to reconstruct the host allocation candidate set from the
``HostState`` object.

By extending the ``HostState`` object with the allocation candidate we will
enable the filters to filter not just by the host but optionally by the
allocation candidates of the host without altering the filter API therefore
maintaining compatibility with external filters.

PCI tracker
-----------

The PCI tracker will have to be enhanced to support allocation aware claims.
To do this we will need to extend the ``PciDevicePool`` object to have a unique
identifier that can be correlated by the resource tracker to the RP in
Placement. The suggested value is the PCI address. In the case of ``type-PF``
and ``type-PCI`` the PCI address for the allocation will be the PCI address of
the device to claim. In the case of ``type-VF`` it will be the address of the
parent device.

Both the instance claim and the move claim need to be extended similarly.


VM lifecycle operations
-----------------------

The initial scheduling is very similar to the later scheduling done due to
move operations. So, the existing implementation can be reused. Also, the
current logic that switches the source node Placement allocation to be held by
the migration UUID can be reused.

Live migration is not supported with PCI alias-based PCI devices and this will
not be changed by the current spec.

Attaching and detaching PCI devices are only supported via Neutron SR-IOV ports
and that is out of the scope of this spec.


Neutron SR-IOV ports (out of scope)
-----------------------------------

This is out of scope in the current spec. But certain aspects of the problem
are already known and therefore listed here.

There are a list of Neutron port ``vnic_type`` (e.g. ``direct``,
``direct-physical``,etc) where the port needs to be backed by VF or PF PCI
devices.

In the simpler case when a port only requires a PCI device but does
not require any other resources (e.g. bandwidth) then Nova needs to create
Placement request groups for each Neutron port with the already proposed
prefilter. See `Scheduling`_ for more details. In this case, neither the
name of the resource class nor the vendor ID, product ID pair is known at
scheduling time (compared to the PCI alias case) therefore the prefilter does
not know what resource class needs to be requested in the Placement request
group.

To resolve this, PCI devices that are intended to be used for Neutron-based
SR-IOV should should not use the ``resource_class`` tag in the
``[pci]device_spec``. Instead Nova will use standard resource classes to
model these resource.

Today nova allows consuming type-PCI or type-VF for ``direct`` ports. This
is mostly there due to historical reasons and it should be cleaned up. A
better device categorization is suggested:

* A device in the ``device_spec`` will be consumable only via PCI alias
  if it does not have ``physical_network`` tag attached.

* A device that has ``physical_network`` tag attached will be considered a
  network device and it will be modelled as ``PCI_NETDEV`` resource.

* A device that has ``physical_network`` tag and also has the capability to
  provide VFs will have a trait ``HW_NIC_SRIOV`` but still use the
  ``PCI_NETDEV`` resource class.

* A device that has ``physical_network`` tag and is a VF will be modelled
  as ``SRIOV_NET_VF`` resource.

This way every Neutron ``vnic_type`` can be mapped to one single resource
class by Nova. The following ``vnic_type`` -> resource class mapping is
suggested:

* ``direct``, ``macvtap``, ``virtio-forwarder``, ``remote-managed`` ->
  ``SRIOV_NET_VF``
* ``direct-physical`` -> ``PCI_NETDEV``
* ``vdpa`` -> ``VDPA_NETDEV``

Nova will use these resource classes to report device inventories to
Placement. Then the prefilter can translate the ``vnic_type`` of the ports to
request the specific resource class during scheduling.

Another specialty of Neutron-based SR-IOV is that the devices listed in the
``device_spec`` always have a ``physical_network`` tag.
This information needs to be reported as a trait to the PF RP in Placement.
Also, the port's requested physnet needs to be included in the Placement
request group by the prefilter.

There is a more complex case when the Neutron port not only requests a PCI
device but also requests additional resources (e.g. bandwidth) via the port
``resource_request`` attribute. In this case, Nova already generates Placement
request groups from the ``resource_request`` and as in the simple case will
generate a request group from the PCI request. The resource request
of these groups of a neutron port needs to be correlated to ensure that a port
gets the PCI device and the bandwidth from the same physical device. However
today the bandwidth is modeled under the Neutron RP subtree while PCI devices
will be modeled right under the root RP. So the two RPs to allocate from are
not within the same subtree. (Note that Placement always fulfills a named
request group from a single RP but allows correlating such request groups
within the same subtree.) We have multiple options here:

* Create a scheduler filter that removes allocation candidates where these
  request groups are fulfilled from different physical devices

* Report the bandwidth and the PCI device resource on the same RP. This breaks
  the clear ownership of a single RP as the bandwidth is reported by the
  neutron agent while the PCI device is reported by Nova.

* Move the two RPs (bandwidth and PCI dev) into the same subtree. This
  needs an agreement between Nova and Neutron devs where to move the RPs and
  needs an extra reshape to implement the move.

* Enhance Placement to allow sharing of resources between RPs within the same
  RP tree. By that, we could make the bandwidth RP a sharing RP that shares
  resources with the PCI device RP representing the physical device.

Based on the selected solution either:

* Neutron requests the specific resource class for the SRIOV
  port via the port ``resource_request`` field

* Nova can include these resources to the request when the
  ``InstancePCIRequest`` objects are created based on the requested ports.

Alternatives
------------

* We could keep using the legacy tracking with all its good and bad properties.

* We could track each PCI device record as a separate RP.
  This would result in each VF having its own RP allowing each VF to have
  different traits. This is not proposed as it will significantly increase the
  possible permutations of allocation candidates per host.

* We could keep supporting the dynamic PF or VF consumption in Placement but
  it is deemed more complex than useful. We will keep supporting it via the
  legacy code path but the new code path will not support it.

* We could model each PCI device under a NUMA node.
  This can be done in the future by moving the RP under a NUMA node RP instead
  of the compute node RP but it is declared out of the scope of this initial
  spec.


Data model impact
-----------------

``InstancePCIRequest`` object will be extended to include the required and
forbidden traits and the resource class requested via the PCI alias in the
flavor and defined in the PCI alias configuration.

``PciDevicePool`` object will be extended to store PCI address information so
that the PCI device allocated in Placement can be correlated to the PCI device
to be claimed by the PCI tracker.

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

In general, this is expected to improve the scheduling performance but
should have no runtime performance impact on guests.

The introduction of a new prefilter will make the computation of the placement
query slightly longer and the resulting execution time may increase for
instances with PCI requests but should have no effect for instances without
PCI requests. This added complexity is expected to be offset by the removal of
the requirement to enable the ``PciPassthroughFilter`` scheduler filter
eventually. As a result of the offloading of the filtering to Placement and the
removal of reschedules due to racing for the last PCI device on a host, the
overall performance is expected to improve.

Other deployer impact
---------------------

To utilize the new feature the operator will have to define two new config
options. One to enable the placement prefilter and a second to enable the
reporting of the PCI devices to Placement.

Developer impact
----------------

Drivers, other than the libvirt virt driver, need to be adapted to use the new
Placement based PCI device tracking.

Upgrade impact
--------------

The new Placement based PCI tracking will be disabled by default. Deployments
already using PCI devices can freely upgrade to the new Nova version without
any impact. At this state the PCI device management will be done by the
``PciPassthroughFilter`` in the scheduler and the PCI claim in the PCI device
tracker in the compute service same as in the previous version of Nova.
Then after the upgrade the new PCI device tracking can be enabled in two
phases.

First the PCI inventory reporting needs to be enabled by
``[pci]report_to_placement`` on each compute host. During the startup of the
nova-compute service with ``[pci]report_to_placement = True`` config the
service will do the reshape of the provider tree and start reporting PCI device
inventory to Placement. Nova compute will also heal the PCI allocation of the
existing instances in Placement. This healing will be done for new
instances with PCI requests until a future release where the prefilter enabled
by default. This is needed to keep the resource usage in sync in Placement
even if the instance scheduling is done without the prefilter requesting
PCI allocations in Placement.

.. note::

  Even after we make the prefilter enabled by default in a future release the
  prefilter still need to be kept configurable as we don't know when the hyperv
  virt driver will implement PCI tracking in Placement.

.. note::

  Operators are encouraged to take the opportunity to rename the
  ``[pci]passthrough_whitelist`` config option to the new ``[pci]device_spec``
  option. The syntax of the two options are the same.

.. note::

  The ``devname`` tag is not supported in the ``[pci]device_spec`` and in the
  ``[pci]passthrough_whitelist`` any more if ``[pci]report_to_placement`` is
  enabled. We suggest to use the ``address`` tag instead.

.. note::

  If the deployment is configured to rely on the dynamic dependent device
  behavior, i.e. both the PF and its children VFs are matching the
  ``device_spec`` then reconfiguration will be needed as the new code patch
  will not support this and the nova-compute service will reject to start with
  such configuration. To do the reconfiguration the deployer needs to look at
  the current allocation of the PCI devices on each compute node:

  *  if neither the PF nor any of its children VFs are allocated then the
     deployer can decide which device(s) kept in the ``device_spec``.

  * if the PF is already allocated then the PF needs to be kept in the
    ``device_spec`` but all children VFs has to be removed.

  * if any of the children VF device is allocated then the parent PF needs to
    be removed from the ``device_spec`` and at least the currently allocated
    VFs needs to be kept in the config, while other non allocated children VFs
    can be kept or removed from the ``device_spec`` at will.

.. note::

  Once ``[pci]report_to_placement`` is enabled for a compute host it cannot be
  disabled any more.

Second, after every compute has been configured to report PCI inventories to
Placement the scheduling prefilter needs to be enabled in the nova-scheduler
configuration via the ``[scheduler]pci_prefilter`` configuration option.


Implementation
==============

Assignee(s)
-----------


Primary assignee:
  balazs-gibizer


Feature Liaison
---------------


Feature liaison:
  sean-k-mooney


Work Items
----------
* rename PCI ``passthrough_whitelist`` to ``device_spec``
* support for adding a resource class and traits to ``device_spec``
* introduce ``[pci]report_in_placement``
* reject dependent devices config and ``devname`` config
* PCI reshape and allocation healing for existing instances
* support for adding resource class and required and forbidden traits to PCI
  alias
* prefilter
* extension of ``HostState`` object with an allocations candidate list
* extension of scheduler to populate ``HostState`` object with candidates and
  then reconstruct the candidate list after filtering.
* extension of ``hardware.py`` to consider allocation candidates when filtering
  for NUMA affinity.
* extension of PCI manager claiming to be allocation aware.

Dependencies
============

The unified limits feature exists in an opt-in, experimental state and will
allow defining limits for the new PCI resources if enabled.


Testing
=======

As this is a PCI passthrough related feature it cannot be tested in upstream
tempest. Testing will be primarily done via the extensive unit and functional
test suites that exists for instances with PCI devices and NUMA topology in the
libvirt functional tests.


Documentation Impact
====================

The PCI passthrough doc will have to be rewritten to document the new
``resource_class`` and ``trait`` tags for the PCI ``device_spec`` and
PCI alias.


References
==========

* _`CPU resource tracking spec`: https://specs.openstack.org/openstack/nova-specs/specs/train/implemented/cpu-resources.html
* _`Unified Limits Integration in Nova`: https://specs.openstack.org/openstack/nova-specs/specs/ussuri/approved/unified-limits-nova.html
* _`Support virtual GPU resources`: https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/add-support-for-vgpu.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
   * - Zed
     - Extended and re-proposed
