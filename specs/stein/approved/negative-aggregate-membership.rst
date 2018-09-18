..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Support filtering by forbidden aggregate membership
===================================================

https://blueprints.launchpad.net/nova/+spec/negative-aggregate-membership

This blueprint proposes to support for negative filtering by the underlying
resource provider's aggregate membership.

Problem description
===================

Placement currently supports ``member_of`` query parameters for the
``GET /resource_providers`` and ``GET /allocation_candidates`` endpoints.
This parameter is either "a string representing an aggregate uuid" or "the
prefix ``in:`` followed by a comma-separated list of strings representing
aggregate uuids".

For example,

  ``&member_of=in:<agg1>,<agg2>&member_of=<agg3>``

would translate logically to:

  Candidate resource providers should be in either agg1 or agg2, but definitely
  in agg3. (See `alloc-candidates-member-of`_ spec for details)

However, there is no expression for forbidden aggregates in the API. In other
words, we have no way to say "don't use resource providers in this special
aggregate for non-special workloads".

Use Cases
---------

This feature is useful to save special resources for specific users.

Use Case 1
~~~~~~~~~~

Some of the compute host are `Licensed Windows Compute Host`, meaning any VMs
booted on this compute host will be considered as licensed Windows image and
depending on the usage of VM, operator will charge it to the end-users.
As an operator, I want to avoid booting images/volumes other than Windows OS
on `Licensed Windows Compute Host`.

Use Case 2
~~~~~~~~~~

Reservation projects like blazar would like to have its own aggregate for
host reservation in order to have consumers without any reservations to be
scheduled outside of that aggregate in order to save the reserved resources.

Proposed change
===============

Adjust the handling of the ``member_of`` parameter so that aggregates can be
expressed as forbidden. Forbidden aggregates are prefixed with a ``!``.

In the following example,

  ``&member_of=!<agg1>``

would translate logically to:

  Candidate resource providers should *not* be in agg1.

This negative expression can also be used in multiple ``member_of`` parameters:

  ``&member_of=in:<agg1>,<agg2>&member_of=<agg3>&member_of=!<agg4>``

would translate logically to:

  Candidate resource providers must be at least one of agg1 or agg2,
  definitely in agg3 and definitely *not* in agg4.

Note that we don't support ``!`` in the ``in:`` prefix:

  ``&member_of=in:<agg1>,<agg2>,!<agg3>``

would result in HTTP 400 Bad Request error.

Instead, we support ``!in:`` prefix:

  ``&member_of=!in:<agg1>,<agg2>,<agg3>``

which is equivalent to

  ``member_of=!<agg1>&member_of=!<agg2>&member_of=!<agg3>``

Nested resource providers
-------------------------

For nested resource providers, an aggregate on a root provider automatically
spans the whole tree. When a root provider is in forbidden aggregates, the
child providers can't be a candidate even if the child provider belongs to no
(or another different) aggregate.

In the following environments, for example,

.. code::

                                           +-----------------------+
                                           | sharing storage (ss1) |
                                           |   agg: [aggB]         |
                                           +-----------+-----------+
                                                       | aggB
      +------------------------------+  +--------------|--------------+
      | +--------------------------+ |  | +------------+------------+ |
      | | compute node (cn1)       | |  | |compute node (cn2)       | |
      | |   agg: [aggA]            | |  | |  agg: [aggB]            | |
      | +-----+-------------+------+ |  | +----+-------------+------+ |
      |       | parent      | parent |  |      | parent      | parent |
      | +-----+------+ +----+------+ |  | +----+------+ +----+------+ |
      | | numa1_1    | | numa1_2   | |  | | numa2_1   | | numa2_2   | |
      | |  agg:[aggC]| |   agg:[]  | |  | |   agg:[]  | |   agg:[]  | |
      | +-----+------+ +-----------+ |  | +-----------+ +-----------+ |
      +-------|----------------------+  +-----------------------------+
              | aggC
        +-----+-----------------+
        | sharing storage (ss2) |
        |   agg: [aggC]         |
        +-----------------------+

the exclusion constraint is as follows:

* ``member_of=!<aggA>`` excludes "cn1", "numa1_1" and "numa1_2".
* ``member_of=!<aggB>`` excludes "cn2", "numa2_1", "numa2_2", and "ss1".
* ``member_of=!<aggC>`` excludes "numa1_1" and "ss2".

Note that this spanning doesn't happen on numbered ``member_of`` parameters,
which is used for the granular request:

* ``member_of<N>=!<aggA>`` excludes "cn1"
* ``member_of<N>=!<aggB>`` excludes "cn2" and "ss1"
* ``member_of<N>=!<aggC>`` excludes "numa1_1" and "ss2".

See `granular-resource-request`_ spec for details.

Alternatives
------------

We can use forbidden traits to exclude specific resource providers, but if we
use traits, then we should put Blazar or windows license trait not only on
root providers but also on every resource providers in the tree, so we don't
take this way.

We can also create nova scheduler filters to do post-processing of compute
hosts by looking at host aggregate relationships just as `BlazarFilter`_
does today. However, this is inefficient and we don't want to develop/use
another filter for the windows license use case.

Data model impact
-----------------

None.

REST API impact
---------------

A new microversion will be created which will update the validation for the
``member_of`` parameter on ``GET /allocation_candidates`` and ``GET
/resource_providers`` to accept ``!`` both as a prefix on aggregate uuid and
as a prefix on ``in:`` prefix to express that the prefixed aggregate (or
the aggregates) is required to be excluded in the results.

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

Queries to the database will see a moderate increase in complexity but existing
table indexes should handle this with aplomb.

Other deployer impact
---------------------

None.

