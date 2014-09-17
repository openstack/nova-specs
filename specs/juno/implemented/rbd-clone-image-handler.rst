..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Storage: Copy-on-write cloning for RBD-backed disks
===================================================

https://blueprints.launchpad.net/nova/+spec/rbd-clone-image-handler

Currently RBD-backed ephemeral disks are created by downloading an image from
Glance to a local file, then uploading that file into RBD. Even if the file is
cached, uploading may take a long time, since 'rbd import' is synchronous and
slow. If the image is already stored in RBD by Glance, there's no need for any
local copies - it can be cloned to a new image for a new disk without copying
the data at all.


Problem description
===================

The primary use case that benefits from this change is launching an instance
from a Glance image where Ceph RBD backend is enabled for both Glance and Nova,
and Glance images are stored in RBD in RAW format.

Following problems are addressed:

* Disk space on compute nodes is wasted by caching an additional copy of the
  image on each compute node that runs instances from that image.

* Disk space in Ceph is wasted by uploading a full copy of an image instead of
  creating a copy-on-write clone.

* Network capacity is wasted by downloading the image from RBD to a compute
  node the first time that node launches an instance from that image, and by
  uploading the image to RBD every time a new instance is launched from the
  same image.

* Increased time required to launch an instance reduces elasticity of the cloud
  environment and increases the number of in-flight operations that have to be
  maintained by Nova.


Proposed change
===============

Extract RBD specific utility code into a new file, align its structure and
provided functionality in line with similar code in Cinder. This includes the
volume cleanup code that should be converted from rbd CLI to using the RBD
library.

Add utility functions to support cloning, including checks whether image exists
and whether it can be cloned.

Add direct_fetch() method to nova.virt.libvirt.imagebackend, make its
implementation in the Rbd subclass try to clone the image when possible.
Following criteria are used to determine that the image can be cloned:

* Image location uses the rbd:// schema and contains a valid reference to an
  RBD snapshot;

* Image location references the same Ceph cluster as Nova configuration;

* Image disk format is 'raw';

* RBD snapshot referenced by image location is accessible by Nova.

Extend fetch_to_raw() in nova.virt.images to try direct_fetch() when a new
optional backend parameter is passed. Make the libvirt driver pass the backend
parameter.

Instead of calling disk.get_disk_size() directly from verify_base_size(), which
assumes the disk is stored locally, add a new method that is overridden by the
Rbd subclass to get the disk size.

Alternatives
------------

An alternative implementation based on the image-multiple-location blueprint
(https://blueprints.launchpad.net/glance/+spec/multiple-image-locations) was
tried in Icehouse. It was ultimately reverted, which can be attributed to a sum
of multiple reasons:

* The implementation in https://review.openstack.org/33409 took a long time to
  stabilize, and didn't land until hours before Icehouse feature freeze.

* The impact of https://review.openstack.org/33409 was significantly larger
  than that of the ephemeral RBD clone change that was built on top of it.

* The impact included exposing nova.image.glance._get_locations() method that
  relies on Glance API v2 to code paths that assume Glance API v1, which caused
  LP bug #1291014 (https://bugs.launchpad.net/nova/+bug/1291014).

This design has a significantly smaller footprint, and is mostly isolated to
the RBD image backend in the libvirt driver.

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

When Ceph RBD backend is enabled for Glance and Nova, there will be a
noticeable difference in time and resource consumption when launching instances
from Glance images in RAW and non-RAW formats.

Performance Impact
------------------

In the primary use case defined in the `Problem description`_ section above,
there will be a significant performance improvement.

In other use cases, libvirt driver will introduce one more API call to Glance
to retrieve a list of image locations when RBD backend is enabled. The
performance impact of that call is insignificant compared to the time and
resources it takes to fetch a full image from Glance.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jdurgin

Other contributors:
  angdraug

Work Items
----------

Current implementation (see `References`_) consists of following changes:

* Move libvirt RBD utilities to a new file

* Use library instead of CLI to cleanup RBD volumes

* Enable cloning for rbd-backed ephemeral disks


Dependencies
============

None.


Testing
=======

This is a non-functional change with no impact on the test cases that need to
be covered.

There is work currently going on to get all of tempest running against an
environment using Ceph in the OpenStack CI environment.  The first step is ceph
support for devstack, which you can see here:

    https://review.openstack.org/#/c/65113

There's also a test devstack patch with forces ceph to be enabled, which
results in all of the devstack jobs being run with ceph enabled.  You can find
that here:

    https://review.openstack.org/#/c/107472/

There are some tests failing (14 and 15 the first couple of runs).  However,
that also means that the vast majority of tests that cover this code (anything
that spawns an instance) are passing.  So, we at least have a way to run these
tests on demand against master.  Once the devstack patch merges, we will enable
a job that can run against patches in all projects (perhaps experimental to
start with).

Fuel CI also includes a suite of tests for OpenStack deployments with Ceph:
https://github.com/stackforge/fuel-main/blob/master/fuelweb_test/tests/test_ceph.py


Documentation Impact
====================

None.


References
==========

Mailing list discussions:
http://lists.openstack.org/pipermail/openstack-dev/2014-March/029127.html
http://lists.ceph.com/pipermail/ceph-users-ceph.com/2014-March/008659.html

Current implementation:
https://github.com/angdraug/nova/tree/rbd-ephemeral-clone
https://review.openstack.org/#/q/status:open+topic:bp/rbd-clone-image-handler,n,z
