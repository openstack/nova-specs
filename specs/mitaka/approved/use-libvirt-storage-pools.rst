..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Use libvirt Storage Pools
=========================

https://blueprints.launchpad.net/nova/+spec/use-libvirt-storage-pools

Currently, the libvirt driver does not make use of libvirt's storage pools
and volumes.  Using libvirt storage pools would simplify adding support for
new image backends, as well as facilitating cold migrations (see follow up
blueprint).


Problem description
===================

Currently, Nova's libvirt driver does not make any use of libvirt volumes
and storage pools.

This means that, for the image backends, we have a lot
of code that deals directly with various images backend formats, and we have
to manually deal with a variety of different situations via various command
line tools and libraries.

However, much of this functionality is already present in libvirt, in the form
of libvirt storage pools, so the libvirt driver duplicates functionality
already present in libvirt itself.

Use Cases
-----------

Developer: This will facilitate removing SSH from resize/migrate, as it will
allow us to use virStorageVolUpload and virStorageVolDownload to migrate
storage.

Developer: Second, this will simplify adding in support for pool types that
are supported by libvirt but not supported by Nova (such as Sheepdog).

Developer: this will (in the long run) simplify the imagebackend code, making
it easier to maintain.

Proposed change
===============

The cache of images downloaded from Glance would be placed into a volume pool
(:code:`nova-base-images-pool`).  This is done simply by instructing libvirt
that Nova's image cache directory (e.g. :code:`/var/lib/nova/_base`) is a
directory storage pool, and as such does not affect directory layout (and is
thus compatible with both the legacy image backends and the new image backend
proposed below).

A new image backend, :code:`LibvirtStorage`, would be introduced.  This would
support being used in place of all of the current types (with the exeception of
RBD support, which for the time being would need a subclass [1]_).

If we are not using COW, the libvirt :code:`pool.createXMLFrom` method
could be used to appropriately copy the template image from the source pool,
:code:`nova-base-images-pool`, into the target image in the target pool
`nova-disks-pool`.  This works regardless of the source and destination formats
(for instance, the same function calls are used to copy from raw to LVM or
from qcow2 to raw).

If we are using COW, the libvirt :code:`pool.createXML` method could be used
with a :code:`backingStore` element, which will appropriately create the new
QCOW2 file with the backing file as the file in the image cache.

This has the additional benefit of paving the way for the simplification of the
image cache manager -- instead of having to run an external executable to check
if an image is in the qcow2 format and has a backing store, we can simply check
the :code:`backingStore` element's :code:`path` subelement for each
libvirt volume (this also makes the code less brittle, should we decide to
support other formats with backing stores) [2]_.

A similar approach could be used with :code:`extract_snapshot` -- use
:code:`createXMLFrom` to duplicate the libvirt volume (the new XML we pass
in can handle compression, etc) into a temporary directory pool.

In order to associate images with instances, the volumes in `nova-disks-pool`
would have a name of the form `{instance-uuid}_{name}` (with :code:`name` being
"disk", "kernel", etc, depending on the name passed to the image creation
method).  This way, it still remains easy to find the disk image associated
with a particular instance.  This is the same name format used for the legacy
LVM and RBD backends.

A configuration variable named :code:`[libvirt]use_storage_pools` would enable
or disable the storage pool functionality, and would be set to true by default.
However, the legacy backends would be left in place to maintain the live
upgrade functionality (e.g. Juno->Kilo). See the `Other deployer impact`_
section below for more information.

For the :code:`disk` XML element in the :code:`domain` element supplied to
libvirt on instance creation, a type of :code:`volume` can be supplied, with
the :code:`<source>` element specifying the pool name and volume name [3]_.

.. [1] Currently, libvirt does not have support for the createXMLFrom operation
   for RBD-backed pools, so for RDB support, we would have to subclass the new
   backend and add in code to manually upload the template image.  This
   functionality should be present in a future version of libvirt. See
   `Red Hat BZ 1089079 <https://bugzilla.redhat.com/show_bug.cgi?id=1089079>`_.

.. [2] For the time being both the legacy backing storage detection code and
   the new detection code would have to coexist.  However, once we remove the
   legacy image backends (in L), the legacy detection code would be removed.

.. [3] Note that this XML is only available in libvirt version 1.0.5 and up.
   If we wish to support a version older than this in Kilo, we could use the
   libvirt volume XML to extract the necessary data to construct appropriate
   disk XML similar to what we currently use.  This legacy code would be
   removed once the minimum libvirt version is set to 1.0.5 or higher.

Alternatives
------------

The setup described in this document calls for using a single storage pool
for all VMs on a system.

When using a file-based backend, this would require storing disk images in a
single directory (such as :code:`/var/lib/nova/instance/disks`) instead of the
current setup, where the disk images are stored in the instance directory
(:code:`/var/lib/nova/instances/{instance-id}`).  This is due to the way that
the libvirt :code:`dir` storage pool works.

While it would be possible to create a new storage pool for each instance,
this would only be applicable for file-based backends.  Having different
functionality between file-based backends and other backends would complicate
the code and reduce the abstraction introduced by this blueprint.

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

Since the :code:`createXMLFrom` is actually intelligent about creating and
copying image files (for instance, it calls :code:`qemu-img` under the hood
when appropriate), there should be no performance impact.  As per what is
mentioned in the `Proposed change`_ section, we would maintain current image
cache functionality, including support for COW (via QCOW2), while paving the
road for other file formats that libvirt supports as well.

