..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Add support for InfiniBand SR-IOV VIF Driver
=============================================

https://blueprints.launchpad.net/nova/+spec/vif-driver-ib-passthrough

Adding support for InfiniBand SR-IOV vif type allows Virtual PCI device (VF)
to be directly mapped to the guest, allowing higher performance
and advanced features such as RDMA (remote direct memory access).

Problem description
===================

Till Juno Release (including) InfiniBand (IB) SR-IOV networking was possible
via out of the tree nova vif driver with neutron Mellanox Ml2 Mechanism Driver.
Since Juno Ethernet SR-IOV device vNIC is supported by nova, and may be
leveraged for IB SR-IOV device.
IB SR-IOV vif plugging logic should be added to LibvirtGenericVIFDriver.

Use Cases
----------

InfiniBand (IB) is popular, open standard, high performance and
extreme efficiency interconnect protocol. To enable Big Data, High Performance
Computing (HPC) and other similar use cases the guest requires direct access
to IB NIC device.

Project Priority
-----------------

None

Proposed change
===============

This change adds vif_driver support for vif_type VIF_TYPE_IB_HOSTDEV
as part of the GenericLibvirtVifDriver.
Currently, there is no standard API to set InfiniBand vGuid (equivalent for
Ethernet mac address), therefore special driver utility will be used to set it.
This utility is already used in case of mlnx_direct vif_type.

In the neutron VIF_TYPE_HOSTDEV is already supported by ML2 Mellanox
Mechanism Driver and enables networking configuration of SR-IOV Virtual
Functions on IB Fabric. The vif_type name should be renamed to
VIF_TYPE_IB_HOSTDEV to indicate specific InfiniBand vif_type.

Alternatives
------------

Currently there is no valid alternative.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Execution of the dedicated 'ebrctl' utility requires the use of sudo.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

To use this feature the deployer must use Infiniband enabled network adapters.
Infiniband Subnet Manager should be running to enable IB Fabric.
The 'ebrctl' utility should be installed on compute nodes.

Deployers need to be aware of the limitations:
* There will be no smooth upgrade path from the out of tree solution [3] to
the current solution.
* The out of tree solution [3] will be deprecated.

Developer impact
----------------

This blueprint will have no developer impact.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Moshe Levi

Other contributors:
  Irena Berezovsky

Work Items
----------

* Add vif_type ib_hostdev support to LibvirtGenericVIFDriver

Dependencies
============

proprietary 'ebrctl' library is required. This is installed as part
of the Driver OFED package.

Testing
=======

* Unit tests will be added to validate these modifications.
* Adding Third party testing for nova with SR-IOV Infiniband NIC
* Third party testing for neutron is already in place:
  https://wiki.openstack.org/wiki/ThirdPartySystems/Mellanox_CI



Documentation Impact
====================

No documentation changes for Nova are anticipated.
VIF_TYPE_IB_HOSTEV will be automatically enabled by Neutron where appropriate.

References
==========

[1] Infiniband openstack solution documentation:
  https://wiki.openstack.org/wiki/Mellanox-Neutron-Icehouse-Redhat#InfiniBand_Network
[2] Mellanox ML2 Mechanism Driver:
  https://github.com/openstack/neutron/blob/master/neutron/plugins/ml2/drivers/mlnx/mech_mlnx.py
[3] Out of the tree VIF_TYPE_HOSTDEV vif driver:
  https://github.com/mellanox-openstack/mellanox-vif
