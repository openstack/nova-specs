..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Support multiple stores of Glance
=================================

https://blueprints.launchpad.net/nova/+spec/support-glance-multiple-backend

This blueprint proposed to support the multiple backend of glance.

Problem description
===================

In Train, Glance has added the ability to configure multiple stores
[1]_. This way an operator can configure more than one of similar or
different kind of stores and use one as a default store. If a store
is not specified at the time of uploading an image then the image
will be stored in default store.

In case of Nova snapshot or backup, if no changes are made to Nova, even if
multiple stores are configured then the snapshot or backup image will be
uploaded to default store. This will not cause any issue unless Nova is using
ceph as a backend and glance has configured ceph store as well and default
store in glance is not ceph. This will affect nova's ability to use ceph
backend for uploading snapshots or backup images in more efficient way.

Use Cases
---------
1. Operator wants to upload all the snapshots or backup images to one
   specific/dedicated store in Glance.
2. Fast snapshot using ceph even ceph is not a default store in glance.

Proposed change
===============
In case if instance is created using image then it stores the image uuid as
'image_ref'. When instance snapshot or backup is requested nova should
pass the 'image_ref' as a header 'X-OpenStack-Base-Image-Ref' to glance, so
that glance will identify in which store the base image is stored and use that
same store to upload the instance snapshot or instance backup.

In case if instance is created using volume then the snapshot or backup image
should be uploaded to default store configured in Glance.

Alternatives
------------
* Add a new microversion to snapshot and backup API to support configuring to
  upload the snapshot/backup image to specific store. I am proposing to add
  new ``--store`` option to snapshot and backup API where user can specify to
  which store snapshot/backend image will be uploaded. If ``--store`` option
  is not specified then the image will be uploaded to default store.

  If user chooses the 'store' which is not configured in
  glance then glance will return with 404 NotFound error and the image which
  is created in 'queued' state while 'snapshot' or 'backup' operation will
  be deleted during the cleanup operation. The alternate way is, In the
  beginning before creating queued image, validate the 'store' specified by
  end user using '/v2/info/stores' discovery call of glance. If specified
  'store' is not present in the discovery response then whole operation will
  be skipped with 404 response to end user.

  End user can identify available 'stores' in glance using
  'GET $IMAGE_API_URL/v2/info/stores' discovery call. It will return the
  list of stores configured at glance side. The "id" field from the
  discovery response represents the configured store. Following is the
  example of discover '/v2/stores/info' response call::

    GET $IMAGE_API_URL/v2/info/stores

    {
        "stores": [
            {
                "id":"reliable",
                "description": "Reliable filesystem store"
            },
            {
                "id":"fast",
                "description": "Fast access to rbd store",
                "default": true
            },
            {
                "id":"cheap",
                "description": "Less expensive rbd store"
            }
        ]
    }

  For example glance has two file stores configured as 'file_1', 'file_2' and
  'file_1' is set as default store then at present scenario all images of
  'snapshot'or 'backup' operation will always be uploaded to 'file_1' store of
  glance.

* Add a new configuration option 'store' under 'glance' section to
  upload all the snapshot/backup images to specified/dedicated store. If this
  option is not defined then all the snapshot/backup images will be uploaded to
  the default store. This solution will be efficient if operator doesn't want
  to expose the use of uploading snapshot image to specific store to end user.

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

Upgrade impact
--------------
None

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  abhishek-kekane

Feature Liaison
---------------
Feature liaison:
  Balazs Gibizer

Work Items
----------
* Change glanceclient in nova to pass 'X-OpenStack-Base-Image-Ref' header
  to upload call.
* Add related tests

Dependencies
============
None

Testing
=======
* Add related unittest
* Add related functional test
* Add tempest tests

Documentation Impact
====================
None

References
==========
.. [1] https://docs.openstack.org/glance/train/admin/multistores.html

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced

