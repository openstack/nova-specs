..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Use uuids in services and os-hypervisors APIs
=============================================

`<https://blueprints.launchpad.net/nova/+spec/service-hyper-uuid-in-api>`_

To work with services and hypervisors (compute nodes) in the compute REST API
we currently expose and take primary key IDs. In a multi-cell
deployment, these IDs are not unique. This spec proposes exposing a uuid for
services and hypervisors in the REST API to uniquely identify a resource
regardless of which cell it is in.


Problem description
===================

We currently leak database id fields (primary keys) out of the compute REST
API for services and compute_nodes which are all in a cell database (the
'nova' database in a cells v2 deployment). These are in the `os-services` and
`os-hypervisors` APIs, respectively.

For example, to delete a service record, you must issue a DELETE request to
``/os-services/{service_id}`` to delete the service record with that id.

The `os-hypervisors` API exposes the id in GET (index) requests and uses it in
the "show" and "uptime" methods to look up the ComputeNode object by that id.

This is ugly but functional in a single-cell deployment. However, in a
multi-cell deployment, we have no context on which cell we should query to get
service/node details from, since you could have multiple cells each with a
nova-compute service and compute node with id 1, so which cell do you pick to
delete the service or show details about the hypervisor?

Use Cases
---------

As a cloud administrator, I want to uniquely identify the resources in my
cloud regardless of which cell they are in and be able to get details about
and delete them.

Proposed change
===============

This blueprint proposes to add a microversion to the compute REST API which
replaces the usage of the id field with a uuid field. The uuid would be
returned instead of the id in GET responses and also taken as input for the id
in CRUD APIs.

Then when a request to delete a service is made, if the uuid is provided we
can simply iterate cells until we find the service, or error with a 404.

Before the microversion, if an id is passed and there is only one cell, or no
duplicates in multiple cells, we will continue to honor the request. But if an
id is passed on the request (before the microversion) and we cannot uniquely
identify the record out of multiple cells, we error with a 400. This is
similar behavior to how creating a server works when a network or port is not
provided and there are multiple networks available to the project, we fail
with a 400 "NetworkAmbiguous" error.

The compute_nodes table already has a uuid field. The services table, however,
does not, so as part of this blueprint we will need to add a
uuid column to that table and corresponding versioned object.

Alternatives
------------

Alternatives to exposing just the basic uuid and using it to iterate over
potentially multiple cells until we find a match, is to encode the cell uuid
in the resource uuid. For example, if we could simply return
``{cell_uuid}-{resource_uuid}``.

Then rather than iterating all cells to find the resource, we could decode the
input uuid to get the cell we need.

This is not a recommended alternative because it encodes the cell in the REST
API which is something we have said in the past we did not want to do, and is
similar to how cells v1 does namespacing on cells. It would also mean that
parts of the compute API are encoding a cell uuid and others, like the
`servers` API, are not. This could lead to maintenance issues in the actual
code since we would have different lookup operations for different resources.

Another alternative is creating mapping tables in the Nova API database, like
the ``host_mappings`` and ``instance_mappings`` tables. This alternative is
not recommended, at least not at this time, because the need for working with
service records should be relatively small.

Data model impact
-----------------

The `services` table in the cell (nova) database will have a nullable uuid
column added. The column will be nullable due to existing records which do
not have the uuid field.

We can migrate the data on access through the versioned object, and/or
provide online data migrations to add uuids to existing records during an
upgrade.

REST API impact
---------------

os-hypervisors
~~~~~~~~~~~~~~

There are only ``GET`` methods in this API. They will all be changed
to return the uuid value for the `id` field and take as input a uuid
value for the ``{hypervisor_id}``. We cannot use the `query parameter
validation`_ added in Ocata to validate that the ID passed in is a uuid since
it is not be a query parameter. Therefore, we will need to validate the
input `id` value is a uuid in code.

The following APIs will also be changed::

   * GET /os-hypervisors/{hypervisor_hostname_pattern}/search
   * GET /os-hypervisors/{hypervisor_hostname_pattern}/servers

Both of those APIs return a list of matches given the hostname
search pattern. While not directly needed to the problem stated
in this spec, we will take the opportunity of the microversion change
in this API to make these better. The `hypervisor_hostname_pattern` will
change to a query parameter.

