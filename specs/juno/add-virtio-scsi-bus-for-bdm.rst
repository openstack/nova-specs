..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Add virtio-scsi bus support for block device mapping
=====================================================

https://blueprints.launchpad.net/nova/+spec/add-virtio-scsi-bus-for-bdm


VirtIO SCSI is a new para-virtualized SCSI controller device for KVM instances.
It has been designed to replace virtio-blk, increase it's performance and
improve scalability. Currently, using virtio-scsi bus is not supported when
booting from volume.



Problem description
===================

VirtIO SCSI is a new para-virtualized SCSI controller device for KVM instances.
It has been designed to replace virtio-blk, increase it's performance and
improve scalability. The interface is capable of handling multiple block
devices per virtual SCSI adapter, keeps the standard scsi device naming
in the guests (e.x /dev/sda) and support SCSI devices passthrough.

Currently, virtio-scsi bus has been supported when booting from glance image,
which is implemented by BP ([1]) aimed to Icehouse.

However, when we create a cinder volume from this image, and then booting
from this volume and specify the bus_type as "scsi", the guest will still
use lsi controller instead of virtio-scsi controller.

The aim of this BP as follows:

When booting from volume with "scsi" bus type, use virtio-scsi controller
for volume which was created from glance image, which is set with
"virtio-scsi" hw_scsi_model property.

The main use case is to improve performance in I/O-intensive applications.


Proposed change
===============

* Nova retrieve "hw_scsi_model" property from volume's glance_image_metadata
  when booting from cinder volume

* Libvirt driver will create the "virtio-scsi" controller if "hw_scsi_model"
  property is "virtio-scsi" and the bus_type specified for volume is "scsi"

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

Will improve guest's performance.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <zhangleiqiang@huawei.com>


Work Items
----------

* Nova retrieve "hw_scsi_model" property from volume's glance_image_metadata
  when booting from cinder volume

* Libvirt driver will create the "virtio-scsi" controller if "hw_scsi_model"
  property is "virtio-scsi" and the bus_type specified for volume is "scsi"


Dependencies
============

* Depend on the BP [1], which will provide the virtio-scsi-controller object

Testing
=======

None

Documentation Impact
====================

None

References
==========

* [1] https://blueprints.launchpad.net/nova/+spec/libvirt-virtio-scsi-driver
