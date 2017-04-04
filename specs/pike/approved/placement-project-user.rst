..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Add project/user association to placement
=========================================

https://blueprints.launchpad.net/nova/+spec/placement-project-user

This cycle we are changing the quota system to count resources to check
quota instead of tracking usage and reservations separately. As things
currently stand, we must query cell tables to count things like cores
and ram to check against quota limits. There are a couple of problems
with the current approach:

  1. Querying all cells for instances owned by a project and summing their
     cores and ram counts is not efficient.
  2. Quota usage becomes effectively "freed" if contact with one or more
     cells is lost for any reason, until the cells return.

To address these problems, we propose adding project and user associations
to placement for consumers.


Problem description
===================

With the current resource counting approach, placement allocated resources
such as cores and ram must be counted by querying for instances owned by
a project in all cells and summing their cores and ram. The counts could
be more efficiently obtained if placement stored project/user associations
for resource consumers and we could query placement for allocations based
on project/user and resource classes.

There is also the problem of relying on cell databases for allocated
resource counts. If the API cell loses contact with a cell for some reason
(network issue, cell maintenance, transient cell database issue, etc), the
resources for that cell cannot be counted. The down cell's resources then
become omitted from the counted usage for the project/user, allowing them
to allocate additional resources in other cells in the meantime. If and when
the down cell returns, the project/user could then have allocated more
resources than their allowed quota limit.

Use Cases
---------

As an administrator of an OpenStack multiple cell environment, it's important
that my users not be able to exceed their allocated quota limits when cells are
down.

Proposed change
===============

Add a `consumers` table for placement that stores project/user associations
for consumers with fields: consumer_id, project_id, user_id::

    CREATE TABLE consumers (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        consumer_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(255) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        INDEX (consumer_id),
        INDEX (project_id, user_id)
    );

The records should have the same lifetime as `allocations` records.

The queries for allocations for a project/user will look like::

    GET /allocations?project_id=<uuid>
    GET /allocations?project_id=<uuid>&user_id=<uuid>

In placement, when a query is received it will look up the consumer_ids and
matching allocations by querying the `consumers` table joined with the
`allocations` table on consumer_id and return the allocations.

After the allocations are returned from placement, the quota counting code
can count cores and ram from the allocations.

Alternatives
------------

Another way to associate project/user with allocations would be to add
project_id and user_id columns to the `allocations` table. It would be more
direct than creating a `consumers` table with the associations but it wouldn't
be as generic. A `consumers` table could potentially be used for queries other
than just allocations.

Data model impact
-----------------

The following data model changes will be needed:

* New models for: `Consumer`

* New database table for `Consumer`

* Database migration will be needed to add the `consumers` table to the schema.

REST API impact
---------------

The GET method for /allocations will now accept new query strings in the URI
called 'project_id' and 'user_id' that will return a list of allocations
matching the project_id and user_id.

Example::

    GET /allocations?project_id=<uuid>

The response would be::

    200 OK
    Content-Type: application/json

    {
      "allocations": [
        {
          "resource_provider": {
            "uuid": "b6b065cc-fcd9-4342-a7b0-2aed2d146518"
          },
          "resources": {
            "VCPU": 2,
            "MEMORY_MB": 1024,
            ...
          }
        },
        {
          "resource_provider": {
            "uuid": "eaaf1c04-ced2-40e4-89a2-87edded06d64"
          },
          "resources": {
            "VCPU": 4,
            "MEMORY_MB": 4096,
            ...
          }
        }
      ]
    }

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

Performance of quota resource counting should be more efficient with the new
API over querying all cells for instances owned by a project and iterating
over them, summing the cores and ram values. Instead of N database queries
for N cells, there will be one database query by placement of consumers
associated with a project/user joined on allocations to get the matching
allocations. Performance will also be improved in that cells being temporarily
down will no longer have the potential for end users to exceed allowed quota
limits.

Other deployer impact
---------------------

Deployers must be aware of the ``nova-manage`` command that will perform one
time data migration to populate the `consumers` table from existing
`allocations` records.

Developer impact
----------------

None.

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

* Fix bug 1679750 where allocations are not cleaned up upon local delete
  https://bugs.launchpad.net/nova/+bug/1679750
* Create database migration that creates the `consumers` table
* Update AllocationList object to read/write the `consumers` table
* Add new query parameters for the placement allocations REST API to query
  allocations by project_id and user_id
* Add online data migration that pulls all `allocations` records and for each
  allocation, look up the instance via consumer_id and write its consumer to
  the `consumers` table using the project_id and user_id from the instance


Dependencies
============

The quota counting spec is a foundation for this work, since the need for the
project/user association and updates to the allocations REST API is based on
counting resources for checking quota.

* http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/cells-count-resources-to-check-quota-in-api.html


Testing
=======

New unit tests for the migration and changes to the AllocationList object will
be added. Gabbi functional tests will be added to test the new query parameters
in the allocations REST API.


Documentation Impact
====================

None.

References
==========

* http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/cells-count-resources-to-check-quota-in-api.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
