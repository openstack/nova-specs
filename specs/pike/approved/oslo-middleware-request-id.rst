..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Use oslo.middleware request_id
==============================

https://blueprints.launchpad.net/nova/+spec/oslo-middleware-request-id

Make Nova be in line with the rest of OpenStack on request_id
processing which means that global_request_id also works with Nova.

Problem description
===================

Nova has a copy/pasted version of oslo.middleware RequestId
middleware, because this is code that grew up in Nova using the return
header ``X-Compute-Request-ID``, then moved to oslo with
``X-OpenStack-Request-ID``. Nova never migrated to that middleware.

That middleware now has the logic to accept and validate inbound
request_ids. We want this to be consistent through all of OpenStack,
so for Nova to participate in global_request_id support as a callee,
it needs to be on this middleware.

Adding this middleware will mean that Nova now returns the additional
``X-OpenStack-Request-ID`` header. This requires a microversion per
our rules.

Use Cases
---------

As an application calling Nova I would like to be able to trace my
requests with an application provided global_request_id, which is easy
to search for in all service logs.

Proposed change
===============

Change ``ComputeReqIdMiddleware`` to inherent from
``oslo_middleware.request_id.RequestId``.

Bump requirements to require oslo.middleware >= 3.27.0.

Bump microversion. This is a signaling microversion only, request_id
generation and processing happens **well before** we have anything
approaching microversion handling in the paste pipeline. It's not
feasible to make the header a microversion conditional as it would
require complete rearchitecting of the request processing flow.

Alternatives
------------

Don't support global_request_id.

Data model impact
-----------------

None.

REST API impact
---------------

An additional HTTP Header ``X-OpenStack-Request-ID`` will be returned
after this change. The value will be identical to the existing
``X-Compute-Request-ID``.

There are no plans to ever remove the ``X-Compute-Request-ID``.

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

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------
Primary assignee: sdague

Work Items
----------

* Change Nova's ComputeRequestIdMiddleware

Dependencies
============

* Changes in oslo.middleware for compat headers which were landed in 3.27.0.

Testing
=======

* oslo.middleware tests that the value of any compat headers is
  identical to the ``X-OpenStack-Request-ID`` header.
* Tempest already tests for ``X-Compute-Request-ID`` from Nova
  commands. We are thus transitively tested.
* If folks insist a Tempest test for the new header could be added
  based on microversion, but it's probably overkill.

Documentation Impact
====================

api-ref doesn't yet talk about any of these headers. That should be
changed in the future, however given that it's not currently
documented (and will require some os-api-ref changes to be efficient
to document that) this work should not be held up for it.

References
==========

* oslo request_id spec -
  https://specs.openstack.org/openstack/oslo-specs/specs/pike/global-req-id.html

* Previous implementation for v3 - which seems to have been accidentally
  reverted in the v2.1 tear down -
  https://specs.openstack.org/openstack/nova-specs/specs/juno/implemented/cross-service-request-id.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
