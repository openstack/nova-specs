..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
API v3: Add x-openstack-request-id header
==========================================

https://blueprints.launchpad.net/nova/+spec/cross-service-request-id

The various OpenStack services are standardizing on a common header name to
use for the request ID: x-openstack-request-id. Nova currently uses the header
x-compute-request-id.

Problem description
===================

nova sends the request ID as x-compute-request-id. Other services (cinder,
glance, neutron) send x-openstack-request-id.


Proposed change
===============

Use x-openstack-request-id when handling v3 requests for nova. There is
existing middleware in oslo to generate the ID and attach the header to
the response.

Alternatives
------------

The current approach -- keeping the existing header name -- is the alternative.
This will perpetuate header name discontinuity among OpenStack services.

Another alternative is to include the new header name for both v2 and v3. But
the benefits of doing so is not great enough to justify altering the behavior
of the existing API.

Data model impact
-----------------

None.

REST API impact
---------------

This change will add a new header to HTTP responses. The new header,
x-openstack-request-id, will have the same value as x-compute-request-id.
After this blueprint is implemented, v2 will continue to return
x-compute-request-id. For v3, only x-openstack-request-id will be returned.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users making requests using the v3 API will only receive the new header,
x-openstack-request-id. python-novaclient uses x-compute-request-id (if
present) when reporting an HTTPError; this will need to be updated to use the
new header name when novaclient is using v3. Other clients moving from v2 to v3
will need to consider the header name change.

Performance Impact
------------------

None.

Other deployer impact
---------------------

This change has an UpgradeImpact, since it relies on adding middleware to the
pipeline in api-paste.ini. Since the middleware is taking over the task of
attaching the header to the response, not updating api-paste.ini will cause
responses to be returned without the x-openstack-request-id header.
Additionally, when using the v2 API, the x-compute-request-id header will also
be missing. The impact of this will be missing request ID information in
error output by novaclient, as alluded to in a previous section.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

chris-buccella

Work Items
----------

1) Sync request_id middleware from oslo (complete)
2) Use request_id middleware to add x-openstack-request-id to both the v3
   pipeline in api-paste.ini
3) Write middleware to attach x-compute-request-id. Add this to the v2 pipeline
   only.
4) Remove existing x-compute-request-id header manipulation code from
   api/openstack/wsgi.py


Dependencies
============

None.


Testing
=======

Due to the header name change, api/compute/v3/servers/test_instance_actions
will be affected, as it references the current header name. We already have
a skip in place for this, and will update the test to use the new name after
this blueprint is completed.


Documentation Impact
====================

v3 responses of the API will only include x-openstack-request-id, not
x-compute-request-id.


References
==========

Discussion from the HK Summit:
https://etherpad.openstack.org/p/icehouse-summit-nova-cross-project-request-ids

Refinements from the ML:
http://lists.openstack.org/pipermail/openstack-dev/2013-December/020774.html

Existing change:
https://review.openstack.org/#/c/66903/
