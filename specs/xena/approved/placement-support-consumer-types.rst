..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Support Consumer Types
======================

.. note::
    This is specification does not target the Nova services it only impacts the
    Placement service.

https://storyboard.openstack.org/#!/story/2005473

This spec aims at providing support for services to model ``consumer types``
in placement. While placement defines a consumer to be an entity consuming
resources from a provider it does not provide a way to identify similar
"types" of consumers and henceforth allow services to group/query them based
on their types. This spec proposes to associate each consumer to a particular
type defined by the service owning the consumer.

Problem description
===================

In today's placement world each allocation posted by a service is against a
provider for a consumer (ex: for an instance or a migration). However a
service may want to distinguish amongst the allocations made against its
various types of consumers (ex: nova may want to fetch allocations against
instances alone). This is currently not possible in placement and hence the
goal is to make placement aware of "types of consumers" for the services.

Use Cases
---------

* Nova using placement as its `quota calculation system`_: Currently this
  approach uses the nova_api database to calculate the quota on the "number of
  instances". In order for nova to be able to use placement to count the number
  of "instance-consumers", there needs to be a way by which we can
  differentiate "instance-consumers" from "migration-consumers".

* Ironic wanting to differentiate between "standalone-consumer" versus
  "nova-consumer".

Note that it is not within the scope of placement to model the coordination of
the consumer type collisions that may arise between multiple services during
their definition. Placement will also not be able to identify or verify correct
consumer types (eg, INTANCE versus INSTANCE) from the external service's
perspective.

Proposed change
===============

In order to model consumer types in placement, we will add a new
``consumer_types`` table to the placement database which will have two columns:

#. an ``id`` which will be of type integer.
#. a ``name`` which will be of type varchar (maximum of 255 characters) and
   this will have a unique constraint on it. The pattern restrictions for the
   name will be similar to placement traits and resource class names, i.e
   restricted to only ``^[A-Z0-9_]+$`` with length restrictions being {1, 255}.

A sample look of such a table would be:

+--------+----------+
|   id   |   name   |
+========+==========+
|   1    | INSTANCE |
+--------+----------+
|   2    | MIGRATION|
+--------+----------+

A new column called ``consumer_type_id`` would be added to the ``consumers``
table to map the consumer to its type.

The ``POST /allocations`` and ``PUT /allocations/{consumer_uuid}`` REST API's
will gain a new (required) key called ``consumer_type`` which is of type string
in their request body's through which the caller can specify what type of
consumer it is creating or updating the allocations for. If the specified
``consumer_type`` key is not present in the ``consumer_types`` table, a new
entry will be created. Also note that once a consumer type is created, it
lives on forever. If this becomes a problem in the future for the operators
a tool can be provided to clean them up.

In order to maintain parity between the request format of
``PUT /allocations/{consumer_uuid}`` and response format of
``GET /allocations/{consumer_uuid}``, the ``consumer_type`` key will also be
exposed through the response of ``GET /allocations/{consumer_uuid}`` request.

The external services will be able to leverage this ``consumer_type`` key
through the ``GET /usages`` REST API which will have a change in the format
of its request and response. The request will gain a new optional key called
``consumer_type`` which will enable users to query usages based on the consumer
type. The response will group the resource usages by the specified
consumer_type (if consumer_type key is not specified it will return the usages
for all the consumer_types) meaning it will gain a new ``consumer_type`` key.
Per consumer type we will also return a ``consumer_count`` of consumers of that
type.

See the `REST API impact`_ section for more details on how this would be done.

The above REST API changes and the corresponding changes to the ``/reshaper``
REST API will be available from a new microversion.

The existing consumers in placement will have a ``NULL`` value in their
consumer_type_id field, which means we do not know what type these consumers
are and the service to which the consumers belong to needs to update this
information if it wants to avail the ``consumer_types`` feature.

Alternatives
------------

We could create a new REST API to allow users to create consumer types
explicitly but it does not make sense to add a new API for a non-user facing
feature.

Data model impact
-----------------

The placement database will get a new ``consumer_types`` table and the
``consumers`` table will get a new ``consumer_type_id`` column that by default
will be ``NULL``.

REST API impact
---------------

