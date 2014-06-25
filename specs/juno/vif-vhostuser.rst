..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Create VIF_VHOSTUSER
====================

https://blueprints.launchpad.net/nova/+spec/vif-vhostuser

We propose to add a new VIF type to support the new QEMU vhost-user
feature. vhost-user is a new QEMU feature that supports efficient
Virtio-net I/O between a guest and a user-space vswitch. vhost-user is
the userspace equivalent to /dev/vhost-net and is based on a Unix
socket for communication instead of a kernel device file.


Problem description
===================

QEMU has a new type of network interface, vhost-user, and we want to
make this available to Neutron drivers. This will support deploying
high-throughput userspace vswitches for OpenStack-based NFV
applications. (This is the reason that vhost-user was developed.)


Proposed change
===============

This change defines nova.network.model.VIF_TYPE_VHOSTUSER.

We propose to add VIF_VHOSTUSER to Nova for creating network
interfaces based on vhost-user. This VIF type would be enabled by
Neutron drivers that want to assign certain ports to a userspace agent
(vswitch) that is based on vhost-user.

VIF_VHOSTUSER is to be implemented by extending the Libvirt driver.
Libvirt support for vhost-user is currently under review and we expect
it to be merged in time for Juno. We see that upstream Libvirt support
for vhost-user is a dependency for merging the VIF_VHOSTUSER
implementation into Nova.


Alternatives
------------

Intel DPDK has a separate mechanism for accessing vhost from
userspace, based on replacing /dev/vhost-net with a FUSE-based device
file that traps ioctls into userspace. However, vhost-user is the new
standard way to achieve this and is upstream in QEMU.


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

vhost-user will make OpenStack compatible with vswitches supporting N
x 10G Virtio-net workloads.


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
  Luke Gorrie <lukego>

Other contributors:
  m.paolino

Work Items
----------

* Add vhost-user support to the Libvirt driver.
* Add VIF_VHOSTUSER support to Nova.

Dependencies
============

* Libvirt must add support for vhost-user. Current patch under review:
  http://www.redhat.com/archives/libvir-list/2014-July/msg00111.html

* VIF_VHOSTUSER will enable the Neutron driver for Snabb NFV:
  https://blueprints.launchpad.net/neutron/+spec/snabb-nfv-mech-driver
  http://snabb.co/nfv.html
  http://github.com/SnabbCo/snabbswitch


Testing
=======

VIF_VHOSTUSER will be Tempest-tested by the planned 3rd party CI
integration for the Snabb NFV mech driver.


Documentation Impact
====================

No documentation changes for Nova are anticipated. VIF_VHOSTUSER will
be automatically enabled by Neutron where appropriate.


References
==========

* vhost-user:
  http://www.virtualopensystems.com/en/solutions/guides/snabbswitch-qemu/

* Snabb NFV (initial vswitch supporting vhost-user): http://snabb.co/nfv.html

* Deutsche Telekom TeraStream project (initial user of VIF_VHOSTUSER):
  http://blog.ipspace.net/2013/11/deutsche-telekom-terastream-designed.html

* Discussion from NFV BoF (Atlanta) etherpad:
  https://etherpad.openstack.org/p/juno-nfv-bof

