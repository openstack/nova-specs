..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Add differencing vhdx resize support in Hyper-V Driver
======================================================

https://blueprints.launchpad.net/nova/+spec/add-differencing-vhdx-resize-support

Differencing VHDX images can be resized, unlike differencing VHD images. Even
so, the Nova Hyper-V driver currently does not support this.

This feature is required for resizing existing instances which use CoW VHDX
images and also in order to resize the root disk image when spawning a new
instance.

Problem description
===================

Currently, when using the Hyper-V Nova Driver and differencing (CoW) VHDX
images for the instances, the differencing image will not get resized according
to the flavor size. Instead, the VM root image will keep having the same size
as the base image used when spawning a new instance.

Also, when trying to resize such an instance, not only that the disk image will
not get resized, but this will actually raise an exception as currently the
method which gets the internal maximum size of a vhd/vhdx does not support
differencing images.


Proposed change
===============

The solution is simply passing the desired size when creating a new
differencing vhdx image. Not passing it will result in the new disk having the
same size as the base image.

Also, it is required that the method which gets the internal maximum size of
a vhdx to lookup the parent disk and return the according size instead of
raising an exception.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <lpetrut@cloudbasesolutions.com>

Work Items
----------

Add a "size" argument to the create_differencing_vhd method.

Adapt the vmops module to specify the new size only if resize is required
when booting a new instance using CoW vhdx images.

Lookup for the parent image and get the according size when getting the
maximum internal size of a vhdx.

Adapt the vhdutils according methods in order to have the same method
signatures and keep consistency.

Dependencies
============

None

Testing
=======

Testing this feature will be covered by the Hyper-V CI.

Documentation Impact
====================

None

References
==========

Official VHDX format specs:
http://www.microsoft.com/en-us/download/details.aspx?id=34750
