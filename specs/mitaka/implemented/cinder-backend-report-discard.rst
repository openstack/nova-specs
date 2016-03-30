..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Add ability to support discard/unmap/trim for Cinder backend
============================================================

https://blueprints.launchpad.net/nova/+spec/cinder-backend-report-discard

Currently, libvirt/qemu has support for a discard option when attaching a
volume to an instance. With this feature, the unmap/trim command can be sent
from guest to the physical storage device.

A cinder back-end will report a connection capability that Nova will use
in attaching a volume.

Problem description
===================

Currently there is no way for Nova to know if a Cinder back end supports
discard/trim/unmap functionality. Functionality is being added in Cinder
to supply this information. The spec seeks to add the ability to consume
that information.

Use Cases
---------

If a Cinder backend uses media that can make use of discard functionality
there should be a way to do this. This will improve long term performance
of such back ends.

Proposed change
===============

Code will be added to check for a 'discard' property returned to Nova from
the Cinder attach API. When present and set to True we will modify the config
returned by the libvirt volume driver to contain::

  driver_discard = "unmap"

This will only give the desired support if the instance is configured with a
interface and bus type that will support Trim/Unmap commands. In the case where
it is possible to detect that discard will not actually work for the instance
we will log a warning, but continue on with the attach anyway.

Currently the virtio-blk backend does not support discard.

There will be several ways to get an instance that will support discard, one
example is to use the virtio-scsi storage interface with a scsi bus type. To
create an instance with this support it must be booted from an image
configured with ``hw_scsi_model=virtio-scsi`` and ``hw_disk_bus=scsi``.

It is important to note that the nova.conf option hw_disk_discard is NOT read
for this feature. We rely entirely on Cinder to specify whether or not discard
should be used for the volume.

Alternatives
------------

Alternatives include adding discard for all drives if the operator has set
hw_disk_discard but it was decided this was not a good way to solve the
problem as you could not mix different underlying volume providers easily.

We could also hot-plug a SCSI controller that is capable of supporting discard
when attaching Cinder volumes. This would allow for mixing a non-trim boot
disk from an image and then attaching a Cinder volume that would get the
benefits. The risk is that the instance may not be able to actually support
doing UNMAP.


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

There will be a performance gain for back ends that benefit from having
discard functionality.

See https://en.wikipedia.org/wiki/Trim_(computing) for more info.

Other deployer impact
---------------------

Deployers wanting to use this feature with their Cinder backend will need to
ensure the instances are configured with a SCSI model and bus that support
discard. This includes IDE, AHCI, and Xen disks. virtio-blk is the only
backend missing this support.

A simple way to enable this is to modify Glance images to contain the
following properties::

  hw_scsi_model=virtio-scsi
  hw_disk_bus=scsi

In addition compute nodes will need to be using libvirt 1.0.6 or higher and
QEMU 1.6.0 or higher.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
*  Patrick East

Work Items
----------

* Modify volume attach code in libvirt driver to check for the new Cinder
  connection property.
* Add unit tests for new functionality, modify any existing as needed.
* Configure Pure Storage 3rd party CI system to enable the feature and
  validate it as a Cinder CI. This configuration change will be made available
  to any other 3rd party CI maintainer to allow additional systems to test with
  this feature enabled.

Dependencies
============

Cinder Blueprint (Completed and released in Liberty):
  https://blueprints.launchpad.net/cinder/+spec/cinder-backend-report-discard


Testing
=======

Unit tests needs to include all permutations of the discard
flag from Cinder.

We could enable one of the jenkins jobs to be configured to enable this. A nice
starting point would maybe be the Ceph jobs. Potentially a Tempest test could
be added behind a config option to validate volume attachments do get the
correct discard settings.


Documentation Impact
====================

We may want to add documentation to the Cloud Administrator Guide on how to
utilize this feature.

References
==========

Cinder Blueprint:
  https://blueprints.launchpad.net/cinder/+spec/cinder-backend-report-discard

Cinder Spec:
  http://specs.openstack.org/openstack/cinder-specs/specs/liberty/cinder-backend-report-discard.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced