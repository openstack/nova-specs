..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
volume-backed server rebuild
==========================================
https://blueprints.launchpad.net/nova/+spec/volume-backed-server-rebuild

Currently, the compute API will `fail`_ if a user tries to rebuild
a volume-backed server with a new image. This spec proposes to add
support for rebuilding a volume-backed server with a new image.

.. _fail: https://github.com/openstack/nova/blob/62245235b/nova/compute/api.py#L3318

Problem description
===================

Currently Nova rebuild (with a new image) only supports instances which are
booted from images. The volume-backed instance cannot be rebuilt when a new
image is supplied. Trying to rebuild a volume-backed instance will raise a
HTTPBadRequest exception.

Use Cases
---------

* As a user, I would like to rebuild my volume-backed server with a new image.

* As a nova developer, I would like to have feature parity in the compute API
  for volume-backed and image-backed servers.

Proposed change
===============

First, change the existing API for rebuilding a volume-backed server.
Then the API flow would be:

#. Has the new API microversion been requested?
#. Is the instance.host service version new enough to support
   volume-backed rebuild with a new image?

If these are true, proceed. If not, fail in the API with a 409 error.

Note that when rebuilding with a new image, the request will be run through
the scheduler against the current host to be consistent with image-backed
rebuild with a new image. See `bug 1664931`_ for details.

.. _bug 1664931: https://bugs.launchpad.net/nova/+bug/1664931

Then the nova-compute will perform the following steps:

#. Create an empty (no connector) volume attachment for the volume and
   server. This ensures the volume remains ``reserved`` through the next
   step.
#. Delete the existing volume attachment (the old one).
#. Call the new ``os-reimage`` cinder API.
#. Poll the volume status for completion (either success or failure).
#. Upon successful completion of the re-image operation, update the empty
   volume attchment in Cinder, and then do the attachment on the Nova host
   when spawning the (rebuilt) guest VM and "complete" the attachment
   which will make the volume ``in-use`` again.

In this process, there are some conditions that we could hit:

* If we failed to re-image the volume and the volume is in 'error' status
  then we should set the instance status as "error". Since users can rebuild
  instances in error status, the user has a way to retry the rebuild once
  the cause of the cinder side failure is resolved. Note that nova-compute
  will *not* attempt to update the volume attachment records with the host
  connector again on the volume in error status.
* If the cinder API itself returns a >=400 error, nothing changed about the
  root volume and in that case the migration status can be 'failed' but the
  instance status should go back to what it was (we can see how
  _error_out_instance_on_exception is used).


Alternatives
------------

The main alternative is that nova would perform the rebuild like an initial
boot from volume where nova-compute would create a new volume from the new
image and then "swap" the root volume on the instance during rebuild.

There are issues with this, however, like what to do about the old volume:

* Regarding 'delete_on_termination' flag in the BDM,
  delete_on_termination=True means: don't delete the volume when we kill
  the instance. Rebuild means: re-initialize this instance in place. The
  rebuild flow would have to determine what to do if the old root volume
  BDM was marked with delete_on_termination=True - ignore that and preserve
  the old root volume or delete it.

* We could pass a new flag to the rebuild API telling nova what to do about the
  old volume (delete it or not).
  If the flag is true to delete the old volume but the old volume has
  snapshots, Nova won't be deleting the volume snapshots just to delete
  the volume during a rebuild.

But there are several issues with that as mentioned above like quota and
the questions about what nova should do about the old volume, you can
see more detailed information in `References`_.

Data model impact
-----------------

None

REST API impact
---------------

Change the rebuild request response code from 400 to 202 if the conditions
described in the `Proposed change`_ section are met.
The API microversion and compute RPC version will also be incremented to
indicate the new support.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The python-novaclient and python-openstackclient will be updated
to support the new microversion.

Performance Impact
------------------

The operation will take longer because of the orchestration
involved and the work that needs to happen in Cinder.

Other deployer impact
---------------------

If the cinder volume ``reimage`` API operation fails and the volume goes to
``error`` status, an admin will likely need to investigate and resolve the
issue in cinder and then reset the volume status to ``reserved``.

Developer impact
----------------

None

Upgrade impact
--------------

The API microversion and compute RPC version will also be incremented
to indicate the new support, therefore users will not be able to leverage
the feature until the nova-compute service hosting a volume-backed instance
is upgraded.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jie Li <lijie@unitedstack.com> (ramboman)

Other contributors:
  Kevin Zheng <zhengzhenyu@huawei.com>

Work Items
----------

* Change the existing rebuild API.
* Create an empty attachment for the root volume so the volume
  remains in-use during rebuild (we do this today already).
* Delete the old volume attachment.
* Call the cinder API to re-image the volume.
* Update and complete the volume attachment once re-imaged.
* Adopt the new compute version.
* Adopt the new microversion in python-novaclient.
* Adopt the new microversion in python-openstackclient.
* Change the nova API documents.

Dependencies
============

Depends on the cinder blueprint for re-imaging a volume, see
more detail information in References.


Testing
=======

The following tests are added.

* Nova unit tests for negative scenarios
* Nova functional tests for "happy path" testing
* Tempest integration tests to make sure the nova/cinder integration
  works properly

Documentation Impact
====================

We will replace the `note in the API reference`_ with
a note about the required minimum microversion for rebuilding a
volume-backed server with a new image.

The following document will be updated:

* API Reference

.. _note in the API reference: https://developer.openstack.org/api-ref/compute/?expanded=#rebuild-server-rebuild-action

References
==========

* Stein PTG etherpad: https://etherpad.openstack.org/p/nova-ptg-stein

* This is the discussion about rebuild the volume-backed server:

  http://lists.openstack.org/pipermail/openstack-dev/2017-October/123255.html

* This is the discussion about what we should do about the root volume
  during a rebuild:

  http://lists.openstack.org/pipermail/openstack-operators/2018-March/014952.html

* The cinder blueprint for re-imaging a volume:

  https://blueprints.launchpad.net/cinder/+spec/add-volume-re-image-api

History
=======

.. list-table:: Revisions
      :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Proposed.
   * - Train
     - Re-proposed.