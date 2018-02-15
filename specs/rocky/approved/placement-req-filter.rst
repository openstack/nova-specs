..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Placement Request Filtering
===========================

https://blueprints.launchpad.net/nova/+spec/placement-req-filter

As we move to having the scheduler rely on placement for providing the
initial host list, we discover other use cases and edge scenarios
where this may not be as efficient as we hope. With the goal of
getting cellsv1 users converted over to cellsv2, we also have to
consider deployment layouts that are in place that may be hard to
change, or have other benefits to very large users.

This spec specifically addresses one such concern of existing cellsv1
users, but represents a class of problems that center around a need to
make a more efficient request to placement than one purely based on
the resources and traits implied by the flavor the user has
chosen. Thus while a solution to this single problem is the goal of
the implementation described here, we aim to provide a generic
mechanism for solving those other problems along the way.

Problem description
===================

With cellsv1, some deployments use the top-level filtering cell
scheduler to pre-select a cell based soley on the tenant of the
user making the request. This then limits the amount of work
(i.e. hosts that must be filtered) that the scheduler within the cell
must do in order to make a selection. With the global nature of
cellsv2's scheduler and placement scope, this is not currently
possible. Thus, for a cloud with a large amount of free space, a
modest request that previously only considered ~200 hosts within a
cell (due to pre-selection of a cell by tenant) may now have to filter
many thousands of hosts in order to make a selection, most of which
are categorically not valid based on the tenant mapping.

Use Cases
---------

As a deployer, I wish to segregate users into cells for technical,
security, or budget reasons and need efficient scheduling of the
resources within those cells.

Proposed change
===============

This spec aims to add a small and lightweight mechanism to the early
phase of the scheduling process, where the request to placement is
formed from things like the flavor selected by the user. It should
provide us a way to opt in to certain behaviors, represented by simple
modular transformations made to the `RequestSpec` object before we
make the request to placement.

These modules will be called "request filters" and will perform
transformations on the `RequestSpec` object. They will be enabled
initially through dedicated configuration variables (ideally boolean)
in the short term for the sake of simplicity. As we grow more of
these, it may make sense to enable a list-of-request-filters sort of
configuration paradigm, like our existing scheduler filters.

For the tenant-to-cell limiting functionality, a single new request
filter will be provided and enabled by a single boolean configuration
knob in the ``scheduler`` group. When enabled, this filter will:

#. Look for host aggregates with metadata items of
   `filter_tenant_id=$tenant`, for the tenant id making the request
#. Augment the `RequestSpec` object to indicate that the result
   should be limited to the matching aggregates
#. Fail if no aggregates match

This depends on placement aggregates overlaying with host aggregates
configured with this key. Mirroring of those aggregates has been
planned to happen automatically in nova, but this functionality will
work with manual aggregate setup until that point and would only be
required by deployers wishing to use this feature.

To make this work, we will need to extend the
``RequestSpec.destination`` to contain an ``aggregates`` field, peer
to the ``host``, ``node``, and ``cell`` limits already present. The
``get_allocation_candidates()`` scheduler client method will also need
to consider those aggregates and pass the UUIDs to placement,
indicating that the resulting nodes must be members of one of those
aggregates. The aggregate metadata key used here
(``filter_tenant_id``) is the same as the one used by the
AggregateMultiTenancyIsolation scheduler filter to accomplish the same
thing via filtering. As such, existing users of that filter will be
able to easily convert to this request filter approach which will be
more efficient as well.

Alternatives
------------

We could build knowledge of tenant affinity into placement
itself. This would require a less generic change to the API, as well
as require another purpose-built change for the next thing we need
along these lines.

We could not provide a mechanism for this sort of filtering. This may
result in cellsv1 users not migrating to cellsv2, hamper cellsv2
adoption in general, or worst-case cause cellsv1 users to migrate away
from nova.

We could require that deployers handle this by assigning private
flavors with trait requirements to control scheduling. This would
result in a flavor explosion (aka `The Skittles(tm) Effect`) for cases
like the one driving this, where all tenants would need their own
flavors.

We could also take the approach of a request filter, but instead of
mapping tenants to host/placement aggregates, simply map them to a
an auto-generated trait with the tenant id in the name. This approach
would require a lot more trait churn on hosts when changing the
boundaries, but may be a very viable option for other use-cases of the
request filter pattern.

Data model impact
-----------------

The `Destination` object (stored in the `RequestSpec`) will need to
gain an `AggregateList` field. Besides this, no other data model
changes will be required (`Aggregate` already has metadata for us to
use).

REST API impact
---------------

The Nova REST API will not be changed. The placement API will need to
provide for aggregates to be specified in the ``allocation_candidates``
query, which will be handled as part of a different spec.

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

Large performance gain in some circumstances, derived from the ability
to consider smaller groups of hosts during scheduling.

Other deployer impact
---------------------

No impact to deployers not choosing to enable the
functionality. Direct impact to deployers that need to be able to
isolate tenants into cells (or other aggregates).

Developer impact
----------------

None.

Upgrade impact
--------------

None other than the usual placement-before-nova requirement when we
add something to placement that nova depends on.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

#. Add `AggregateList` to `Destination` object
#. Add a query method to AggregateList that allows filtering by key
   and value
#. Make scheduler request to placement include aggregate members
#. Add a lightweight request filter mechanism
#. Add a request filter that does the tenant-to-aggregate mapping operation


Dependencies
============

* This will require adding aggregate membership to
  the `allocation_candidates` API, which is covered by:
  https://blueprints.launchpad.net/nova/+spec/alloc-candidates-member-of
* While not a hard dependency, this will be more automatic with
  mirroring of host aggregates into placement, which is covered by:
  https://blueprints.launchpad.net/nova/+spec/placement-mirror-host-aggregates


Testing
=======

* Unit and functional tests for the filter mechanism, filter itself,
  and the scheduler-to-placement API changes are simple

Documentation Impact
====================

* Compute scheduler admin guide updates to describe the setup and use
  of this feature

References
==========

* Discussion with CERN folks about their requirements for moving from
  cellsv1: http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2018-02-14.log.html#t2018-02-14T15:41:34


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
