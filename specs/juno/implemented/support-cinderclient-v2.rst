..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Cinder Client V2 Support
==========================================

https://blueprints.launchpad.net/nova/+spec/support-cinderclient-v2

Cinder has a new API version 2 [1]. This version has existed since Grizzly [2]
and has been available in devstack since Havana [3].

The API provides:

* More consistent responses like name, description instead of 'display_name',
  etc.

* Caching data between controllers instead of multiple database hits.

* Filtering when listing information on volumes, snapshots and backups. This
  would be great support to have in Nova so the full listing of resources
  doesn't have to be given over the network for Nova to sort through. [4]

Cinder is also deprecating version 1 in favor of 2, so it would be great to
give users a transition period in other projects.

Problem description
===================

Nova currently has a wrapper to the Cinder client in nova.volumes.cinder which
supports version 1 and expects a variety of response keys like 'display_name'
and 'display_description' which aren't available in version 2. These were
changed to be consistent with other projects that just use 'name' and
'description'.

Proposed change
===============

Nova should use Cinder v2 client [5] which understands how to talk to the
Cinder v2 API. Since v1 is deprecated, we can leave Cinder client v1 support
in.

`cinder_catalog_info` option in nova.conf should also be set to
`volumev2:cinder:publicURL` which would default new users the v2 API which is
on by default in Cinder since Grizzly.

Making these changes to the wrapper won't require any change to its interface
or changes to how it returns information. This is done by the wrapper doing the
translation and still giving back the expected data structure as it would with
v1.

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

Existing deployments will not need to make any changes to nova.conf in the Juno
release. Cinder will just be deprecating v1 support, so they'll receive
a warning on start up in the cinder-api service. If the deployer wants Nova to
use Cinder v2, they'll need to change `cinder_catalog_info` to use the
appropriate service_type they have Cinder v2 endpoint setup in the service
catalog. It is acceptable to have a mix of Nova hosts talking to different
versions of the Cinder API, assuming both v1 and v2 are enabled in Cinder.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  thingee

Other contributors:
  dzyu

Work Items
----------

* Write changes in nova.volumes.cinder to support Cinder client v2, while
  keeping support for v1. [6]
* Add Cinder filtering support in Nova.

Dependencies
============

None

Testing
=======

Tempest gate tests for compute will test against Cinder v2. Tempest has both
versions available, so Nova's config option of cinder_catalog_info will be
updated to the appropriate service_type of v2. If resources allow, we can also
test against v1.

Unit tests will test against Nova's wrapper which talks to Cinder client. This
will specifically verify usage between v1 and v2 is handled on this layer and
is transparent to the rest of Nova.

Documentation Impact
====================

None

References
==========

[1] - http://docs.openstack.org/api/openstack-block-storage/2.0/content/
[2] - https://review.openstack.org/#/q/status:merged+project:openstack/cinder+branch:master+topic:bp/bp,n,z
[3] - https://review.openstack.org/#/c/22489/
[4] - https://github.com/openstack/cinder/commit/88e688317dc4066f2f0b4dfc454a3f049da4d0e3
[5] - https://github.com/openstack/python-cinderclient/tree/master/cinderclient/v2
[6] - https://review.openstack.org/#/c/43986/
