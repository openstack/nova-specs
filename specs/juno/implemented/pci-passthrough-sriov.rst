..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
PCI SR-IOV passthrough to nova instance
==========================================

https://blueprints.launchpad.net/nova/+spec/pci-passthrough-sriov

Enable nova instance to be booted up with SR-IOV neutron ports.

Problem description
===================
Right now it is possible to boot VM with general purpose PCI device passthrough
by means of libvirt's managed hostdev device definition in the domain XML. A
guide to use it can be found in [GPPWIKI]_. However, it's not possible to
request access to virtual network via SR-IOV NICs. Nova enhancments are
required to support SR-IOV networking with Neutron.

Traditionally, a neutron port is a virtual port that is either attached to a
linux bridge or an openvswitch bridge on a compute node. With the introduction
of SR-IOV based NIC (called vNIC), the virtual bridge is no longer required.
Each SR-IOV port is associated with a virtual function (VF) that logically
resides on a vNIC.  There exists two variants for SR-IOV networking. SR-IOV
ports may be provided by Hardware-based Virtual Eithernet Bridging (HW VEB); or
they may be extended to an upstream physical switch (IEEE 802.1br). In the
latter case, port's configuration is enforced in the switch.  There are also
two variants in connecting a SR-IOV port to its corresponding VF. A SR-IOV port
may be directly connected to its VF. Or it may be connected with a macvtap
device that resides on the host, which is then connected to the corresponding
VF. Using a macvtap device makes live migration with SR-IOV possible.

In the Icehouse release, a couple of blueprints from neutron side were approved
and their associated patches were committed that enable the interactions
between nova and neutron for SR-IOV networking. Refer to [VIFDETA]_ and
[BINDPRF]_ for details about them.

Another blueprint [VNICTYP]_ added the support in the neutron port API to
allow users to specify vnic-type when creating a neutron port. The currently
supported vnic-types are:

* normal: a traditional virtual port that is either attached to a linux bridge
  or an openvswitch bridge on a compute node.
* direct: an SR-IOV port that is directly attached to a VM
* macvtap: an SR-IOV port that is attached to a VM via a macvtap device.

This specification attempts to build up on top of the above-mentioned neutron
changes and address the following functionalities in Nova so that SR-IOV
networking in openstack is fully functional end-to-end:

1. Generating libvirt domain XML and network XML that enables SR-IOV for
   networking.
2. Scheduling based on SR-IOV port's network connectivity.

The initial use case that is targeted in this specification and therefore for
Juno is to boot a VM with one or more vNICs that may use different vnic-types.
Particularly a user would do the following to boot a VM with SR-IOV vnics:

* create one or more neutron ports. For example:

::

  neutron port-create <net-id> --binding:vnic-type direct

* boot a VM with one or more neutron ports. For example:

::

  nova boot --flavor m1.large --image <image>
            --nic port-id=<port1> --nic port-id=<port2>

Note that in the nova boot API, users can specify either a port-id or a net-id.
If it's the latter case, it's assumed that the user is requesting a normal
virtual port (which is not a SR-IOV port).

This specification will make use of the existing PCI passthrough
implementation, and make a few enhancements to enable the above use cases.
Therefore, the existing PCI passthrough support as documented by [GPPWIKI]_
works as it is for general-purpose PCI passthrough.

Proposed change
===============

To schedule an instance with SR-IOV ports based on their network connectivity,
the neutron ports' associated physical networks have to be used in making the
scheduling decision. A VF has to be selected for each of the neutron port.
Therefore, the VF's associated physical network has to be known to the system,
and the selected VF's associated physical network has to match that from the
neutron port. To make the above happen, this specification proposes associating
an extra tag called *physical_network* to each networking VF. In addition, nova
currently has no knowledge of a neutron port's associated physical network.
Therefore, nova needs to make extra calls to neutron in order to retrieve this
information from neutron. In the following, detailed changes in nova will be
described on how to achieve that.

Note that this specification only supports libvirt driver.

PCI Whitelist
-------------

This specification introduces a few enhancements to the existing PCI whitelist:

* allows aggregated declaration of PCI devices by using '*' and '.'
* allows tags to be associated with PCI devices.

Note that it's compatible with the previous PCI whitelist definition. And
therefore, the existing functionalities associated with the PCI whitelist work
as is.

with '[' to indicate 0 or one time occurrence, '{' 0 or multiple occurrences,
'|' mutually exclusive choice, a whitelist entry is defined as:

::

      ["device_id": "<id>",] ["product_id": "<id>",]
      ["address": "[[[[<domain>]:]<bus>]:][<slot>][.[<function>]]" |
       "devname": "PCI Device Name",]
      {"tag":"<tag_value>",}

