..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Relax API validation for v2.0 on v2.1
==========================================

https://blueprints.launchpad.net/nova/+spec/api-relax-validation

Currently v2.1 strongly validates all API requests.

This spec details how we will relax some validation for v2.0 API requests
served by the v2.1 code base.
Note requests being sent to /v2.1 will keep their full strong validation.

Problem description
===================

We hope that in the near future, all request to nova API can be processed by
the new API v2.1 code base.
At that point, we will be able to deprecate, then delete, the current v2.0
API implementation, and return to a single API implementation.

While all clients making valid requests to the v2.0 API will get the same
results talking to the v2.1 API, there are issues.
Various types of "invalid" requests are currently accepted by v2.0, but would
be rejected by v2.1.
Even tempest was found to be making invalid requests:
https://review.openstack.org/#/c/138245

Use Cases
----------

We need it to be low risk for users to deploy v2.1 to deal with the current
requests for v2.0.

While initial tests of some major SDKs have shown they appear to be making
correct requests to our v2.0 API, not all users use an SDK.

Given the problems found in the tempest test suite, where invalid requests
were being made to the v2.0 API, it must be assumed that users who have
written their own code to access our API will have made similar mistakes.
Where possible, we want these users to be unaffected by the change from
v2.0 to v2.1.

It is expected that SDKs will be updated to start adding the version headers
for all their requests to the API. At this point, they will start to get the
full benefits of strong API validation. Only those users that are still not
specifying the version headers would be getting the weaker validation.

Project Priority
-----------------

Part of the API v2.1 effort.

Proposed change
===============

The API v2.1 validation logic will change such that:

* requests to /v2.1 work the same as today after this change

* requests to /v2 will have relaxed validation, and will ignore
  X-OpenStack-Nova-API-Version headers, and always return /v2 responses

* requests made to /v2 will never return X-OpenStack-Nova-API-Version headers,
  even when powered by the v2.1 codebase

* if we keep /v1.1 it will remain the same as /v2

The relaxed validation consists of:

* no longer error out requests due to additionalProperties, instead when
  the request if for the /v2 API we just ignore those additionalProperties.

In addition:

* any request to /v2 that includes headers for /v2.1 will be ignored when
  v2.1 codebase is used to deliver the /v2 requests, so it matches what
  the v2 codebase is doing today.

For more details see REST API impact.

Alternatives
------------

The main alternative is to not do this, which is likely to lead to slower
adoption of v2.1.

We could also allow /v2 requests to be sent to /v2.1, but that would
confuse matters, /v2 should just ignore the version headers.

We could ensure that any requests to /v2 error out if you sent the
X-OpenStack-Nova-API-Version header, but as python-novaclient already
sends that header for all /v2 requests, it would create another backwards
compatibility issue.

Instead of just ignoring parameters, it would be nice to also strip out
any invalid parameters before passing through the request to the v2.1 code.
It also feels slightly better from an input validation and security point
of view, but it does risk changing how the API behaves.
We could still look to add this at a later date, if it turns out to be a
good idea.

Data model impact
-----------------

None

REST API impact
---------------

This will have zero impact for the /v2.1 endpoint.

The /v2 endpoint powered by the v2.1 code gets the relaxed validation to
make it more compatible, as mentioned above.

In addition /v2 endpoint thats powered by the v2.1 code should never accept
any requests not accepted by /v2, and should only return /v2 like responses.
Basically, it should always ignore any X-OpenStack-Nova-API-Version
just like the v2 code base does today.

For consistency, /v1.1 will be the same as /v2

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

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johnthetubaguy and alex_xu

Work Items
----------

* relax validation for /v2 requests when using v2.1 codebase,
  instead just ignore bad properties

* requests made to /v2 will never return X-OpenStack-Nova-API-Version headers,
  even when powered by the v2.1 codebase

* ensure that /v2 served up by the v2.1 codebase ignores any
  of the X-OpenStack-Nova-API-Version headers,
  just like v2.0 code base does.

Dependencies
============

None

Testing
=======

Additional unit tests and integration tests should be enough to cover these
changes.

Documentation Impact
====================

None

References
==========

None
