..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Support filtering by aggregate membership to allocation candidates
==================================================================

https://blueprints.launchpad.net/nova/+spec/alloc-candidates-member-of

Provide support for filtering allocation candidates by the underlying resource
provider's membership in one or more aggregates.

Problem description
===================

The list of resource providers that the placement API's ``GET
/allocation_candidates`` returns can be very large, particularly when many
compute hosts are empty. Sometimes nova may have information that would allow
the number of compute hosts to be dramatically reduced. For instance, if nova
knows that a particular project is "pinned" to a host aggregate, currently nova
asks placement for all the resource providers that meet the resource
requirements of the flavor and then promptly discards any compute hosts that
are not in that particular host aggregate (in the aggregate multi-tenancy
isolation filter).

This process could be much more efficient if the nova scheduler were to simply
ask placement to only return compute hosts that are associated with a nova host
aggregate.

Use Cases
---------

Simple pre-processing scheduler filters like the aggregate multi-tenancy
isolation filter can be replaced with more efficient placement-side filtering.
This requires only the ability to provide a list of aggregates, one of which
the candidates must belong to.

More complex cases arise when multiple aggregate-based requirements
need to be expressed. For example, imagine the above case of a tenant
confined to a set of aggregates, combined with a user's request to
boot into a specific AZ (aggregate). In order to express this, we need
to be able to provide multiple OR'd sets of aggregates, each of which
are AND'd together. This would allow us to express a logical query like::

  Give me all allocation candidates that are allowed to house tenant
  "foo" (either "tenant_foo_old_computes" or
  "tenant_foo_new_computes") and are also in AZ "US Chicago".

The desired nodes are the resource providers that are in the union
of all the aggregates that define suitable computes assigned to the
tenant by the operator, which intersect with the aggregate that
defines the AZ requested by the user.

Proposed change
===============

The existing ``GET /resource_providers`` placement REST API call supports a
``member_of`` query `parameter_`. This parameter is "a string representing an
aggregate uuid; or the prefix in: followed by a comma-separated list of strings
representing aggregate uuids. The returned resource providers must be
associated with at least one of the aggregates identified by uuid."

This provides sufficient expressivity to query for the set of
providers desired in the first use case above. For the second, we must
be able to provide multiple such sets, and take the resulting
intersection.

We propose to support this exact same parameter for the ``GET
/allocation_candidates`` placement REST API call.

.. _parameter: https://developer.openstack.org/api-ref/placement/#list-resource-providers

If multiple `member_of` parameters are provided, the corresponding values will
be considered by the underlying implementation to be ANDed together. In other
words, the following query string::

  &member_of=in:agg1,agg2&member_of=agg3

would translate logically to:

  Candidate resource providers should be in either agg1 or agg2, but definitely
  in agg3.

For consistency, the ``GET /resource_providers`` REST API call should also be
augmented to handle multiple ``member_of`` query sets in the same way as above.

Alternatives
------------

We can continue to do post-processing of compute hosts by looking at host
aggregate relationships in the scheduler filters. As noted, however, this is
inefficient.

Data model impact
-----------------

None.

REST API impact
---------------

Add the ``member_of`` parameter to the ``GET /allocation_candidates`` REST API
call. Make the behavior and specification identical to the same-named parameter
for the ``GET /resource_providers`` REST API call. A new microversion will be
used to indicate to clients that the new parameter is available.

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

Expected increase in overall scheduler performance for use cases where the
scheduler can limit the number of compute hosts it operates on.

Other deployer impact
---------------------

We should be able to deprecate the aggregate multi-tenancy isolation
and availability zone scheduler filters after the "S" release.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jaypipes

Other contributors:
  cdent

Work Items
----------

* Add support to the ``nova.objects.AllocationCandidates.get_by_requests()``
  method for the ``member_of`` filter. This will require changes to the
  ``RequestGroup`` object as well

* Add new microversion to the placement REST API to support the ``member_of``
  query parameter

* Add support to the ``nova.objects.AllocationCandidates.get_by_requests()``
  method for multiple ``member_of`` query sets.

* Add new microversion to the placement REST API to support multiple sets.

Dependencies
============

In order for this functionality to be useful, nova host aggregates should be
"mirrored" into the placement service. Currently, nova host aggregates are not
yet showing up automatically in the placement service. A separate `blueprint_`
for this will be a soft dependency for this work.

.. blueprint_: https://blueprints.launchpad.net/nova/+spec/placement-mirror-host-aggregates

Testing
=======

Normal functional and unit testing.

Documentation Impact
====================

Document the REST API microversion in the appropriate reference docs.

References
==========

placement-req-filter blueprint (use case): https://review.openstack.org/544585