* Old: GET /os-hypervisors/{hypervisor_hostname_pattern}/search

* New: GET /os-hypervisors?hypervisor_hostname=xxx

Example request::

  GET /os-hypervisors?hypervisor_hostname=london1.compute

Example response::

  {
    "hypervisors": [
      {
        "hypervisor_hostname": "london1.compute.1",
        "id": "37c62dfd-105f-40c2-a749-0bd1c756e8ff",
        "state": "up",
        "status": "enabled"
      }
    ]
  }


* Old: GET /os-hypervisors/{hypervisor_hostname_pattern}/servers

* New: GET /os-hypervisors?hypervisor_hostname=xxx&with_servers=true

Example request::

  GET /os-hypervisors?hypervisor_hostname=london1.compute&with_servers=true

Example response::

  {
    "hypervisors": [
      {
        "hypervisor_hostname": "london1.compute.1",
        "id": "37c62dfd-105f-40c2-a749-0bd1c756e8ff",
        "state": "up",
        "status": "enabled",
        "servers": [
          {
            "name": "test_server1",
            "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
          },
          {
            "name": "test_server2",
            "uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
          }
        ]
      }
    ]
  }

.. _query parameter validation: https://specs.openstack.org/openstack/nova-specs/specs/ocata/implemented/consistent-query-parameters-validation.html

os-services
~~~~~~~~~~~

The following API methods which take as input and/or return the integer
primary key id in the response will be updated to take/return a uuid::

   * GET /os-services
   * DELETE /os-services/{service_id}

For example:

**GET /os-services**

Response::

   {
      "services": [
         {
            "id": "8e6e4ab6-0662-4ff5-8994-dde92bedada1",
            "binary": "nova-scheduler",
            "disabled_reason": "test1",
            "host": "host1",
            "state": "up",
            "status": "disabled",
            "updated_at": "2012-10-29T13:42:02.000000",
            "forced_down": false,
            "zone": "internal"
         },
         {
            "id": "3fe90b52-1d67-4f03-9ed3-5fbf1a6fa1e1",
            "binary": "nova-compute",
            "disabled_reason": "test2",
            "host": "host1",
            "state": "up",
            "status": "disabled",
            "updated_at": "2012-10-29T13:42:05.000000",
            "forced_down": false,
            "zone": "nova"
         },
      ]
   }

**DELETE /os-services/3fe90b52-1d67-4f03-9ed3-5fbf1a6fa1e1**

There is no response for a successful delete operation.


The **action** APIs do not take an id to identify the service on which to
perform an action. These include::

   * PUT /os-services/disable
   * PUT /os-services/disable-log-reason
   * PUT /os-services/enable
   * PUT /os-services/force-down

Unlike the ``/servers/{server_id}/action`` APIs which take the action in
the request body, these APIs do not take a specific service id. The request
body contains a ``host`` and ``binary`` field to identify the service.

As part of this microversion, we will collapse those action APIs into a single
PUT method which supports all of the actions and takes a ``service_id`` as
input to uniquely identify the service rather than a body with the ``host``
and ``binary`` fields.

What follows are examples of the old and new formats for each action API.

* PUT /os-services/disable

  Old request::

    PUT /os-services/disable
    {
        "host": "host1",
        "binary": "nova-compute"
    }

  New request::

    PUT /os-services/{service_id}
    {
        "status": "disabled"
    }

* PUT /os-services/disable-log-reason

  Old request::

    PUT /os-services/disable-log-reason
    {
        "host": "host1",
        "binary": "nova-compute",
        "disabled_reason": "test2"
    }

  New request::

    PUT /os-services/{service_id}
    {
        "status": "disabled",
        "disabled_reason": "test2"
    }

* PUT /os-services/enable*

  Old request::

    PUT /os-services/enable
    {
        "host": "host1",
        "binary": "nova-compute"
    }

  New request::

    PUT /os-services/{service_id}
    {
        "status": "enabled"
    }

* PUT /os-services/force-down

  Old request::

    PUT /os-services/force-down
    {
        "host": "host1",
        "binary": "nova-compute",
        "forced_down": true
    }

  New request::

    PUT /os-services/{service_id}
    {
        "forced_down": true
    }

We will also provide a full response for the PUT method now. For example:

