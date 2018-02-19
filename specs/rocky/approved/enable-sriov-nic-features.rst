..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Enable SR-IOV NIC offload feature discovery
===========================================

https://blueprints.launchpad.net/nova/+spec/enable-sriov-nic-features

Today, most networking hardware vendors implement some of the TCP/IP stack,
traditionally done by the host operating system, in the NIC. Offloading
some of these functions to dedicated hardware frees up CPU cycles for
applications running on the system.

``libvirt`` implemented the SR-IOV NIC offload feature discovery in version
1.2.14 [1]_.

Problem description
===================

NIC features, in particular features around various hardware offload, are
useful for network-intensive applications. Unfortunately, Nova doesn't yet
retrieve physical NIC information from the system, which means the scheduler
cannot filter out compute hosts that do not contain certain NIC features.

If a virtual machine, during the booting step, discovers a NIC offload
feature, Nova Scheduler can select those hosts that have PCI devices with that
feature.

The aim of this spec is to fill this gap by proposing a method to read this
information, store it, use it during the scheduling process and provide a way
to share this information with Neutron.

Use Cases
---------

* An NFV MANO/VNFM system needs to ensure that a particular network I/O
  intensive workload is launched on a compute host with SR-IOV NIC hardware
  that has some specific hardware offload features (e.g. TSO and checksumming).


Proposed change
===============

This spec proposes to implement the following changes in Nova:

* A method to read the NIC feature information.
* A method to store this information in the Nova DB.
* How Nova Scheduler PCI filter will match this new information.

The spec also describes how a Neutron port must be defined to
include these NIC features. This information will be added to the OpenStack
manuals and devref.

NIC feature information
-----------------------

The libvirt API currently provides the feature list of a NIC device. Using the
command line utility we can retrieve the following information ::

    $ virsh nodedev-dumpxml net_ens785_68_05_ca_34_83_60
    <device>
      <name>net_ens785_68_05_ca_34_83_60</name>
      <path>/sys/devices/pci0000:00/0000:00:02.0/0000:02:00.0/net/ens785</path>
      <parent>pci_0000_02_00_0</parent>
      <capability type='net'>
        <interface>ens785</interface>
        <address>68:05:ca:34:83:60</address>
        <link state='down'/>
        <feature name='rx'/>   <-- example of NIC feature
        <feature name='tx'/>
        <feature name='sg'/>
        <feature name='tso'/>
        <feature name='gso'/>
        <feature name='gro'/>
        <feature name='rxvlan'/>
        <feature name='txvlan'/>
        <feature name='rxhash'/>
        <feature name='rdma'/>
        <feature name='txudptnl'/>
        <capability type='80203'/>
      </capability>
    </device>


The parent of a NIC device is always a unique PCI device and the only child of
this PCI device is the NIC device. This spec proposes to add a new member to
``nova.virt.libvirt.config.LibvirtConfigNodeDevicePciCap`` class, called
'net_features'. This member will be a list of strings, e.g.,
'HW_NIC_OFFLOAD_RX', 'HW_NIC_OFFLOAD_TSO' or 'HW_NIC_OFFLOAD_RXHASH'. This list
is empty by default. If a PCI device is not a NIC interface or doesn't have any
feature, the list will remain empty.

Store the NIC features information
----------------------------------

No changes are needed in the database. The NIC information per PCI device will
be stored in ``pci_devices.extra_info`` under a dictionary labeled
``capabilities``. This dictionary will contain all discovered PCI capabilities,
grouped in types. In this case, because the features are related with
networking capabilities, these will be contained in a list called ``network``
::

    extra_info: {'capabilities':
                    {'network': ['HW_NIC_OFFLOAD_RX', 'HW_NIC_OFFLOAD_SG',
                                 'HW_NIC_OFFLOAD_TSO', 'HW_NIC_OFFLOAD_TX']}
                }


