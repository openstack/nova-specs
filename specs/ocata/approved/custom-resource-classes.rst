..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Resource Providers - Custom Resource Classes
============================================

https://blueprints.launchpad.net/nova/+spec/custom-resource-classes

We propose to provide the ability for an administrator to create a set of
special resource classes that indicate deployer-specific resources that can be
provided by a resource provider.

Problem description
===================

Some hardware resources should be represented as a singular unit of consumable
resource. These singular units of consumable resources may vary from one cloud
offering to another, and attempting to create a standardized resource class
identifier for these types of resources that can be used across different
OpenStack clouds is simply not possible.

We require a method for cloud administrators to create new resource classes
that represent consumable units of some resource.

Use Cases
---------

As a cloud deployer providing baremetal resources to my users, I wish to
utilize the new resource providers functionality for the Nova scheduler to
place a request for different configurations of baremetal hardware to a
provider of those resources. I also wish to use the new placement REST API to
see a consistent view of the inventory and allocations of those resources to
various users of my cloud.

As an NFV deployer, I have hardware that has some fully programmable gate array
(FPGA) devices. These FPGAs may be flashed with a synthesized RT netlist
containing an algorithm or entire software program that is accelerated. Each of
these algorithms has one or more contexts that can be consumed by a guest
virtual machine. I wish to allow my users to specify to launch an instance and
have the instance consume one or more of the contexts for a particular
algorithm that I have loaded onto the FPGAs on a compute node.

Proposed change
===============

We propose the addition of a few things:

* Changes and additions to `nova.objects` objects to handle custom resource
  classes. All custom resource classes will be prefixed with the string
  "CUSTOM\_".

* New `resource_classes` database table storing the string -> integer mapping
  for custom resource classes

* An additional placement REST API call for creating, modifying, deleting and
  querying custom resource classes

Alternatives
------------

None.

Data model impact
-----------------

A new lookup table for resource classes is introduced in the API database::

    CREATE TABLE resource_classes (
        id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        PRIMARY KEY (id),
        UNIQUE INDEX (name)
    );

The `nova.objects.fields.ResourceClass` is an Enum field that lists the
standard known resource classes like VCPU, MEMORY_MB, DISK_GB, etc. We will
need to make some modifications to this class and the object models that have a
`ResourceClass` field (`Allocation` and `Inventory` object models). We will
sort during the implementation phase the details about that, probably a
StringField field type that could allow us not touching the object version
anytime a new class is added.

This new `ResourceClass` object model would look up its integer index values in
a new cache utility that would look for string values in the enumerated
standard resource classes and, if not found, look up records in the new
`resource_classes` table.

REST API impact
---------------

A set of new REST API commands will be created on the placement REST API with a
new microversion:

* `GET /resource_classes`: Returns list of all resource classes (standard as
  well as custom)
* `POST /resource_classes`: Creates a new custom resource class
* `PUT /resource_classes/{name}`: Change the string name of an existing custom
  resource class
* `DELETE /resource_classes/{name}`: Removes a custom resource class

`GET /resource_classes`
***********************

Return a list of all resource classes defined for this Nova deployment.
Pagination could be envisaged during the implementation phase if we consider
that it could become a very long list, where the marker could be a resource
class name and the list be alphabetically sorted by name.

Example::

    200 OK
    Content-Type: application/json
    {
      "resource_classes": [
      {
        "name": "VCPU",
        "links": [
          {
            "rel": "self",
            "href": "/resource_classes/VCPU"
          }
        ]
      },
      {
        "name": "MEMORY_MB",
        "links": [
          {
            "rel": "self",
            "href": "/resource_classes/MEMORY_MB"
          }
        ]
      }
      ...
      {
        "name": "CUSTOM_BAREMETAL_GOLD",
        "links": [
          {
            "rel": "self",
            "href": "/resource_classes/CUSTOM_BAREMETAL_GOLD"
          }
        ]
      }
      ]
    }

`POST /resource_classes`
************************

Creates a new custom resource class.

Example::

    POST /resource_classes
    {
      "name": "CUSTOM_BAREMETAL_GOLD"
    }

The body of the request must match the following JSONSchema document::

    {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^CUSTOM\_[A-Z0-9_]*"
        },
    },
      "required": [
        "name"
      ]
      "additionalProperties": False
    }

The response body is empty. The headers include a location header
pointing to the created resource class::

    201 Created
    Location: /resource_classes/CUSTOM_BAREMETAL_GOLD

* A `400 Bad Request` response code will be returned if name is for a standard
  resource class -- i.e. VCPU or MEMORY_MB.
* A `409 Conflict` response code will be returned if another resource class
  exists with the provided name.

`PUT /resource_classes/{name}`
******************************

Changes the string name of an existing custom resource class.

Example::

    PUT /resource_classes/CUSTOM_BAREMETAL_GOLD
    {
      "name": "CUSTOM_BAREMETAL_SILVER"
    }

The body of the request must match the following JSONSchema document::

    {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^CUSTOM\_[A-Z0-9_]*"
        },
    },
      "required": [
        "name"
      ]
      "additionalProperties": False
    }

The response body is empty and the response code will be a `204 No Content`
upon successful name change.

* A `404 Not Found` response code will be returned if no such resource class
  matching the name is found.
* A `400 Bad Request` response code will be returned if name is for a standard
  resource class -- i.e. VCPU or MEMORY_MB.
* A `409 Conflict` response code will be returned if there is an existing
  resource class with the same name.

`DELETE /resource_classes/{name}`
*********************************

Deletes an existing custom resource class.

Example::

    DELETE /resource_classes/CUSTOM_BAREMETAL_GOLD

The response body is empty and the response code will be a `204 No Content`
upon successful deletion.

* A `404 Not Found` response code will be returned if no such resource class
  matching the name is found.
* A `400 Bad Request` response code will be returned if name is for a standard
  resource class -- i.e. VCPU or MEMORY_MB.
* A `409 Conflict` response code will be returned if there are existing
  inventories or allocations for the resource class.

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

None.

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
  jaypipes

Other contributors:
  cdent
  edleafe
  bauzas

Work Items
----------

* Create new `resource_classes` lookup table in API database
* Create `nova/objects/resource_class.py` object model, deprecating the old
  `nova.objects.fields.ResourceClass` classes
* Add all new placement REST API commands

Dependencies
============

* `generic-resource-pools` blueprint implemented

Testing
=======

Unit and functional API tests using Gabbi.

Documentation Impact
====================

API reference documentation needed.

References
==========

None.
