..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Limiting Allocation Candidates
==============================

https://blueprints.launchpad.net/nova/+spec/allocation-candidates-limit

This specification provides a model for limiting the number of allocation
candidates that are returned when making a request to ``GET
/allocation_candidates`` while maintaining reasonable performance and not
impacting pack versus spread behavior.

Problem description
===================

In a large and sparse cloud (e.g. 10,000 empty compute nodes), a request of
``GET /allocation_candidates?resource=VCPU:1`` can return information for
10,000 resource providers. This has implications for memory and performance on
both the placement service and in the client (in the present day, the
nova-scheduler).

There are many potential solutions to this problem, many of which introduce
other problems, such as impacting pack versus spread handling in scheduling
decisions, disrupting use of indexes in the database, or increased complexity
in the server process.

Use Cases
---------

As a client of the placement service I would like to optionally be able to
request a limited number of allocation candidates.

Proposed change
===============

The proposed solution is the result of discussing many different options and
eventually resolving to doing a simple thing to address the problems present in
clients of the placement service while leaving open options to future
adjustments as required.

* In a new microversion accept an optional ``limit`` query parameter on the
  ``GET /allocation_candidates`` whose value expresses the maximum number of
  allocation candidates that will be returned in the response. At this time no
  support for expressing pagination or ordering is being considered. The value
  means the first N candidates. If unset, there is no limit.

* Modify `AllocationCandidates.get_by_filters` to take a slice of the
  `allocation_requests` of the size defined by the ``limit`` and provide
  `provider_summaries` of only those providers mentioned in the requests.

* That slice is either the first `N` items or a random sampling depending on
  the value of a boolean configuration setting
  (``randomize_allocation_candidates``). This allows a deployment to choose
  pack or spread behavior in the results. The default, ``False``, maintains
  existing behavior.

This solution will mean a smaller dataset being transformed into JSON and
transmitted over the wire to the candidate, and a smaller number of objects
being created server-side, but still a large number of rows being returned from
database queries.

Alternatives
------------

There are many alternatives, most of which involve invasive changes in the
database and establishing periodic jobs in the placement service.

For a first pass, the relatively simple model proposed above will work and can
be incrementally improved or adjusted if there are issues.

Data model impact
-----------------

None.

REST API impact
---------------

Extend the query parameter schema for the ``GET /allocation_candidates``
request to, in a new microversion, accept a ``limit`` parameter that takes an
integer value representing the maximum number of candidates that will be
returned.

Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

N/A

Performance Impact
------------------

The purpose of this change is to protect global performance by limiting the
size of result sets sent over the wire. However in an environment where there
are a very large number of resource providers the database query will still
have a large result set. Depending on how we handle that result set in Python,
there is potential for it to have an impact on server resource use. If that
proves to be the case, we have additional techniques to address that beyond
those already proposed here.

Other deployer impact
---------------------

N/A

Developer impact
----------------

The new configuration item will need to be changed for those deployments that
do not want the default.

Implementation
==============

The main guts of this change happen in a loop within `get_by_filters`_,
wherein a list of resource providers is traversed.

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  rgerganov

.. _get_by_filters: https://github.com/openstack/nova/blob/8ca24bf1ff80f39b14726aca22b5cf52603ea5a0/nova/objects/resource_provider.py#L2510

Work Items
----------

* Add a configuration setting as described above that controls how the result
  set is to be sliced.
* Add ``limit`` to the ``GET /allocation_candidates`` query parameter JSON
  schema
* Adjust `AllocationCandidates.get_by_filters` to accept an optional ``limit``
  parameter, to be used in processing the results.
* Update functional tests to confirm the limit and randomization functionality
  of ``get_by_filters``.
* Update gabbi tests for ``GET /allocation_candidates`` to exercise the
  ``limit`` functionality.

Dependencies
============

N/A

Testing
=======

We may wish to provide some facilities for examining performance before and
after this change, and after this change and before any further adjustments.

Documentation Impact
====================

The new configuration setting will be documented.

References
==========

N/A

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