*<id>* can be a '*' or a valid *device/product id* as displayed by the linux
utility lspci. The *address* uses the same syntax as it's in lspci. Refer to
lspci's manual for its description about the '-s' switch. The *devname* can be
a valid PCI device name. The only device names that are supported in this
specification are those that are displayed by the linux utility *ifconfig -a*
and correspond to either a PF or a VF on a vNIC. There may be 0 or more tags
associated with an entry.

If the device defined by the *address* or *devname* corresponds to a SR-IOV PF,
all the VFs under the PF will match the entry.

For SR-IOV networking, a pre-defined tag "physical_network" is used to define
the physical network that the devices are attached to. A whitelist entry is
defined as:

::

      ["device_id": "<id>",] ["product_id": "<id>",]
      ["address": "[[[[<domain>]:]<bus>]:][<slot>][.[<function>]]" |
       "devname": "Ethernet Interface Name",]
      "physical_network":"name string of the physical network"

Multiple whitelist entries per host are supported as they already are. The
fields *device_id*, *product_id*, and *address* or *devname* will be matched
against PCI devices that are returned as a result of querying libvirt.

Whitelist entries are defined in nova.conf in the format:

::

    pci_passthrough_whitelist = {<entry>}

{<entry>} is a json dictionary and is defined as in above.
*pci_passthrough_whitelist* is a plural configuration, and therefore can appear
multiple times in nova.conf.

Some examples are:

::

    pci_passthrough_whitelist = {"devname":"eth0",
                                 "physical_network":"physnet"}

    pci_passthrough_whitelist = {"address":"*:0a:00.*",
                                 "physical_network":"physnet1"}

    pci_passthrough_whitelist = {"address":":0a:00.",
                                 "physical_network":"physnet1"}

    pci_passthrough_whitelist = {"vendor_id":"1137","product_id":"0071"}

    pci_passthrough_whitelist = {"vendor_id":"1137","product_id":"0071",
                                 "address": "0000:0a:00.1",
                                 "physical_network":"physnet1"}

PCI stats
---------

On the compute node, PCI devices are matched against the PCI whitelist entries
in the order as they are defined in the nova.conf file. Once a match is found,
the device is placed in the corresponding PCI stats entry.

If a device matches a PCI whitelist entry, and if the PCI whitelist entry is
tagged, the tags together with *product_id* and *vendor_id* will be used as
stats keys; otherwise, the existing predefined keys will be used.

A PCI whitelist entry for SR-IOV networking will be tagged with a physical
network name. Therefore, the physical network name is used as the stats key for
SR-IOV networking devices. Conceptually speaking for SR-IOV networking, a PCI
stats entry keeps track of the number of SR-IOV ports that are attached to a
physical network on a compute node. And for scheduling purpose, it can be
considered as a tuple of

::

    <host_name> <physical_network_name> <count>

When a port is requested from a physical network, the compute nodes that host
the physical network can be found from the stats entries. The existing PCI
passthrough filter in nova scheduler works without requiring any change in
support of SR-IOV networking.

There is no change in how the stats entries are updated and persisted into the
compute_nodes database table with the use of nova resource tracker.  Currently,
a collumn called *pci_stats* in the compute_nodes database table is used to
store the PCI stats as a JSON document. The PCI stats JSON document is
basically a list of stats entries in the format of *<key1> <key2> ....<keyn>* :
*<count>*. This will not be changed for SR-IOV networking. Specifically for
SR-IOV networking, however, PCI stats records are keyed off with the tag
*physical_network_name*, plus *product_id* and *vendor_id*. a stats entry for
SR-IOV networking will look like:

::

   <physical_network_name>, <product_id>, <vendor_id> : <count>.

requested_networks (NICs)
-------------------------

Currently, each requested network is a tuple of

::

    <neutron-net-id> <v4-fixed-ip> <neutron-port-id>

Either neutron-net-id or neutron-port-id must have a valid value, and
v4-fixed-ip can be None. For each --nic option specified in the *nova boot*
command, a requested_network tuple is created. All the requested_network tuples
are passed to the compute node, and the compute service running on the node
uses the information to request neutron services. This specification proposes
one additional field in the tuple: *pci-request-id*.

Corresponding to each requested_network tuple, there is a neutron port with a
valid vnic-type. If the vnic-type is direct or macvtap, a valid
*pci_request_id* must be populated into the tuple (see below for details). The
*pci-request-id* is later used to locate the PCI device from PCI manager that
is allocated for the requested_network tuple (therefore the NIC).

PCI Requests
------------

Currently, pci_requests as key and a JSON doc string as associated value are
stored in the instance's system metadata. In addition, all the PCI devices
allocated for PCI passthrough are treated the same in terms of generating
libvirt xml. However, for SR-IOV networking, special libvirt xml is required.
Further, we need a way to correlate the allocated device with the requested
network (NIC) later on during the instance boot process. In this specification,
we propose the use of *pci_request_id* for that purpose.

