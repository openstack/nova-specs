..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Lightbits LightOS(TM) Nova Spec
===============================

https://blueprints.launchpad.net/nova/spec/nova-support-lightos-driver

Lightbits Labs(TM) (http://www.lightbitslabs.com) LightOS(R) is software-defined,
cloud native, high-performance, scale-out and redundant clustered NVMe/TCP
storage that performs like local NVMe flash.

The nova Lightbits LightOS libvirt volume driver works with LightOS
support for cinder and os_brick to enable openstack environments using
nova/libvirt to connect to LightOS storage clusters.

Problem description
===================

LightOS provides persistent volume storage. In normal flow, cinder
triggers volume creation/deletion and attachment/detachment through
the nova libvirt LightOS volume driver. In abnormal conditions (e.g.,
when the nova node has gone down for reboot or power failure and then
come back up, or on nova restart) the volume driver queries which
instances exist on startup and what storage they were connected to (if
any). For any instances that were connected to LightOS, the libvirt
LightOS volume driver together with the os_brick LightOS connector
will reestablish the connection to LightOS for those instances and
volumes.

Use Cases
---------

As an operator I would like to leverage LightOS with openstack to get
highly-performing (performs the same as local NVMe SSDs) remote
storage over NVMe/TCP for my openstack clouds, with failure-resistance
both on the storage drive level and the storage server level. I want
the performance of local NVMe drives with the convenience and
flexibility of remote storage, while knowing that I am secure and my
instances will remain connected to their storage even if drives and
storage nodes fail.

Proposed change
===============

We add a new libvirt volume driver to nova that will provide
functionalities of attach, detach and extend to a LightOS cluster
volume, as well as querying which instances exist on startup (e.g.,
after reboot of power failure). This is being added concurrently with
the LightOS support for cinder and for os_brick.

NVMe/TCP volumes are host mounted. The os_brick connector connects as
needed to the LightOS cluster via NVMe/TCP and exposes host device
files to the nova node. From the libvirt/QEMU point of view, the files
are then attached/detached to instances.

Although LightOS works with VMware and other container and
virtualization environments as well, LightOS openstack support is
limited to libvirt-based environments.

Live migration with multi-attach is fully supported and there are no
special network requirements. LightOS works via NVMe/TCP that works
over any TCP/IP network. The LightOS cluster needs to be reachable
(routable) over TCP/IP from the compute nodes and network bandwidh
should be provisioned to support the desired storage traffic.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The LightOS volumes are first mounted by the libvirt host, which then
passes them to QEMU as local host files to attach/detach to
instances.

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

LightOS cluster must be installed and configured and the The Lightbits
Labs discovery-client service must run on compute nodes. For more
details, see the README included with the cinder driver:
https://review.opendev.org/c/openstack/cinder/+/821602

Developer impact
----------------

None


Upgrade impact
--------------

Generally, there is no impact on upgrades.
During rolling upgrades where some compute nodes may have been upgraded
with LightOS support and some haven't been upgraded yet, the operator should
use either traits or use a placement aggregate to make sure cinder only places
instances using LightOS storage on nova-computes that have been updated.


Implementation
==============

Assignee(s)
-----------

Yuval Brave (yuval@lightbitslabs.com)

Feature Liaison
---------------

None

Work Items
----------

* create a new volume driver for lightos
* upgrade os-brick to use a new os-brick with the LightOS connector

Dependencies
============

The LightOS libvirt volume driver requires the corresponding LightOS
cinder driver and os_brick support.  Cinder blueprint is at:
https://blueprints.launchpad.net/cinder/+spec/cinder-lightos-driver
https://review.opendev.org/c/openstack/cinder/+/821602
https://review.opendev.org/c/openstack/os-brick/+/821603


Testing
=======

Unit tests were added to the patch. Lightbits LightOS third party CI
is hosted by Lightbits Labs.

Documentation Impact
====================

Documentation for configuring lightos storage will be added to:
https://review.opendev.org/c/openstack/cinder/+/821602/10

References
==========

None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