* PUT /os-services/disable-log-reason

  Old response::

    {
        "service": {
            "binary": "nova-compute",
            "disabled_reason": "test2",
            "host": "host1",
            "status": "disabled"
        }
    }

  New response::

    {
        "service": {
            "id": "ade63841-f3e4-47de-840f-815322afa569",
            "binary": "nova-compute",
            "disabled_reason": "test2",
            "host": "host1",
            "state": "up",
            "status": "disabled",
            "updated_at": "2012-10-29T13:42:05.000000",
            "forced_down": false,
            "zone": "nova"
        }
    }


Security impact
---------------

None

Notifications impact
--------------------

Services
~~~~~~~~

The ``service.update`` versioned notification payload will be updated to
include the new uuid field.

Hosts
~~~~~

There are legacy unversioned notifications for actions on a compute node,
such as ``HostAPI.set_enabled.start``. These are not converted to using
versioned notifications yet, so until they are, there are no changes needed.

Other end user impact
---------------------

Since the REST API changes do not change the 'id' key in the response, only
the value, there should not need to be any changes in python-novaclient.

Performance Impact
------------------

None. Since we do not have a mapping table for services in the nova_api
database, we already have to iterate cells looking for a match, as seen
in this change: https://review.openstack.org/#/c/442162/

Other deployer impact
---------------------

Once deployers have multiple cells, they may have to update tooling to
specify the microversion to uniquely identify hypervisors or services,
for example, to delete a service.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann (mriedem)

Other contributors:
  Dan Peschman (dpeschman)

Work Items
----------

* Write a database schema migration to add the services.uuid column.
* Add the uuid field to the Service object.
   * Generate a uuid for new services if not specified during create().
   * Generate and save a uuid for old services upon retrieval from the
     database, like when compute nodes got a uuid [1]_.
* Add `get_by_uuid` methods to the ComputeNode and Service objects.
* Add an online data migration for service uuids like what we had for compute
  nodes [2]_.
* Update the ``nova.compute.api.HostAPI`` methods which take an ID and check
  if the ID is a uuid and if so, query for the resource using the
  `get_by_uuid` method on the object, otherwise use `get_by_id` as today.
* Add the microversion to the `os-hypervisors` and `os-services` APIs
  including validation to ensure the incoming id is a uuid. This also includes
  changing the request format of the `os-services` PUT method. This is likely
  going to be a large and relatively complicated change to review, but given
  all of these changes are going to be in the same microversion we cannot
  realistically break these changes up.
* Update the compute API response schema validation for hypervisors [3]_ and
  services [4]_. Note that the Tempest response schema already allows for
  integers or strings. As part of this change, we should update the response
  schema validation in Tempest to be strict that the hypervisor and service id
  should be a uuid after this new microversion.


Dependencies
============

None


Testing
=======

* Unit tests for negative scenarios, like not being able to find a service by
  uuid in multiple cells. We should also test passing a non-uuid integer value
  to the changed APIs with the new microversion to ensure the query parameter
  validation makes that request fail with a 400 error.
* Functional testing for API samples to ensure the 'id' value in a response
  after the microversion is a uuid and not an integer.
* Tempest API tests *may* be added, although we can probably handle that same
  test coverage with in-tree functional tests.
* We will have to test all of the `os-services` PUT method changes with
  in-tree functional tests because Tempest does not test disabling or forcing
  down a compute service since that would break a concurrent multi-tenant
  Tempest run.


Documentation Impact
====================

The `os-services`_ and `os-hypervisors`_ API reference docs will need to be
updated to note the new microversion takes as input and returns in the
response a uuid value for the 'id' key.

.. _os-services: https://developer.openstack.org/api-ref/compute/#compute-services-os-services
.. _os-hypervisors: https://developer.openstack.org/api-ref/compute/#hypervisors-os-hypervisors


References
==========

.. [1] https://github.com/openstack/nova/blob/13.0.0/nova/objects/compute_node.py#L243
.. [2] https://github.com/openstack/nova/blob/13.0.0/nova/db/sqlalchemy/api.py#L6436
.. [3] https://github.com/openstack/tempest/blob/15.0.0/tempest/lib/api_schema/response/compute/v2_1/hypervisors.py#L68
.. [4] https://github.com/openstack/tempest/blob/15.0.0/tempest/lib/api_schema/response/compute/v2_1/services.py#L27


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
