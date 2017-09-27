..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Count resources to check quota in API for cells
===============================================

https://blueprints.launchpad.net/nova/+spec/cells-count-resources-to-check-quota-in-api

For cellsv2, quota tables are moving to the API database as data global to
a deployment. Currently, for instance delete, quota reservations are made in
the API and then committed in compute. This is a disconnect which couples
compute cells with the API cell. In cellsv2, we endeavor to decouple compute
cells from the API cell as much as possible -- ideally, cells should not
need to have the API database connection in their configuration.

We propose a new approach of counting consumed resources and checking the
count against the quota limits in the API instead of the current reserve/commit
model where a reservation record is created, quota usage records are created
and marked as "in_use" when they are committed, and the reservation record
deleted.


Problem description
===================

The current quota design consists of reservations and commits/rollbacks. A
simplified explanation of how it works during a create is: "reserve" creates a
reservation record and a usage record indicating resources are "reserved."
"Commit" updates the usage record to modify the "reserved" field, the "in use"
field, and deletes the reservation record. "Rollback" updates the usage record
to modify the "reserved" field and deletes the reservation record.

For instance delete, resources are first reserved in the API when a request is
received and then the reservation is later committed in compute when the
resources are freed. In cellsv2, this means compute cells will write to the API
database for the quota commit if the current quota model is kept. If we instead
count resources in the API to check quota, it will be possible in the future
[*]_ to decouple compute cells from the API cell completely.

.. [*] Quota reads cannot be completely eliminated in compute cells in a
       special case: nova-compute de/allocating fixed IPs from nova-network
       during de/provisioning. Nova-network will need to read quota limits from
       the API database to check quota. This special case can be removed when
       nova-network is fully removed.

Use Cases
---------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons. When partitioned, coupling between the API cell
  and compute cells should be minimized.

Proposed change
===============

Consumed resources will be counted to check quota instead of the current
reserve/commit/rollback model.

* "Reserve," "commit," and "rollback" calls will be removed everywhere. Quota
  checks will instead consist of reading the quota limits from the API database
  and comparing the limit with the resource count.

* "Reserve" calls will be replaced with something like "check_resource_count"
  which will query the databases for consumed resources, count them, and raise
  OverQuota if quota limits for the project can't accomodate the request.

Alternatives
------------

The initial proposal for this work was to commit quota immediately in the API
wherever possible and is an alternative approach to this one. The drawback to
committing quota immediately in the API is that it can't be entirely avoided
for a failed resize scenario. If a resize fails, resource consumption must
be updated accordingly in the quota_usages records whereas with a resource
counting approach, no such update would be needed.

Data model impact
-----------------

We could drop the reservations and quota_usages tables from the API database as
they won't be used.

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

With the resource counting approach, it will be possible for a project to
consume more resources than they have quota if they are racing near the end
of their quota limits. This is because we must aggregate consumed resources
across instances in separate databases. So it would be possible for a quota
check Y to pass at the API and shortly after a racing request X also passed
quota check will have consumed the remaining resources allowed for the project,
and then request Y will consume more resources than the quota limit afterward.

Performance Impact
------------------

Performance will be adversely affected in the case of counting resources for
cores and ram. This is because there is currently no project/user association
with allocations in placement. In the absence of an efficient method through
the placement API, to count cores and ram, the following approach is required:

  * Get all instances by project per cell and add up the vcpus and memory_mb
    counts. For example::

      instance_get_all_by_filters(filters={'deleted': False,
                                           'project_id': myproj})

This approach also has the caveat that counting of instances, cores, and ram
is not possible when a cell is down. This means when a cell is down, the usage
for instances, cores, and ram will not contain the resources in the down cell,
enabling the possibility of allocating new resources in available cells, and
going over quota when the down cell returns. In practice, until multicell is
possible, this should not be a problem in the single cell case.

The plan is to add project/user associations for allocations in placement and
add the ability to query for allocations based on project/user. When the query
is available, the counting of cores and ram in cells will be replaced with a
call to the placement API for allocations which is resilient to down cells.

All other resources should be able to be counted in one step:

  * instances (ReservableResource): This can be obtained from instance_mappings
    table in API DB.
    We may be able to create a tally from the aforementioned cores/ram query
    and use that instead of doing a new query of instance_mappings.
  * security_groups (ReservableResource): Deprecated in 2.36 and not checked in
    Nova with Neutron.
    This is checked in the API with nova-network. security_groups are in the
    cell database so this would be a cell DB read from the API to check.
  * floating_ips (ReservableResource): Deprecated in 2.36 and not checked in
    Nova with Neutron.
    This is checked when auto_assign_floating_ip allocates a floating ip with
    nova-network. floating_ips are in the cell database so this would be a
    local DB read until nova-network is removed.
  * fixed_ips (ReservableResource): Not checked in Nova with Neutron.
    This is checked when nova-compute de/allocates a fixed_ip with
    nova-network. fixed_ips are in the cell database so this would be a local
    DB read until nova-network is removed.
  * metadata_items (AbsoluteResource): This is a limit on allowed number of
    image metadata items and is checked when image metadata requests come in.
    No counting of resources in the database is necessary.
  * injected_files (AbsoluteResource): Similar to metadata_items.
  * injected_file_content_bytes (AbsoluteResource): Similar to metadata_items.
  * injected_file_path_bytes (AbsoluteResource): Similar to metadata_items.
  * security_group_rules (CountableResource): Similar to security_groups.
  * key_pairs (CountableResource): This can be obtained from key_pairs table in
    API DB.
  * server_groups (ReservableResource): This can be obtained from
    instance_groups table in API DB.
  * server_group_members (CountableResource): This can be obtained from
    instance_group_member table in API DB.

Here is an explanation of the resource types, taken from a ML post [1]_:

  * ReservableResource: Can be used with reservations, resources are stored in
    the DB.
  * AbsoluteResource: Number of resources are not stored in the DB.
  * CountableResource: Subclass of AbsoluteResource except resources are stored
    in the DB. Has a counting function that will be called to determine the
    current counts of the resource. Not intended to count by project ID.

With the new approach, it seems like ReservableResources should be changed to
CountableResources with a count function provided for each.

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2015-December/081334.html

Other deployer impact
---------------------

The "nova-manage project quota_usage_refresh" command can be deprecated as
refreshing quotas would no longer be something we do.

Developer impact
----------------

Nova developers will no longer call quota "reserve," "commit," or "rollback."
Instead, they will call quota "check_resource_count" or similar when adding a
new API which will consume quota.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  None

Work Items
----------

* Add a method in nova/objects/quota.py called check_resource_count that counts
  consumed resources and raises OverQuota if the request would go over quota
  limits.

* Remove reserve/commit/rollback everywhere.

* Mark "reserve," "commit," and "rollback" methods as DEPRECATED in the
  docstrings to prevent their further use.


Dependencies
============

None


Testing
=======

New unit tests will be added to cover the new resource counting scenarios.

For the most part, this work should be transparent to end-users, so the
existing suite of unit, functional, and integration tests should suffice
for testing what is proposed.

There is an outstanding review for a regression test for the "quota out of
sync" bug that could be used to verify this proposal solves that problem
as a side effect.


Documentation Impact
====================

None


References
==========

* https://etherpad.openstack.org/p/ocata-nova-summit-cellsv2-quotas


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
   * - Pike
     - Re-proposed
