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

Add a ``consumers`` table for placement that stores project/user associations
for consumers with fields: consumer_id, project_id, user_id::

    CREATE TABLE consumers (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        consumer_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(255) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        INDEX (project_id, consumer_id),
        INDEX (project_id, user_id, consumer_id)
    );

The records should have the same lifetime as ``allocations`` records.

The queries for usages for a project/user will look like::

    GET /usages?project_id=<uuid>
    GET /usages?project_id=<uuid>&user_id=<uuid>

In placement, when a query is received it will look up the consumer_ids and
matching allocations by querying the ``consumers`` table joined with the
``allocations`` table on consumer_id and return the summarized usages.

After the usages are returned from placement, the quota counting code can use
them to check against quota limits.

Alternatives
------------

Another way to associate project/user with allocations would be to add
project_id and user_id columns to the ``allocations`` table. It would be more
direct than creating a ``consumers`` table with the associations but it
wouldn't be as generic. A ``consumers`` table could potentially be used for
queries other than just allocations.

Data model impact
-----------------

The following data model changes will be needed:

* New models for: ``Consumer``

* New database table for ``Consumer``

* Database migration will be needed to add the ``consumers`` table to the
  schema.

REST API impact
---------------

A new REST resource: ``/usages`` will be added and the GET method will accept
query strings in the URI called 'project_id' and 'user_id' that will return
usages matching the project_id and user_id. A usage is a sum of allocations
that match the project_id and user_id, per resource class. The addition of the
REST resource will require a new placement API microversion.

Example::

    GET /usages?project_id=<uuid>

The response would be::

    200 OK
    Content-Type: application/json

    {
      "usages": {
        "VCPU": 2,
        "MEMORY_MB": 1024,
        "DISK_GB": 50,
        ...
      }
    }

The PUT method of ``/allocations/{consumer_uuid}`` will be changed to accept
'project_id' and 'user_id' as required properties on payload as part of the
same new placement API microversion described earlier. They are considered to
be required because allocations are going to be written by either a human/user
or on behalf of a human/user, as a privileged API action. In the case of the
resource tracker, the project_id and user_id are easily obtained from the
Instance object.

Example::

    ALLOCATION_SCHEMA = {
      "type": "object",
      "properties": {
        "allocations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "resource_provider": {
                "type": "object",
                "properties": {
                  "uuid": {
                    "type": "string",
                    "format": "uuid"
                  }
                },
                "additionalProperties": False,
                "required": ["uuid"]
              },
              "resources": {
                "type": "object",
                "patternProperties": {
                  "^[0-9A-Z_]+$": {
                    "type": "integer",
                    "minimum": 1,
                  }
                },
                "additionalProperties": False
              }
            },
            "required": [
              "resource_provider",
              "resources"
            ],
            "additionalProperties": False
          }
        },
        "project_id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 255
        },
        "user_id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 255
        }
      },
      "required": [
        "allocations",
        "project_id",
        "user_id"
      ],
      "additionalProperties": False
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
allocations, which will be summed to represent usages. Performance will also be
improved in that cells being temporarily down will no longer have the potential
for end users to exceed allowed quota limits.

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

Primary assignee:
  melwitt

Other contributors:
  None

Work Items
----------

* Fix bug 1679750 where allocations are not cleaned up upon local delete
  https://bugs.launchpad.net/nova/+bug/1679750
* Create database migration that creates the ``consumers`` table
* Update AllocationList object to read/write the ``consumers`` table
* Add a new REST resource: ``/usages`` for the placement REST API to query
  usages by project_id and user_id as part of a new placement API microversion
* Add 'project_id' and 'user_id' as required properties on the allocations PUT
  request schema as part of the same new placement API microversion
* Update the resource tracker to send project_id and user_id when setting
  allocations in placement
* Bump the service version and add a conditional for whether to call placement
  for counting cores and ram usage, based on the service version. During an
  upgrade, old computes will be writing allocations without project_id and
  user_id, so we can't rely on placement for usage until all computes have been
  upgraded. Existing allocation records will self-heal when upgraded computes
  update them as part of the nova-compute periodic task:
  update_available_resource.


Dependencies
============

The quota counting spec is a foundation for this work, since the need for the
project/user association and updates to the allocations REST API is based on
counting resources for checking quota.

* http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/cells-count-resources-to-check-quota-in-api.html


Testing
=======

New unit tests for the migration and changes to the AllocationList object will
be added. Gabbi functional tests will be added to test the new request
parameters in the allocations REST API and the new ``/usages`` REST resource.


Documentation Impact
====================

The placement-api-ref will be updated to document the new ``/usages`` REST
resource and the new required request parameters for the PUT method of the
``/allocations/{consumer_uuid}`` REST API.

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