Each PCI request is associated with a *pci_request_id* that is generated while
creating/saving the PCI request to the instance's system metadata. The
*pci_request_id* is used on the compute node to retrieve the allocated PCI
device. Particularly for SR-IOV networking, a PCI request is expressed as

::

   "physical_network" : <name>
   "count" : 1
   "pci_request_id" : <request-uuid>

For each --nic specified in the 'nova boot', nova-api creates a requested
network tuple. For a SR-IOV NIC, it creates a PCI request and as a
result a *pci_request_id* is generated and saved in the PCI request spec. The
same *pci_request_id* is also saved in the requested_network (Refer to the last
section).

nova neutronv2 and VIF
-------------------------------------

Note that Nova network will not be enhanced to support SR-IOV. However, Nova
modules that are responsible for interacting with neutron need to be enhanced.

Refer to [BINDPRF]_, [VIFDETA]_, [VNICTYP]_ that has added the
functionalities required to support SR-IOV ports in neutron. Accordingly, nova
neutronv2 will be enhanced to work with them in support of SR-IOV ports.
Particularly:

* When nova processes the --nic options, physical network names will be
  retrieved from neutron. This needs to be done by using neutron provider
  extension with admin access. As a result, additional neutron calls will be
  made to retrieve the physical network name.
* When nova updates neutron ports, binding:profile needs to be populated with
  pci information that includes pci_vendor_info, pci_slot, physical_network.
* After nova successfully updates the neutron ports, it retrieves the ports'
  information from neutron that are used to populate VIF objects. New
  properties will be added in the VIF class in support of binding:profile,
  binding:vif_details and binding:vnic_type.

nova VIF driver
---------------

Each neutron port is associated with a vif-type. The following VIF types are
related to SR-IOV support:

* VIF_TYPE_802_QBH: corresponds to IEEE 802.1BR (used to be IEEE 802.1Qbh)
* VIF_TYPE_HW_VEB: for vNIC adapters that supports virtual embedded bridging
* VIF_TYPE_802_QBG: corresponds to IEEE 802.1QBG. However, this existing vif
  type may not be useful now because the libvirt parameters for 1QBG
  (managerid, typeidversion and instanceid) are not supported by known neutron
  plugins that support SR-IOV.

The nova generic libvirt VIF driver will be enhanced to support the first two
VIF types. This includes populating the VIF config objects and generating the
interface XMLs.

Alternatives
------------

N/A

Data model impact
-----------------

Currently, a nova object *PciDevice* is created for each PCI passthrough
device. The database table *pci_devices* is used to persist the *PciDevice*
nova objects. A new field *request_id* will be added in the *PciDevice* nova
object. Correspondingly, a new column *request_id* is added in the database
table *pci_devices*. Database migration script will be incorporated
accordingly.

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

The physical network to which a port is connected needs to be retrieved from
neutron, which requires additional calls to neutron. Particularly, nova will
call neutron *show_port* to check the port's *vnic_type*. If the *vnic_type* is
either *direct* or *macvtap*, it will call neutron *show_network* to retrieve
the associated physical network. As a consequence, the number of calls to
neutron will be slightly increased when *port-id* is specified in the --nic
option in nova boot.

Other deployer impact
---------------------

No known deployer impact other than configuring the PCI whitelist for SR-IOV
networking devices.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  baoli

Other contributors:
  TBD

Work Items
----------

* PCI whitelist
* PCI request
* PCI stats
* DB change and the required migration script, PCI device object change
* neutronv2
* VIF
* libvirt generic VIF driver and instance configuration
* nova compute api retrieving physical network, change of requested_networks

Dependencies
============

None

Testing
=======

Both unit and tempest tests need to be created to ensure proper functioning of
SR-IOV networking. For tempest testing, given the nature of SR-IOV depending on
hardware, it may require vendor support and use of proper neutron ML2 mechanism
drivers. Cisco Neutron CI and Mellanox External Testing need to be enhanced in
support of SR-IOV tempest testing.

Documentation Impact
====================

* document new whitelist configuration changes
* a user guide/wiki on how to use SR-IOV networking in openstack

References
==========
.. [GPPWIKI] `Generic PCI Passthrough WIKI <https://wiki.openstack.org/wiki/Pci_passthrough>`_
.. [VIFDETA] `Extensible port attribute for plugin to provide details to VIF driver  <https://blueprints.launchpad.net/neutron/+spec/vif-details>`_
.. [BINDPRF] `Implement the binding:profile port attribute in ML2 <https://blueprints.launchpad.net/neutron/+spec/ml2-binding-profile>`_
.. [VNICTYP] `Add support for vnic type request to be managed by ML3 mechanism drivers <https://blueprints.launchpad.net/neutron/+spec/ml2-request-vnic-type>`_