The new ``POST /allocations`` request will look like this::

  {
    "30328d13-e299-4a93-a102-61e4ccabe474": {
      "consumer_generation": 1,
      "project_id": "131d4efb-abc0-4872-9b92-8c8b9dc4320f",
      "user_id": "131d4efb-abc0-4872-9b92-8c8b9dc4320f",
      "consumer_type": "INSTANCE", # This is new
      "allocations": {
        "e10927c4-8bc9-465d-ac60-d2f79f7e4a00": {
          "resources": {
            "VCPU": 2,
            "MEMORY_MB": 3
          },
          "generation": 4
        }
      }
    },
    "71921e4e-1629-4c5b-bf8d-338d915d2ef3": {
      "consumer_generation": 1,
      "project_id": "131d4efb-abc0-4872-9b92-8c8b9dc4320f",
      "user_id": "131d4efb-abc0-4872-9b92-8c8b9dc4320f",
      "consumer_type": "MIGRATION", # This is new
      "allocations": {}
    }
  }

The new ``PUT /allocations/{consumer_uuid}`` request will look like this::

  {
    "allocations": {
      "4e061c03-611e-4caa-bf26-999dcff4284e": {
        "resources": {
          "DISK_GB": 20
        }
      },
      "89873422-1373-46e5-b467-f0c5e6acf08f": {
        "resources": {
          "MEMORY_MB": 1024,
          "VCPU": 1
        }
      }
    },
    "consumer_generation": 1,
    "user_id": "66cb2f29-c86d-47c3-8af5-69ae7b778c70",
    "project_id": "42a32c07-3eeb-4401-9373-68a8cdca6784",
    "consumer_type": "INSTANCE" # This is new
  }

Note that ``consumer_type`` is a required key for both these requests at
this microversion.

The new ``GET /usages`` response will look like this for a request of type
``GET /usages?project_id=<project id>&user_id=<user id>`` or
``GET /usages?project_id=<project id>`` where the consumer_type key is not
specified::

  {
      "usages": {
        "INSTANCE": {
            "consumer_count": 5,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
        "MIGRATION": {
            "consumer_count": 2,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
        "unknown": {
            "consumer_count": 1,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
      }
  }

The new ``GET /usages`` response will look like this for a request of type
``GET /usages?project_id=<id>&user_id=<id>&consumer_type="INSTANCE"``
or ``GET /usages?project_id=<id>&consumer_type="INSTANCE"`` where the
consumer_type key is specified::

  {
      "usages": {
        "INSTANCE": {
            "consumer_count": 5,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
      }
  }

A special request of the form
``GET /usages?project_id=<project id>&consumer_type=all`` will be allowed to
enable users to be able to query for the total count of all the consumers. The
response for such a request will look like this::

  {
    "usages": {
        "all": {
            "consumer_count": 3,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
    }
  }

A special request of the form
``GET /usages?project_id=<project id>&consumer_type=unknown`` will be allowed
to enable users to be able to query for the total count of the consumers that
have no consumer type assigned. The response for such a request will look like
this::

  {
    "usages": {
        "unknown": {
            "consumer_count": 3,
            "DISK_GB": 5,
            "MEMORY_MB": 512,
            "VCPU": 2
        }
    }
  }

Note that ``consumer_type`` is an optional key for the ``GET /usages`` request.

The above REST API changes and the corresponding changes to the ``/reshaper``
REST API will be available from a new microversion.

Security impact
---------------

None.

Notifications impact
--------------------

N/A

Other end user impact
---------------------

The external services using this feature like nova should take the
responsibility of updating the consumer type of existing consumers
from ``NULL`` to the actual type through the
``PUT /allocations/{consumer_uuid}`` REST API.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

The ``placement-manage db sync`` command has to be run by the operators in
order to upgrade the database schema to accommodate the new changes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <melwitt>

Other contributors:
  <tssurya>
  <cdent>

Work Items
----------

* Add the new ``consumer_types`` table and create a new ``consumer_type_id``
  column in the ``consumers`` table with a foreign key constraint to the ``id``
  column of the ``consumer_types`` table.
* Make the REST API changes in a new microversion for:

   * ``POST /allocations``,
   * ``PUT /allocations/{consumer_uuid}``,
   * ``GET /allocations/{consumer_uuid}``,
   * ``GET /usages`` and
   * ``/reshaper``

Dependencies
============

None.


Testing
=======

Unit and functional tests to validate the feature will be added.


Documentation Impact
====================

The placement API reference will be updated to reflect the new changes.

References
==========

.. _quota calculation system: https://review.opendev.org/#/q/topic:bp/count-quota-usage-from-placement


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Xena
     - Reproposed
