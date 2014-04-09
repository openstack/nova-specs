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

Proposed change
===============

The cache of images downloaded from Glance would be placed into a volume pool
(:code:`nova-base-images-pool`).  This is done simply by instructing libvirt
that Nova's image cache directory (e.g. :code:`/var/lib/nova/_base`) is a
volume pool, and as such does not affect directory layout (and is thus
compatible with both the legacy image backends and the new image backend
proposed below).

A new image backend, :code:`LibvirtStorage`, would be introduced.  This would
support being used in place of all of the current types (with the exeception of
RBD support, which for the time being would need a subclass [1]_).

If we are not using COW, the libvirt :code:`pool.createXMLFrom` method
could be used to appropriately copy the template image from the source pool,
:code:`nova-base-images-pool`, into the target image in the target pool
`nova-disks-pool`.

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
in can handle compression, etc).

In order to associate images with instances, the volumes in `nova-disks-pool`
would have a name of the form `{instance-uuid}_{name}` (with :code:`name` being
"disk", "kernel", etc, depending on the name passed to the image creation
method).  This way, it still remains easy to find the disk image associated
with a particular instance.

The use of this new backend would become the default for new installations.
However, the legacy backends would be left in place to maintain the live
upgrade functionality (e.g. Icehouse->Juno). See the `Other deployer impact`_
section below for more information.

For the :code:`disk` XML element in the :code:`domain` element supplied to
libvirt on instance creation, a type of :code:`volume` can be supplied, with
the :code:`<source>` element specifying the pool name and volume name [3]_.

.. [1] Currently, libvirt does not have support for the createXMLFrom operation
   for RBD-backed pools, so for RDB support, we would have to subclass the new
   backend and add in code to manually upload the template image.  This
   functionality should be present in a future version of libvirt. See
   `Red Hat BZ 1089079 <https://bugzilla.redhat.com/show_bug.cgi?id=1089079>`_.

.. [2] Note that this functionality will most likely have to wait until the
   OpenStack K release to be enabled by default, since such functionality would
   be difficult to implement while supporting instances using both the legacy
   and new backend -- see the `Other deployer impact`_ section below.  It could
   be enabled in Juno by setting the :code:`images_type` configuration option
   to 'libvirt-storage', which would imply that the deployer didn't want the
   transitional functionality described in the aforementioned section.

.. [3] Note that this XML is only available in libvirt version 1.0.5 and up,
   so if we wish to support a version less than that for Juno, we
   would simply have to rely on the current code (with some slight tweaks -- we
   no longer have to try to detect the format, etc ourselves, as libvirt will
   give it to us via the libvirt volume XML specification).

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

For live migration/upgrade from OpenStack Icehouse to OpenStack Juno, the
legacy image backends (and support for them in Nova's image cache) will be left
in place for the next release (Juno), but will be marked as deprecated.  In
the K release, the legacy backends will be removed (as well as support for
them in the image cache manager).

To allow existing installations to easily transition to the new backend,
existing instances would be left on the legacy backend, while all new instances
would be created to use the new backend.  Whether or not an instance was using
a legacy backend could be determined by checking the instance directory for
images (if they are present, the instance is using a legacy backend, if not the
instance is using the new backend).

During operations which allow the changing of libvirt XML, such as cold
migrations, resizes, reboots, and live migrations, instances would be
automatically transitioned to using the new system [5]_.  This would allow
deployers to move to the new system at their leisure, since they could either
choose to bulk-restart the VMs themselves, or simply ask the VMs owners to do
so when convinient.  For instances still on the legacy system, a warning would
be issued on compute node startup.

.. [5] This would entail telling libvirt to use the volume as the disk source.
   In the case of live migrations with shared storage, resizes to the same
   host, and reboots, a couple extra steps would be taken for deployments using
   the local-file-based legacy backends.  For reboots and resizes, we can
   simply move the disk image file to the directory pool location while the VM
   is shut off.  In the case of shared storage which supports hard-linking, a
   hard link pointing to the disk image file would be placed into the storage
   pool directory.  Once the live migration finishes, the original location
   would be deleted, leaving the new hard link as the only remaining reference
   to the disk image file.  For filesystems where hard linking isn't supported,
   a block live migration would be necessary to migrate the VM to the new image
   backend.

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
stored differently [6]_, we could simply create a pool for each type, and place
the images into the appropriate pool based on their name.  An advantage to
using pools is that Nova doesn't actually need to know the underlying details
about the pool, only its name.  Thus, if a deployer wanted to move a particular
pool to a different location, device, etc, no XML changes would be needed,
assuming the same pool name was kept.

.. [6] As suggested in
   `this blueprint <https://review.openstack.org/#/c/83727>`_, for instance

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    sross-7

Other contributors:
    None

Work Items
----------

1. Modify the code which downloads images from Glance into a cache to
   create a storage pool in the cache directory and refresh the cache
   when a new image is downloaded.

2. Implement the new image backend (and subclass it for RBD as long as it's not
   supported natively as per [1]_) and sections in the XML config builder to
   accept the :code:`volume` type for disk elements.

3. Implement the functionality required to support transitional installations
   (detecting legacy backend use, adding code to migration and reboots to
   transition into new backend use).

4. Implement functionality in the image cache manager to take advantage of the
   new data about backing files stored in libvirt's volume information XML
   (this would be disabled in Juno unless :code:`images_type` was set to
   'libvirt-storage', implying the deployer didn't want the transitional
   functionality mentioned above).


Dependencies
============

No new libraries are required for this change.  However, the XML changes
discussed above require a libvirt version > 1.0.5 (the actual storage pools do
not, however).  While this is not strictly needed (as we can simply use the
existing code for determining the correct XML for a given image), it does
simplify the section of the code responsible for XML generation.  Since we
will most likely be increasing the minimum libvirt version for Juno, however,
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
