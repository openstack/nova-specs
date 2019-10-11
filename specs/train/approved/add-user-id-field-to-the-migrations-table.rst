..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Track user_id/project_id for migrations
=======================================

https://blueprints.launchpad.net/nova/+spec/add-user-id-field-to-the-migrations-table

The blueprint proposes tracking the user_id and project_id of the user that
initiated a server migration and exposing those values in the API.

Problem description
===================
By default, all server actions which create a migration record (live migration,
cold migration, resize, evacuate) except resize are initiated by an admin who
might not own the server. There could be multiple users within the same admin
project who migrate (or evacuate) servers. The migrations APIs do not expose
information about who actually migrated the server which is important for
auditing. The instance actions API does record the initiating user/project
but trying to correlate the instance actions to the migrations can be
complicated and error prone, especially if multiple migrations occur on the
same server in the same day.

Use Cases
---------
As an (admin) user, I would like to know who operates the instance through the
instance migration history without having to try and stitch that information
together from the migrations and instance actions APIs.

Proposed change
===============
When creating a Migration record, store the ``user_id`` and ``project_id``
from the request context, similar to an InstanceAction record.

In a new microversion, expose the ``user_id`` and ``project_id`` fields in the
following APIs:

* GET /os-migrations
* GET /servers/{server_id}/migrations
* GET /servers/{server_id}/migrations/{migration_id}

In addition, the ``GET /os-migrations`` request will add optional ``user_id``
and ``project_id`` query parameters for filtering migrations by user or
project.

Alternatives
------------
As noted above, each operation that generates a migration record will also
have an instance action and the instance action records the user_id and
project_id of who made the request. However, there is no other direct link
between the instance action record and the migration record so trying to use
the actions to correlate that information to the migrations can be complicated
and error prone, especially if a server is moved multiple times in the same
day. Since migration records are a top-level resource in the API like servers,
it makes sense for them to include the user_id/project_id like servers when
they are created and by whom.

Data model impact
-----------------
Add ``user_id`` and ``project_id`` columns to the ``migrations`` table. The
schema will be the same as in the ``instances`` and ``instance_actions``
tables::

  user_id = Column(String(255))
  project_id = Column(String(255))

The columns will be nullable since existing records would not have values for
those columns.

REST API impact
---------------
In a new microversion, expose the ``user_id`` and ``project_id`` parameters
in the following API responses:

* GET /os-migrations

  .. code-block:: json

    {
      "migrations": [
        {
          "created_at": "2012-10-29T13:42:02.000000",
          "dest_compute": "compute2",
          "dest_host": "1.2.3.4",
          "dest_node": "node2",
          "id": 1234,
          "instance_uuid": "8600d31b-d1a1-4632-b2ff-45c2be1a70ff",
          "new_instance_type_id": 2,
          "old_instance_type_id": 1,
          "source_compute": "compute1",
          "source_node": "node1",
          "status": "done",
          "updated_at": "2012-10-29T13:42:02.000000",
          "migration_type": "migration",
          "uuid": "42341d4b-346a-40d0-83c6-5f4f6892b650",
          "user_id": "ef9d34b4-45d0-4530-871b-3fb535988394",
          "project_id": "011ee9f4-8f16-4c38-8633-a254d420fd54"
        }
      ]
    }

* GET /servers/{server_id}/migrations

  .. code-block:: json

    {
      "migrations": [
        {
          "created_at": "2016-01-29T13:42:02.000000",
          "dest_compute": "compute2",
          "dest_host": "1.2.3.4",
          "dest_node": "node2",
          "id": 1,
          "server_uuid": "4cfba335-03d8-49b2-8c52-e69043d1e8fe",
          "source_compute": "compute1",
          "source_node": "node1",
          "status": "running",
          "memory_total_bytes": 123456,
          "memory_processed_bytes": 12345,
          "memory_remaining_bytes": 111111,
          "disk_total_bytes": 234567,
          "disk_processed_bytes": 23456,
          "disk_remaining_bytes": 211111,
          "updated_at": "2016-01-29T13:42:02.000000",
          "uuid": "12341d4b-346a-40d0-83c6-5f4f6892b650",
          "user_id": "ef9d34b4-45d0-4530-871b-3fb535988394",
          "project_id": "011ee9f4-8f16-4c38-8633-a254d420fd54"
        }
      ]
    }

* GET /servers/{server_id}/migrations/{migration_id}

  .. code-block:: json

    {
      "migration": {
        "created_at": "2016-01-29T13:42:02.000000",
        "dest_compute": "compute2",
        "dest_host": "1.2.3.4",
        "dest_node": "node2",
        "id": 1,
        "server_uuid": "4cfba335-03d8-49b2-8c52-e69043d1e8fe",
        "source_compute": "compute1",
        "source_node": "node1",
        "status": "running",
        "memory_total_bytes": 123456,
        "memory_processed_bytes": 12345,
        "memory_remaining_bytes": 111111,
        "disk_total_bytes": 234567,
        "disk_processed_bytes": 23456,
        "disk_remaining_bytes": 211111,
        "updated_at": "2016-01-29T13:42:02.000000",
        "uuid": "12341d4b-346a-40d0-83c6-5f4f6892b650",
        "user_id": "ef9d34b4-45d0-4530-871b-3fb535988394",
        "project_id": "011ee9f4-8f16-4c38-8633-a254d420fd54"
      }
    }

The key will always be returned but the value could be null for older records.

The ``GET /os-migrations`` API will also have optional ``user_id`` and
``project_id`` query parameters for filtering migrations by user and/or
project::

  GET /os-migrations?user_id=ef9d34b4-45d0-4530-871b-3fb535988394

  GET /os-migrations?project_id=011ee9f4-8f16-4c38-8633-a254d420fd54

  GET /os-migrations?user_id=ef9d34b4-45d0-4530-871b-3fb535988394&project_id=011ee9f4-8f16-4c38-8633-a254d420fd54

Security impact
---------------
None

Notifications impact
--------------------
None. ``InstanceActionPayload`` already contains ``action_initiator_user``
and ``action_initiator_project`` fields.

Other end user impact
---------------------
Update python-novaclient for the new microversion (and python-openstackclient
if it grows server migration resource CLIs in the future).

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Upgrade impact
--------------
None. The new columns in the database will be nullable as will the fields
on the Migration object and the API response can return null values. A data
migration to populate the values for existing migrations will not be added.

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  Brin Zhang

Work Items
----------
* Add ``user_id`` and ``project_id`` to the ``migrations`` table and
  Migration versioned object.
* Modify the API to expose the ``user_id`` and ``project_id`` fields in
  GET responses that expose migration resources. Also add ``user_id`` and
  ``project_id`` query parameters to ``GET /os-migrations`` for filtering
  the results.
* Add related tests
* Docs for the new microversion.

Dependencies
============
None

Testing
=======
* Add related unit test for negative scenarios.
* Add related functional test (API samples).

Tempest testing should not be necessary for this change.

Documentation Impact
====================
Update the API reference for the new microversion.

References
==========
None

History
=======
.. list-table:: Revisions
      :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