Developer impact
----------------

This helps us to develop a simple reservation mechanism without having a
specific nova filter, for example, via the following flow:

0. Operator who wants to enable blazar sets default forbidden and required
   membership key in the ``nova.conf``.

   * The parameter key in the configuration file is something like
     ``[scheduler]/placement_req_default_forbidden_member_prefix`` and the
     value is set by the operator to ``reservation:``.

   * The parameter key in the configuration file is something like
     ``[scheduler]/placement_req_required_member_prefix`` and the value
     would is set by the operator to ``reservation:``.

1. Operator starts up the service and makes a host-pool for reservation via
   blazar API

   * Blazar makes an nova aggregate with ``reservation:<random_id>`` metadata
     on initialization as a blazar's free pool

   * Blazar puts hosts specified by the operator into the free pool aggregate
     on demand

2. User uses blazar to make a host reservation and to get the reservation id

   * Blazar picks up a host from the blazar's free pool

   * Blazar creates a new nova aggregate for that reservation and set that
     aggregate's metadata key to ``reservation:<resv_id>`` and puts the
     reserved host into that aggregate

3. User creates a VM with a flavor/image with ``reservation:<resv_id>``
   meta_data/extra_specs to consume the reservation

   * Nova finds in the flavor that the extra_spec has a key which starts with
     what is set in ``[scheduler]/placement_req_required_member_prefix``,
     and looks up the table for aggregates which has the specified metadata::

        required_prefix = CONF.scheduler.placement_req_required_member_prefix
        # required_prefix = 'reservation:'
        required_meta_data = get_flavor_extra_spec_starts_with(required_prefix)
        # required_meta_data = 'reservation:<resv_id>'
        required_aggs = aggs_whose_metadata_is(required_meta_data)
        # required_aggs = [<An aggregate for the reservation>]

   * Nova finds out that the default forbidden aggregate metadata prefix,
     which is set in
     ``[scheduler]/placement_req_default_forbidden_member_prefix``, is
     explicitly via the flavor, so skip::

        default_forbidden_prefix = CONF.scheduler.placement_req_default_forbidden_member_prefix
        # default_forbidden_prefix = ['reservation:']
        forbidden_aggs = set()
        if not get_flavor_extra_spec_starts_with(default_forbidden_prefix):
            # this is skipped because 'reservation:' is in the flavor in this case
            forbidden_aggs = aggs_whose_metadata_starts_with(default_forbidden_prefix)

   * Nova calls placement with required and forbidden aggregates::

        # We don't have forbidden aggregates in this case
        ?member_of=<required_aggs>

4. User creates a VM with a flavor/image with no reservation, that is,
   without ``reservation:<resv_id>`` meta_data/extra_specs.

   * Nova finds in the flavor that the extra_spec has no key which starts with
     what is set in ``[scheduler]/placement_req_required_member_prefix``,
     so no required aggregate is obtained::

        required_prefix = CONF.scheduler.placement_req_required_member_prefix
        # required_prefix = 'reservation:'
        required_meta_data = get_flavor_extra_spec_starts_with(required_prefix)
        # required_meta_data = ''
        required_aggs = aggs_whose_metadata_is(required_meta_data)
        # required_aggs = set()

   * Nova looks up the table for default forbidden aggregates whose metadata
     starts with what is set in
     ``[scheduler]/placement_req_default_forbidden_member_prefix``::

        default_forbidden_prefix = CONF.scheduler.placement_req_default_forbidden_member_prefix
        # default_forbidden_prefix = ['reservation:']
        forbidden_aggs = set()
        if not get_flavor_extra_spec_starts_with(default_forbidden_prefix):
            # This is not skipped now
            forbidden_aggs = aggs_whose_metadata_starts_with(default_forbidden_prefix)
        # forbidden_aggs = <blazar's free pool aggregates and the other reservation aggs>

   * Nova calls placement with required and forbidden aggregates::

        # We don't have required aggregates in this case
        ?member_of=!in:<forbidden_aggs>

Note that the change in the nova configuration file and change in the request
filter is an example and out of the scope of this spec. An alternative for this
is to let placement be aware of the default forbidden traits/aggregates (See
the `Bi-directional enforcement of traits`_ spec). But we agreed that it is not
placement but nova which is responsible for what traits/aggregate is
forbidden/required for the instance.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Tetsuro Nakamura (nakamura.tetsuro@lab.ntt.co.jp)

Work Items
----------

* Update the ``ResourceProviderList.get_all_by_filters`` and
  ``AllocationCandidates.get_by_requests`` methods to change the database
  queries to filter on "not this aggregate".
* Update the placement API handlers for ``GET /resource_providers`` and ``GET
  /allocation_candidates`` in a new microversion to pass the negative
  aggregates to the methods changed in the steps above, including input
  validation adjustments.
* Add functional tests of the modified database queries.
* Add gabbi tests that express the new queries, both successful queries and
  those that should cause a 400 response.
* Release note for the API change.
* Update the microversion documents to indicate the new version.
* Update placement-api-ref to show the new query handling.

Dependencies
============

None.

Testing
=======

Normal functional and unit testing.

Documentation Impact
====================

Document the REST API microversion in the appropriate reference docs.

References
==========

* `alloc-candidates-member-of`_ feature
* `granular-resource-request`_ feature

.. _`alloc-candidates-member-of`: https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/alloc-candidates-member-of.html
.. _`granular-resource-request`: https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/granular-resource-requests.html
.. _`BlazarFilter`: https://github.com/openstack/blazar-nova/tree/stable/rocky/blazarnova/scheduler/filters
.. _`Bi-directional enforcement of traits`: https://review.openstack.org/#/c/593475/
