..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Libvirt runtime image type
==========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/runtime-image-type

Libvirt qemu/parallels hypervisor is capable to deal with different images
type. With this change we are going to add an ability to use a supplied image
without converting it according to images_type config parameter.

Problem description
===================

Currently nova libvirt driver sticks to a configured by a nova.conf image type.
It is not possible to use supplied image without conversion in case it differs
from specified or default one. Libvirt currently supports the following image
backends: RBD, LVM, QCOW2, RAW, PLOOP. It is inflexible to limit one node just
for one type of image.

Use Cases
----------

Let a user be flexible about image types usage on different compute nodes.
This would allow them to use all existing catalog of images across all compute
nodes without necessity to reconfigure this by images_type parameter.

Proposed change
===============

LibvirtDriver has a field called image_backend which is initialized just once
when compute service starts. Let it be in an instance property rather than a
property of the compute service.
So, we introduce a new parameter CONF.libvirt.images_type_mapping, which
controls image_backend in a more sophisticated way. This new configuration
parameter is a list of mappings as follows:

images_type_mapping = <source image type1>:<backend image type1>,
              <source image type2>:<backend image type2> ... and so on.

If a provided image is not presented in images_type_mapping list, then it is
converted to the format defined by images_type parameter.

Correctness of the supplied CONF.libvirt.images_type_mapping should be made by
code. In case of invalid input an exception should be thrown by a parsing
function.

Examples:
---------

Correct:
images_type = default
images_type_mapping = raw:lvm, ploop:ploop

images_type = lvm
images_type_mapping = qcow2:qcow2

images_type = qcow2
images_type_mapping = raw:raw, ploop:ploop

images_type = default
images_type_mapping = raw:raw, qcow2:qcow2

images_type = default
images_type_mapping =

Incorrect:
# ambiguous conversion rule for qcow2 format (qcow2->raw or qcow2->qcow2)
images_type = default
images_type_mapping = qcow2:raw, qcow2:qcow2

# ambiguous conversion rule for raw format (raw->rbd or raw->lvm)
images_type = default
images_type_mapping = raw:rbd, raw:lvm

# invalid source format (lvm and rbd can't be specified as a source)
images_type = default
images_type_mapping = lvm:rbd, rbd:rbd

Alternatives
------------

Let it be as it is.

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

A new ListOpt parameter CONF.libvirt.images_type_mapping is added to nova.conf
file.

Performance Impact
------------------

None.

Other deployer impact
---------------------

A new parameter CONF.libvirt.images_type_mapping should be specified if a user
is interested in altering current behavior, which should be seamless in
upgrade.

Developer impact
----------------

Other hypervisors detect particular type of image mostly in runtime. Hyperv,
for instance, detects vhd or vhdx by header and doesn't need to specify which
one to use by config.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Maxim Nestratov mnestratov@virtuozzo.com

Other contributors:
  Dmitry Guryanov dguryanov@virtuozzo.com

Work Items
----------

* Introduce ListOpt images_type_mapping config option.
* Implement parsing images_type_mapping complying with current images_type
  parameter.
* Implement image_backend as a property of an instance rather than a service.

Dependencies
============

None.

Testing
=======

Functional test is going to be implemented.

Documentation Impact
====================

It should be reflected in documentation that a new nova.conf parameter
images_type_mapping is introduced as described above.

References
==========

None.

