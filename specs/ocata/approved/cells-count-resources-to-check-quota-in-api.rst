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
and marked as "in_use" when they are committed, and the reservarion record
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
database for the quota commit. By counting resources in the API to check quota,
we can reduce [*]_ the need for compute cells to write to the API database.
At least, we will eliminate the situation where a quota reserve/commit is split
across the API cell and compute cells.

.. [*] Quota reads and writes cannot be completely eliminated in compute cells
       in a special case: nova-compute de/allocating fixed IPs from
       nova-network during de/provisioning. This special case can be removed
       when nova-network is fully removed.

Use Cases
---------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons. When partitioned, coupling between the API cell
  and compute cells should be minimized.

Proposed change
===============

Consumed resources will be counted to check quota instead of the current
reserve/commit/rollback model.

* "Reserve," "commit," and "rollback" calls will be removed everywhere.

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

With the resource counting approach, it will be possible for a project to
consume more resources than they have quota if they are racing near the end
of their quota limits. This is because we must aggregate consumed resources
across instances in separate databases. So it would be possible for a quota
check Y to pass at the API and shortly after a racing request X also passed
quota check will have consumed the remaining resources allowed for the project,
and then request Y will consume more resources than the quota afterward.

Performance Impact
------------------

Performance will be adversely affected in the case of counting resources such
as cores and ram. This is because there is currently no project association
stored in the allocations records at present. In the future, we will be able
to query the placement API once it has more data and we can do an efficient
query through it. Until then, to count cores and ram, the following approach
is required:

  * Get all instances by project per cell, parsing the flavor JSON blobs and
    adding up the counts. For example::

      instance_get_all_by_filters(filters={'project_id': myproj},
                                  expected_attrs=['flavor'])

All other resources should be able to be counted in one step:

  * instances: this can be obtained from instance_mappings table in API DB.
    We may be able to create a tally from the aforementioned cores/ram query
    and use that instead of doing a new query of instance_mappings.
  * security_groups: deprecated in 2.36 and not checked in Nova with Neutron.
    This is checked in the API with nova-network. security_groups are in the
    cell database so this would be a cell DB read from the API to check.
  * floating_ips: deprecated in 2.36 and not checked in Nova with Neutron. This
    is checked when auto_assign_floating_ip allocates a floating ip with
    nova-network. floating_ips are in the cell database so this would be a
    local DB read until nova-network is removed.
  * fixed_ips: not checked in Nova with Neutron. This is checked when
    nova-compute de/allocates a fixed_ip with nova-network. fixed_ips are in
    the cell database so this would be a local DB read until nova-network is
    removed.
  * metadata_items: this is a limit on allowed number of image metadata items
    and is checked when image metadata requests come in. No counting of
    resources is necessary.
  * injected_files: Similar to metadata_items.
  * injected_file_content_bytes: Similar to metadata_items.
  * injected_file_path_bytes: Similar to metadata_items.
  * security_group_rules: Similar to security_groups.
  * key_pairs: this can be obtained from key_pairs table in API DB.
  * server_groups: this can be obtained from instance_groups table in API DB.
  * server_group_members: this can be obtained from instance_group_member table
    in API DB.

Other deployer impact
---------------------

None

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

None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Ocata
     - Introduced
