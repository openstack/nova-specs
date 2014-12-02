..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add a Quobyte Volume Driver in Nova
==========================================

https://blueprints.launchpad.net/nova/+spec/quobyte-nova-driver

Add a Nova volume driver for the `Quobyte Unified Storage Plane
<http://quobyte.com/>`_ storage system, allowing to attach vm images residing
in Quobyte USP to Nova instances. These images (raw, qcow2) are stored as
files on a Quobyte USP volume.


Problem description
===================

The Quobyte USP provides flexible access to file based storage. Nova can
currently not attach Quobyte USP volumes, although a `Cinder driver
<https://blueprints.launchpad.net/cinder/+spec/quobyte-usp- driver>`_ is
currently in preparation.

Use Cases
----------

Operators can deploy Quobyte USP storage for their Nova installations.

Project Priority
-----------------

None


Proposed change
===============

Add support for the `Quobyte Unified Storage Plane <http://quobyte.com/>`_
to nova.virt.libvirt.volume.py by adding a new class
LibvirtQuobyteVolumeDriver based on the LibvirtBaseVolumeDriver. Code
structure will be similiar to the GlusterFS class
LibvirtGlusterfsVolumeDriver. The Driver will check mountpoint availability,
run mountpoint preparations if required and mount the given Quobyte USP volume
based on the configuration data (connection_info, etc.). Based on the local
qemu 2.0.0+ availability the driver optimizes performance by adopting matching
caching strategies. Other functionalities include volume disconnect (i.e.
unmounting the Quobyte USP volume) and configuration data provisioning
(get_config).


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

None

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

Quobyte USP specific config options are
  * quobyte_mount_point_base (Directory where the Quobyte volume is
    mounted on the compute node)
  * quobyte_client_cfg (Path to a Quobyte Client configuration file)

Mounting Quobyte USP volumes is done as Nova user, not as root. The Nova user
needs to be FUSE enabled, e.g. a member of the fuse group. The deployer has to
install the Quobyte USP software.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <silvan@quobyte.com>

Other contributors:
  <mberlin@quobyte.com>

Work Items
----------

Implementation has been done and tested via Tempest.
The code can be found at `Change-Id:
Ica1820031f1fc8b66d7ed7fe76ffeb985cf0ef35
<https://review.openstack.org/#/c/110722/>`_.


Dependencies
============

This change depends on the addition of disk driver IO policy configurability
as implemented in `Change-Id: Iaaa298029e139690526a61de51b569dd8d34236d
<https://review.openstack.org/#/c/117442/20>`_.

Furthermore the corresponding `Cinder driver
<https://blueprints.launchpad.net/cinder/+spec/quobyte-usp-driver>`_ is
required, the respective code can be found at `Change-Id:
I7ca13e28b000d7a07c2baecd5454e50be4c9640b
<https://review.openstack.org/#/c/94186/>`_.


Testing
=======

Currently no additional Tempest tests are required as the existing tests and
test scenarios cover the volume usage functionalities provided by the driver.
For the corresponding Cinder driver a 3rd party CI is in preparation that will
also test the Nova driver. Unit tests have been created in conjunction with
the existing driver code.


Documentation Impact
====================

None


References
==========

None