Other deployer impact
---------------------

For live migration/upgrade from OpenStack Juno to OpenStack Kilo, the
legacy image backends (and support for them in Nova's image cache) will be left
in place for the next release (Kilo), but will be marked as deprecated.  In
the L release, the legacy backends will be removed (as well as support for
them in the image cache manager).

when the deployer enables the :code:`[libvirt]use_storage_pools` configuration
options, there would be several effects:

First, Nova would check to see if the :code:`nova-image-cache-pool` and
:code:`nova-disks-pool` already existed.  If not, the
:code:`nova-image-cache-pool` storage pool would be created as a directory pool
in the current image cache directory.  Then, Nova would examine the current
images type and attempt to use existing information to create the
:code:`nova-disks-pool` storage pool.  The automated creation of the main
storage pool would be a temporary measure to assist in the transitioning
process; eventually (after L), this would be removed, since the configuration
options for the legacy backends would also be removed.  This lifts some of the
burden from Nova on interacting with various storage backends -- Nova would
no longer have to have a multitude of configuration options for every storage
backend it supported.

Secondly, all new instances would be created using the storage pool image
backend.  Any currently running instances would continue to use the legacy
image backend.

During operations which allow the changing of libvirt XML, such as cold
migrations, resizes, reboots, and live migrations [4]_, instances would be
automatically transitioned to using the new system.  This would allow
deployers and users to move to the new system at their leisure, since they
could either choose to bulk-restart the VMs themselves, or simply ask the users
to do so when convinient.  For instances still on the legacy system, a warning
would be issued on compute node startup.

For "cold" operations (resizes, reboots, and cold migrations), disk images
would be moved into the storage pool before the virtual machine was
(re)started.  For non-directory-based backends (LVM and RBD), no movement is
necessary, since the name format is the same, and they already use a
centralized location by their very nature.

Then, when Nova went to generate the new XML to boot the VM, the XML would
point to the libvirt storage volume (in the case of a soft reboot, we would
simply update the existing XML).

For live block migrations, we simply create a new, empty image in the storage
pool, and let libvirt fill it up as part of the block migration.  For
shared storage live migrations, we can only transition if the image backend
is Ceph, since there's no reliable way to move a disk file into the storage
pool while the VM is still running without losing data.

.. [4] This will only occur for block live migrations or shared-storage live
   migrations where the legacy image backend is not directory-based (i.e.
   is not 'raw' or 'qcow2').  See below.

Developer impact
----------------

Currently, file-based images for a particular instance are stored in the
instance directory (:code:`/var/lib/nova/instances/{instance-id}`).  In order
to have one storage pool per compute node, libvirt's directory-based storage
pool would require all of the disk images to be stored in one directory, so
the images themselves would no longer be in
:code:`/var/lib/nova/instances/{instance-id}`, but instead in something
to the effect of :code:`/var/lib/nova/instance/disks`.

Should it be desired to have different disk types (e.g. main disk vs swap)
stored differently [5]_, we could simply create a pool for each type, and place
the images into the appropriate pool based on their name.  An advantage to
using pools is that Nova doesn't actually need to know the underlying details
about the pool, only its name.  Thus, if a deployer wanted to move a particular
pool to a different location, device, etc, no XML changes would be needed,
assuming the same pool name was kept.

Code that targets a specific backend type (such as LVM encryption, for
instance) is still possible, since we can ask libvirt for the storage pool
type.

.. [5] As suggested in
   `this blueprint <https://review.openstack.org/#/c/83727>`_, for instance

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    paul-carlton2

Other contributors:
    None

Work Items
----------

1. Modify the code which downloads images from Glance into a cache to
   create a storage pool in the cache directory and refresh the cache
   when a new image is downloaded.

2. Implement the new image backend and sections in the XML config builder to
   accept the :code:`volume` type for disk elements, and make the image cache
   manager aware of how to check libvirt storage volumes for backing stores.

3. Implement the functionality required to support transitional installations
   (detecting legacy backend use, adding code to migration and reboots to
   transition into new backend use).

4. Subclass the new image backend for RBD support to allow it to be used with
   the new image backend.


Dependencies
============

No new libraries are required for this change.  However, the XML changes
discussed above require a libvirt version > 1.0.5 (the actual storage pools do
not, however).  While this is not strictly needed (as we can simply use the
existing code for determining the correct XML for a given image), it does
simplify the section of the code responsible for XML generation.  Since we
will most likely be increasing the minimum libvirt version for Mikata, however,
this should not be problematic.

Testing
=======

We will want to duplicate the existing tests for the various image backends to
ensure that the new backend covers all of the existing functionality.
Additionally, new tests should be introduced for:

* the XML changes

* storage pool management

* migrating existing instances to the new backend and the supporting
  transitional functionality

Documentation Impact
====================

We should warn about the deprecation of the legacy image backends,
and note the change to the new backend.  It should also be noted that
migrations and cold resizes are the preferred method to transition existing
instances to the new backend.


References
==========

* http://libvirt.org/formatdomain.html#elementsDisks

* http://libvirt.org/formatstorage.html

* http://libvirt.org/storage.html

* http://libvirt.org/html/libvirt-libvirt.html#virStorageVolCreateXMLFrom
