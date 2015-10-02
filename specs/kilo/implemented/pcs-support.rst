=====================================================
Parallels Cloud Server support in nova/libvirt driver
=====================================================

https://blueprints.launchpad.net/nova/+spec/pcs-support

This specification is intended to describe process of extending nova/libvirt
driver in order to support Parallels Cloud Server [1]_

Problem description
===================

Parallels Cloud Server (PCS) is a virtualization solution product, which
enables service providers to use container and hypervisor virtualization
technology via the same management tools and API.
Though PCS is supported by libvirt it is absent in OpenStack for now due to
not only specific demand related to compute node deployment but also
different disk image format implied by usage of Parallels disk loopback block
device [2]_, domains configuration and supported features.

Use Cases
----------

This change will allow those service providers that use PCS as their
primary virtualization solution to build a cloud upon it using OpenStack.
There is no impact on users who aren't engaged with PCS.

Project Priority
-----------------

No priority defined for this feature yet.

Proposed change
===============

To make PCS be supported by OpenStack we need to modify nova/libvirt driver
mostly regarding a new type of virtualization processing.
The end user will be able to configure nova to use PCS by setting
libvirt.virt_type option to "parallels". Also, as a native disk format for
both VMs and containers supported in PCS is ploop [2]_, to get best performance
we will need to change glance-api configuration to support PCS ploop format.
Using images of different formats will be provided by in-place convertion.
As each host reports supported instances via the resource tracker and
the 'vm_mode' property of images is used to determine what kind of
virtualization to run an a particular host, a decision about it will be made
on an image with particular vm_mode property (eg vm_mode=exe to run containers
or vm_mode=hvm to run hypervisor based instances). So PCS hosts will support
arbitrary mix of machine and container based guests.
In case a cloud administrator needs a way to partition hosts into groups so
that some hosts exclusively run machine virt, while other hosts exclusively
run container virt, host aggregates and flavors extra specs should be used.

nova.conf extract example:
[libvirt]
...
virt_type = parallels
images_type = ploop
...

glance-api.conf extract example:
...
disk_formats=ami,ari,aki,vhd,vmdk,raw,qcow2,vdi,iso,ploop
...

Here is a list of of features we plan to support:

+-----------------------+------+-------------+
|                       |  VMs |  Containers |
+=======================+======+=============+
| Launch                |  yes |         yes |
+-----------------------+------+-------------+
| Reboot                |  yes |         yes |
+-----------------------+------+-------------+
| Terminate             |  yes |         yes |
+-----------------------+------+-------------+
| Resize                |  yes |         yes |
+-----------------------+------+-------------+
| Rescue                |  yes |         yes |
+-----------------------+------+-------------+
| Pause                 |  yes |         (1) |
+-----------------------+------+-------------+
| Un-pause              |  yes |         (1) |
+-----------------------+------+-------------+
| Suspend               |  yes |         yes |
+-----------------------+------+-------------+
| Resume                |  yes |         yes |
+-----------------------+------+-------------+
| Inject Networking     |  yes |         yes |
+-----------------------+------+-------------+
| Inject File           |  yes |         yes |
+-----------------------+------+-------------+
| Serial Console Output |  yes |          no |
+-----------------------+------+-------------+
| VNC Console           |  yes |         yes |
+-----------------------+------+-------------+
| SPICE Console         |   no |          no |
+-----------------------+------+-------------+
| RDP Console           |   no |          no |
+-----------------------+------+-------------+
| Attach Volume         |  yes |         (2) |
+-----------------------+------+-------------+
| Detach Volume         |  yes |         (2) |
+-----------------------+------+-------------+
| Live Migration        |  yes |         yes |
+-----------------------+------+-------------+
| Snapshot              |  yes |         yes |
+-----------------------+------+-------------+
| iSCSI                 |  yes |         yes |
+-----------------------+------+-------------+
| iSCSI CHAP            |  yes |         yes |
+-----------------------+------+-------------+
| Fibre Channel         |  yes |         yes |
+-----------------------+------+-------------+
| Set Admin Pass        |  yes |         yes |
+-----------------------+------+-------------+
| Get Guest Info        |  yes |         yes |
+-----------------------+------+-------------+
| Glance Integration    |  yes |         yes |
+-----------------------+------+-------------+
| Service Control       |   no |         yes |
+-----------------------+------+-------------+
| VLAN Networking       |  yes |         yes |
+-----------------------+------+-------------+
| Flat Networking       |  yes |         yes |
+-----------------------+------+-------------+
| Security Groups       |  yes |         yes |
+-----------------------+------+-------------+
| Firewall Rules        |  yes |         yes |
+-----------------------+------+-------------+
| nova diagnostics      |   no |          no |
+-----------------------+------+-------------+
| Config Drive          |  yes |         yes |
+-----------------------+------+-------------+
| Auto configure disk   |   no |         yes |
+-----------------------+------+-------------+
| Evacuate              |  yes |         yes |
+-----------------------+------+-------------+
| Volume swap           |  yes |         (3) |
+-----------------------+------+-------------+
| Volume rate limiting  |  (4) |         (4) |
+-----------------------+------+-------------+

(1) There are no technical problems with pausing containers it's
    not implemented by now.
(2) It's possible to attach volume to a container either as a block device or
    as a mount point, giving both types of access simultaneously has a
    security problem.
(3) We can tune swap size in containers with vswap technology [4]_,
    not as a conventional swap disk.
(4) We can tune IO rate only for the whole instance but
    not for individual volumes.

Alternatives
------------

The alternate way is to implement a separate PCS nova driver like this [3]_,
which was implemented in terms of PCS + OpenStack proof of concept.

pros:
* There is no middle layer between OpenStack and PCS as pcs-nova-driver uses
native PCS's python API.
* Changes in pcs-nova-driver will not affect nova/libvirt's code.

cons:
* Yet another nova driver
* It is out-of-tree driver

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

None.

Other deployer impact
---------------------

Compute nodes available for "parallels" type of virtualization have to be
deployed in advance. Integrating PCS hosts deployment with OpenStack is out
of this spec scope.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dguryanov

Other contributors:
  burluka
  mnestratov

Work Items
----------
* Enhance libvirt driver to support new virt_type value.
* Implement all the functionality necessary to support PCS in libvirt driver

Dependencies
============
Add support of new disk image format in glance
Bluesprint https://blueprints.launchpad.net/glance/+spec/pcs-support

None

Testing
=======
Testing in the gate will be provided by currently being established Parallels
CI testing system.

Documentation Impact
====================

New type of virtualization provider should be noticed and host deployment
pre-requisites such as the need to have PCS installed on compute nodes.

References
==========

.. [1] Parallels Cloud Server http://www.parallels.com/products/pcs
.. [2] Ploop block device http://openvz.org/Ploop
.. [3] PCS nova driver https://github.com/parallels/pcs-nova-driver
.. [4] OpenVZ kernel memory management model https://openvz.org/VSwap
