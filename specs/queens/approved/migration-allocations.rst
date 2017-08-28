..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Migration Allocations
=====================

https://blueprints.launchpad.net/nova/+spec/migration-allocations

In Pike, we realized that there is a gap in the way we were planning
to handle allocations for instances during move operations. In order
to avoid releasing resources on the source node in order to claim
against the target node, we need a placeholder or temporary
owner. Currently, we solve this by allocating against the source and
destination nodes for the instance, so it looks like the instance is
using resources on both at the same time. This works, but it makes it
harder to determine which node owns the process of releasing the other
half of this "double" allocation during success and failure
scenarios. Things are further complicated by the potential for
same-host migrations.

Problem description
===================

The problem we have is that currently the scheduler must know that
we're performing a move operation, and must add an allocation for the
instance against the target node, leaving the existing allocation
against the source node. After a successful or failed migration, one
of the compute nodes must clean up the correct half of the doubled
allocation to avoid the instance continuing to consume more than one
spot.

Use Cases
---------

As an operator, I want proper resource accounting during a move
operation to make sure compute nodes don't become overcommitted while
instances are moving.

As a nova developer, I want a clear assignment of responsibilities for
each allocation in placement so that the code to allocate and
deallocate for an instance is simple and straightforward.

Proposed change
===============

The overall proposed change is to let the migration operation itself,
as identified by a migration record in the database, "own" one of the
two allocations necessary to reserve resources. Instead of trying to
have the instance be the consumer of two sets of allocations against
the two nodes involved (source and destination), we can let the
instance own one and the migration own the other.

In order to do this, the migration record must have a uuid identifier,
which is the first change that needs to be made.

Once we have that, we will change the existing migration code to
replace the allocation that the instance has against the source node
with an identical one with the migration as the owner. Next, we
allocate for the instance (new flavor if resizing) against the
destination node. If the migration is successful, we can simply delete
the migration-owned allocation against the source node when the
operation is complete (or confirmed). Upon failure, we do the
opposite, deleting the target allocation and replacing the source
allocation with one owned by the instance.

The benefit here is that instead of trying to double-allocate for an
instance, and then having to subtract the source node/flavor from that
allocation on success, we can simply operate on allocations atomically
(i.e. create/delete) as the design intends. This makes the math and
mechanics the same for single and multi-host move operations, and
avoids one compute node manipulating allocations against another.

There is another major issue with the code as it stands today, in the
case of a single-host resize. Placement has a notion of a max_unit for
a given resource, which defines the upper limit of that resource that
any one consumer may allocate. If our allocation for, say, VCPU is
more than half of the max_unit, then a single-host resize will end up
attempting to allocate more than the max_unit for the
summed-during-resize allocation and will fail. The proposed change
will end up with the migration owning the original allocation and the
instance owning the new one, which will work because they are separate
allocations.

Alternatives
------------

When we discovered this issue late in Pike, we implemented the primary
alternative approach because it was less disruptive. That option is to
replace the allocation for the instance against the source node with
one against both the source and destination nodes during the
operation. This is still an option, but in practice the math
(especially for single-host moves) is vague and imprecise, and the
ownership responsibility for each compute node is obscure.

Data model impact
-----------------

The primary impact here is adding a uuid to the migration object which
can be used as the consumer for the source allocation in placement.

REST API impact
---------------

No direct API impact

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

If there are custom tools developed to read usage information out of
placement, then there could be some user-visible change between pike
and queens. This would be in the realm of a pike deployment showing a
large intermediate allocation/usage by the instance, which won't
happen after this change unless the tool takes migration-owned
allocations into account.

Performance Impact
------------------

None.

Other deployer impact
---------------------

As mentioned above, deployers could see some impact here if they have
written custom tools against placement for data gathering. However, it
seems unlikely at this point.

Developer impact
----------------

Developer impact of this will be overwhelmingly positive once the
initial complexity of handling the migration of the "pike way" to the
"queens way". Ownership of the allocations will be clear and concise,
and the code required for cleanup after a migration will be
significantly simpler.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Add a uuid to the migration record
* Migrate existing/outstanding migration records to give them a uuid
* Make the compute node code able to handle either the doubled
  allocation strategy (pike) or the split allocation strategy (queens)
* Make the scheduler create allocations using either strategy,
  determined by whether or not there are pike nodes in the deployment

Dependencies
============

* To optimize our behavior, we need an additional API in placement to
  allow us to submit multiple allocations for different consumers in a
  single atomic operation. See
  https://blueprints.launchpad.net/nova/+spec/post-allocations for the
  related work.
* Ideally we would expose the migration uuid from the os-migrations
  API, in case admins need to be able to correlate the instance with
  its migration allocation for external tooling or auditing.

Testing
=======

As part of the fire drill at the end of pike, we now have a fairly
comprehensive set of functional tests that verify the allocation
behavior during a migration. These should outline the coverage we
need, although the expected behavior at each point will be
different. These tests could easily be duplicated and preserved for
testing pike behavior, and then the original tests can be modified to
verify queens behavior. Once we're past queens we can delete the pike
behavior tests when we drop that code.

Documentation Impact
====================

Since this should ideally be invisible from the outside, no
documentation impact is expected.

References
==========

See the mess in pike.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