As seen in the example above, the strings representing network capabilities are
traits belonging to ``os-traits`` project. Those traits are located under
``os_traits.hw.nic`` directory [2]_. Any other string not found in
``os-traits`` will be discarded from ``capabilities:network`` list and a
warning message will be logged, but no exception will be risen.

Neutron port ``binding:profile``
--------------------------------

The Neutron data model and API is already defined. No modifications in Neutron
project are needed.

E.g., how to define a Neutron port and request some specific NIC features,
defined in the binding profile ::

    $ openstack port create --binding-profile
        '{"capabilities": ["HW_NIC_OFFLOAD_RX", "HW_NIC_OFFLOAD_TSO"]}'
        --network private port1


Nova Scheduler filter ``PciPassthroughFilter``
----------------------------------------------

As it works now, the PCI request information during the boot of a virtual
machine will come both from the PCI alias information provided in the flavor
and the Neutron port definition passed in the boot command. With this feature,
the Neutron port would be able to contain a list of NIC features.

To add this new parameter to the filter, ``PciDeviceStats`` PCI device pools
will contain a new tag key ('capabilities.network'). Because every virtual
function in the pool belongs to the same PCI device, all of them have the same
NIC features.

If the binding profile from a Neutron port has a ``capabilities_network``
parameter, this will be extracted from the neutron port and added to the
PCI request spec, the PCI passthrough filter will try to match this value
with the one stored in the PCI device pools.

``capabilities_network`` parameter in both the request spec and the PCI device
stats are lists. Currently the PCI passthrough filter only matches string
parameters [3]_. This spec proposes to change this matching function to accept
both strings and lists:

* If a string is passed, the function will pass if both strings are equal.
* If a list is passed, the function will pass if all elements in the request
  spec list are contained in the PCI device pool list.


Alternatives
------------

* To create a new member in Neutron ``port``, containing the feature
  information as a list of strings. However, this change doesn't add any value
  because currently there is a place, ``binding:profile``, to define and
  store this information.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The Nova Scheduler ``PciPassthroughFilter`` needs to include the 'NIC features'
parameter into the checking loop, adding an extra time per host checked. In
return, the list of passed hosts could be shorter because of the new
restrictions.

Other deployer impact
---------------------

``libvirt`` implemented the SR-IOV NIC offload feature discovery in version
1.2.14 [1].

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  Rodolfo Alonso <rodolfo.alonso.hernandez@intel.com>
  Sean K Mooney <sean.k.mooney@intel.com>

Work Items
----------

1. Implement a method to read the NIC feature information.
2. Implement a method to store this information in the Nova DB.
3. Design how Nova Scheduler PCI filter will match this new information.
4. Add documentation illustrating how to correctly use filter and sort params
   when listing servers.
5. Add enough documentation to NFV MANO manuals and devref.
6. When Resource Provider project is fully implemented, migrate this feature
   and add all NIC features to os-traits.

Dependencies
============

None

Testing
=======

Few unittest needs to be adjusted to work correctly. All the unittest and
functional should be passed after the change.

Once the third-party CI with specific hardware is added to Jenkins, new tests
will be added.

Documentation Impact
====================

The devref needs to describe:

* Which new information is added to ``pci_devices`` and where is obtained.
* How to define the new parameters in the Nova Flavor extra specs fields.
* How to define a new Neutron port with these new parameters.

Neutron docs SR-IOV section must also contain this information.

References
==========

.. [1] `https://libvirt.org/news-2015.html`

.. [2] `https://github.com/openstack/os-traits/tree/0.3.3/os_traits/hw/nic`

.. [3] `https://github.com/openstack/nova/blob/master/nova/pci/utils.py#L39-L54`

History
=======

.. list-table:: Revisions
   :header-rows: 2

   * - Release Name
     - Description
   * - Pike
     - Approved
   * - Queens
     - Reintroduced
   * - Rocky
     - Reintroduced
