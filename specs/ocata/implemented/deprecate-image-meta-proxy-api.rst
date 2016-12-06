..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Deprecated image-metadata proxy API
===================================

https://blueprints.launchpad.net/nova/+spec/deprecate-image-meta-proxy-api

The proxies APIs were deprecated in the propose of `Deprecated API Proxies`_.
But the `image-metadata` API missed in that propose. This spec aims to describe
the deprecation of `image-metadata` API.

Problem description
===================

The proxies API should be removed from the Nova API. The `image-metadata` API
is one of them. It is just a proxy API for Glance API to operate the image
metadata.

There is quota check in `create_image/backup` APIs for extra metadatas, it
enforces with Nova `metadata` quota. In the glance, there is configure option
`image_property_quota` used to control the quota of image metadatas. So this
quota check should be enforced by the Glance API directly. Nova shouldn't
enforce quota for the resource which isn't managed by itself.

Use Cases
---------

* User should update the image metadata from the glance API directly, not the
  proxy API in Nova.
* Admin only needs to control the quota of image metadata in one single point,
  and that point is Glance.

Proposed change
===============

Propose to deprecated `image-metadata` API and remove the extra quota
enforcement with Nova `metadata` quota in the new Microversion.

Alternatives
------------

Keep these proxies forever. This will increase the cost of the maintenance of
Nova and slow down our ability to adapt to new features and requirements.

Data model impact
-----------------

None

REST API impact
---------------

With new microversion, the request to the `image-metadata` API will get
response `HTTPNotFound 404`. The image quota enforcement with Nova
`metadata` will be removed, and the `maxImageMeta` field will be removed from
`os-limits` API.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The ``nova image-meta`` CLI is already deprecated. The python API binding in
python-novaclient will be cap to the new microversion also. User only can use
this command in the old Microversion and we'll plan to remove that in the
first major python-novaclient release after Nova 15.0.0 is released.

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployer should update the image metadata quota in the glance side to match
the limit in nova create image/backup API.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Alex Xu <hejie.xu@intel.com>

Work Items
----------

The following are all done under a single new microversion:

* Deprecate the `image-metadata` API.
* Remove the quota check for create image/backup actions.
* Remove `maxImageMeta` field from `os-limits` API.
* Cap the image metadata python API binding in python-novaclient.

Dependencies
============

None

Testing
=======

There will be in tree functional testing that these APIs do the right thing
after this microversion and return 404s.

For Tempest, the ImagesMetadataTestJSON will need to be capped at the
microversion. There are `ongoing discussions`_ on how to handle this
in the openstack-dev mailing list.

Documentation Impact
====================

Update the `api-ref`_ about the image-metadata is deprecated in the new
Microversion. Also need upgrade note for the deployer the quota check of
image metadata doesn't enforce at Nova side anymore.

References
==========

.. _deprecated api proxies: ../../newton/approved/deprecate-api-proxies.html
.. _ongoing discussions: http://lists.openstack.org/pipermail/openstack-dev/2016-July/100085.html
.. _api-ref: http://developer.openstack.org/api-ref/compute/#create-image-metadata

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
