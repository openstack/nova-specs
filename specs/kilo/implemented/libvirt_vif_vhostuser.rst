..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Add VIF_VHOSTUSER vif type to libvirt driver
============================================

https://blueprints.launchpad.net/nova/+spec/libvirt-vif-vhost-user

We propose to add a new VIF type to support the new QEMU vhost-user
interface in libvirt dirver. vhost-user is a new QEMU feature that supports
efficient Virtio-net I/O between a guest and a user-space vswitch.
vhost-user is the userspace equivalent to /dev/vhost-net and is based on
a Unix socket for communication instead of a kernel device file.

Problem description
===================

QEMU has a new type of network interface, vhost-user, and we want to
make this available to Neutron drivers. This will support deploying
high-throughput userspace vswitches for OpenStack-based applications.
There are two types of vSwitches that can use vhost-user
interface, a generic vhost-user vSwitch and ovs based one, both types
should be supported.

Use Cases
---------

This change will allow running userspace vSwitches using vhost-user
interface. Both generic vhost-user vSwitches and OVS based vSwtiches
will be supported.

Project Priority
----------------

No

Proposed change
===============

We propose to add VIF_VHOSTUSER to Nova for creating network
interfaces based on vhost-user. This VIF type would be enabled by
Neutron drivers by using portbindings extension and setting the
vif_type to VIF_VHOSTUSER. To support both generic and ovs based
vSwitches additional information will be passed in vif_details.
For ovs based vSwitches plug/unplug methods will create/remove
an ovs port if 'vhost_user_ovs_plug' is set to True in the vif_details.

VIF_VHOSTUSER driver will allow Neutron mechanism drivers to specify
if qemu should work in server or client mode. Mechanism drivers
could pass 'vhost_user_mode' in vif_details to specify the mode.
The name of the socket will be the same as ID of the Neutron port.
For ovs based vSwitches name of the socket will be the same as name
of the ovs port.

Alternatives
------------

In Juno cycle there were two initiatives to support userspace vhost user
in Nova. One was based on vhost-user interface in Qemu the other was based
on DPDK implementation. Since DPDK is moving to support vhost-user only one
driver is needed.

Alternatively a mechanism for plugging in vif libvirt driver could be used
to support
vhost-user in libvirt driver. Such mechanism is proposed here:

https://blueprints.launchpad.net/nova/+spec/libvirt-vif-driver-plugin

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

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Use of VIF_VHOSTUSER will have no inpact on Openstack performance.
Use of userspace vSwitch with vhost-user will improve guest network perforamce.

Other deployer impact
---------------------

VIF_VHOSTUSER does not have to be enabled by the deployer. Neutron
drivers will automatically enable VIF_VHOSTUSER via port binding if
this is the appropriate choice for the agent on the compute host.

VIF_VHOSTUSER will require a version of QEMU with vhost-user support,
which is currently upstream and will be released in QEMU 2.1.

VIF_VHOSTUSER will also require a version of Libvirt with vhost-user
support.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
 Przemyslaw Czesnowicz <pczesno>

Work Items
----------

* Add VIF_VHOSTUSER support to Nova.

Dependencies
============

An ml2 dpdk ovs driver is being proposed for Neutron.
This feature doesn't directly depend on it.

This feature depends on bp/virt-driver-large-pages.


Testing
=======

VIF_VHOSTUSER will be tested by 3rd party CI for the DPDK Ovs mech driver.

Documentation Impact
====================

No documentation changes for Nova are anticipated. VIF_VHOSTUSER will
be automatically enabled by Neutron where appropriate.

References
==========

* vhost-user:
  http://www.virtualopensystems.com/en/solutions/guides/snabbswitch-qemu/

* Snabb NFV (initial vswitch supporting vhost-user): http://snabb.co/nfv.html

* Juno spec for VIF_VHOSTUSER:
  https://review.openstack.org/#/c/96138/

* Juno spec for dpdkvhost
  https://review.openstack.org/#/c/95805/4/specs/juno/libvirt-ovs-use-usvhost.rst

* Neutron dpdk-ovs mechanism driver
  https://blueprints.launchpad.net/neutron/+spec/ml2-dpdk-ovs-mechanism-driver

* Blueprint for vif plugin mechanism.
  https://blueprints.launchpad.net/nova/+spec/libvirt-vif-driver-plugin

* Blueprint for Hugepage support
  https://blueprints.launchpad.net/nova/+spec/virt-driver-large-pages
