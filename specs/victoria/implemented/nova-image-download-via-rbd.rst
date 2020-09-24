..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Allow Nova to download Glance images directly via RBD
=====================================================

https://blueprints.launchpad.net/nova/+spec/nova-image-download-via-rbd


Problem description
===================

When using compute-local storage with qcow2 based VM root disks, Glance images
are downloaded into the libvirt image store by way of the Glance HTTP API.
For images in the 10s-100s of GB, this download can be _very_ slow.
If the compute node has access to Ceph, it can instead perform an 'rbd export'
on the Glance image, bypassing the Glance API entirely and directly download
the image from Ceph. This direct download can result in a drastic reduction
in download time, from tens of minutes to tens of seconds.

Use Cases
---------

As a user with a Ceph-backed image storage, I want to configure some compute
hosts for qcow2 images local to the compute host but quickly get the images
from Ceph rather than slow downloads from the Glance API.

Proposed change
===============

A special download handler will be registered for Glance images when the 'rbd'
value is present in ``allowed_direct_url_schemes`` option.

This download handler will be called only when a VM is scheduled on a node and
the required Glance image is not already present in the local libvirt image
cache. It will execute the OS native 'rbd export' command, using ``privsep``,
in order to perform the download operation instead of using the Glance HTTP
API.

The mechanism for per-scheme download handlers was previously available
as a plugin point, which is now deprecated, along with the
allowed_direct_url_schemes config option. This effort will close out on that
deprecation by moving the per-scheme support into the nova.images.glance module
itself, undeprecating the allowed_direct_url_schemes config, and removing the
old nova.images.download plug point.

The glance module also never used to perform image signature verification when
the per-scheme module was used. Since we are moving this into core code,
we will also fix this so that per-scheme images are verified like all the rest.

Alternatives
------------

VM root disks can be run directly within Ceph as creation of these VM root
disks are fast as they are COW clones for the Glance image, also in Ceph.
However, running the VM root disks from Ceph introduces additional latency to
the running VM and needlessly wastes network bandwidth and Ceph IOPS. This
specific functionality was added in Mitaka but is aimed at a different use case
where the VM root disks remain in Ceph and are not run as qcow2 local disks.

https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/rbd-instance-snapshots.html

The other alternative is to continue with existing approach only.

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

As proposed, there are no new configuration items, simply configuration of
existing items.

The following configuration options are required to ensure qcow2 local images
are downloaded from Ceph and cached on the local compute host:

On the Glance API node in glance-api.conf:

``DEFAULT.show_image_direct_url=true``

On the Nova compute node in nova.conf:

``DEFAULT.force_raw_images=false``

``libvirt.images_type=qcow2``

``libvirt.images_rbd_ceph_conf=<ceph_config_file>``

``libvirt.rbd_user=<ceph_user_name>``

``glance.allowed_direct_url_schemes = rbd``

Looking ahead, it may be desired to create additional entries in the libvirt
section of ``nova.conf`` for this feature as the current implementation assumes
that the ``rbd_user`` will have access to the Glance images. This may not be
the case depending upon how the Ceph pool permissions are configured.

Developer impact
----------------

The ``allowed_direct_url_schemes`` option was deprecated in Queens. Proposed
implementation of this feature would halt the deprecation of this option and
we would need to "un-deprecate" it.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jiri Suchomel <jiri.suchomel@suse.com>

Feature Liaison
---------------

Feature liaison:
  Dan Smith (danms)

Work Items
----------

* Refactor existing in-house out-of-tree implementation and integrate it fully
  into current codebase
* Write tests for implementation
* Update the admin guide with the description of how to set up the config if
  the new feature is required.

Dependencies
============

None

Testing
=======

* Unit tests
* Add an experimental on-demand queue job which uses Ceph with local qcow2
  images and 'direct from rbd' feature enabled

Documentation Impact
====================

The admin guide should be updated to call out this use case and how it differs
from the Ceph-native snapshot feature.  A good place to document this may be:

https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-kvm.html#configure-compute-backing-storage

References
==========

http://lists.openstack.org/pipermail/openstack-dev/2018-May/131002.html

http://lists.openstack.org/pipermail/openstack-operators/2018-June/015384.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Victoria
     - Introduced
