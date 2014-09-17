..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Tags support in EC2 API for volumes and volume snapshots
========================================================

https://blueprints.launchpad.net/nova/+spec/ec2-volume-and-snapshot-tags

Expose volume and volume snapshot metadata as EC2 tags in the EC2 API.

Problem description
===================

OpenStack's EC2 API has little support for 'tags' (resource metadata).
Only instance metadata are exposed in the EC2 API, so a user
can create, delete and list only instance metadata. OpenStack Cinder API
has support for metadata as well, for both volumes and volume snapshots,
and we just need to expose it into the EC2 API. This blueprint aims to
do just that.


Proposed change
===============

* EC2 API's 'CreateTags' method only used to work when one is creating
  tags for an instance resource. After this patch, one will be also
  able to create tags for volume and volume snapshot resources.

* A user will be able to call the 'DeleteTags' API to delete any tag
  associated with a volume or a volume snapshot.

* While calling the 'DescribeTags' API, tags of volumes and volume
  snapshots will be listed along with instance tags (provided tags
  for these resources are present, obviously).

* Support for specifying volume and volume snapshot IDs, and 'volume'
  and 'snapshot' as resources as parameters while calling 'DescribeTags'
  is added.

* As this is the first time the supported resources for tags are becoming
  plural in number, the code is made more generic so as to allow addition
  of further resources easier.

* Implementation detail: In the DescribeInstances API, user can specify
  both resource ID and resource type as filters. If the query says filter
  by resource IDs (vol-00000001 and ami-00000001) and also filter by
  resource type (instances and volumes), the current implementation takes
  the intersection of the resources (volumes in this case) and then checks
  if those resources are implemented.

Alternatives
------------

Alternative is: EC2 tags be different from volume tags by using scoped keys.
So a user creating a tag stack=beta in EC2 API will, in the Cinder API, see
it as EC2:stack=beta. This way, a user using the Cinder APIs will be able
to clearly see which metadata entries are created using EC2 API and which
are created by the OpenStack API.

I think it makes sense to keep the EC2 API layer as transparent as possible.
This means not going with the alternative proposed above. This also falls in
line with what we have presently for instance metadata.

Regarding the implementation detail specified above, an alternative is:
Do not allow resource IDs and resource type to be specified in the same
query.

There is no doc of AWS which says such an API call is not allowed (atleast I
can't find it). This implementation is easier, but IMO the way in which
it is implemented right now gives a better user experience. Probably logging
would help if we are dropping out a resource ID or resource type from the
query.


Data model impact
-----------------

None

REST API impact
---------------

Only EC2 API will be affected. Affected API calls are: CreateTags, DeleteTags
DescribeTags.

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

Insignificant. Note that in the case of DescribeTags, as we keep on adding
resources, an API call will be made to all of them (e.g. Glance, Cinder, etc)
when a DescribeTags call is made without specifying a resource type.

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
  rushiagr (Rushi Agrawal)

Work Items
----------

* Implement support for volume and snapshot tags.


Dependencies
============

None


Testing
=======

Comprehensive unit tests to test the functionality will be written.

Documentation Impact
====================

EC2 API document should be updated to reflect the changes done to the EC2 API
under this blueprint.


References
==========

EC2 API reference:
* CreateTags http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-CreateTags.html
* DeleteTags http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DeleteTags.html
* DescribeTags http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DescribeTags.html
