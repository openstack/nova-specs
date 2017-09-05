..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
Flavor description
==================

https://blueprints.launchpad.net/nova/+spec/flavor-description

Expose a description field on the flavor resource so that operators
can describe a flavor in terms that a user can understand without
relying on verbose names or users needing to understand extra specs.


Problem description
===================

Administrators are only able to describe flavors via the name and id fields
and generally one would like to avoid putting too much detail in those types
of fields, especially for things like flavor extra specs that define the
behavior of an instance created with that flavor, for example, baremetal nodes,
or host aggregates for different hypervisors in a multi-hypervisor deployment.

Use Cases
---------

As an administrator, I want to provide simple names for my flavors but describe
in some detail what is special about each flavor, especially if it has extra
specs or certain limitations.

Proposed change
===============

This is fairly straight-forward and just involves modifying the
``flavors`` APIs to allow specifying a description field when creating
or updating a flavor and returning the description when showing flavor details.

Microversion 2.47 changed how the embedded flavor in a server response
body looks by showing the full flavor details rather than just an id/link.
Despite this change, we will *not* include the embedded flavor description in
the server response body.

Alternatives
------------

Use the name or id fields, which are both strings, but as noted in the
problem description this can get messy.

Data model impact
-----------------

A new nullable ``description`` `TEXT`_ column will be added to the ``flavors``
table in the API database with a maximum length of 65535.

Since we will not index or filter on this field, making it a TEXT (65536 bytes)
versus TINYTEXT (256 bytes) field is not really a concern.

.. note:: We store a serialized version of the flavor associated with an
    instance record in the ``instance_extras`` table and that is a TEXT column.
    Since we are not going to expose the embedded instance flavor description
    in the API, we will trim the flavor description from the serialized version
    stored in the ``instance_extras`` table.

.. _TEXT: https://dev.mysql.com/doc/refman/5.7/en/storage-requirements.html#data-types-storage-reqs-strings

REST API impact
---------------

All of the following changes would happen within a new microversion.

* POST /flavors

  Allow a ``description`` field in the request and response when creating a
  flavor.

  The `schema`_ would be the same as the description field in the 2.19
  microversion for ``POST /servers`` *except* the ``maxLength`` will be 65535.

  The samples below are not particularly interesting since the real value
  in a description field is in describing behaviors or limitations of a flavor
  which is more important when it has extra specs tied to host aggregates,
  which happens after the flavor is initially created.

  Request sample::

     {
       "flavor": {
           "name": "2vcpu-1024ram-10disk-baremetal-10gb",
           "description": "Baremetal flavor with 10GB network card.",
           "ram": 1024,
           "vcpus": 2,
           "disk": 10,
           "id": "f68c1474-4ba6-4291-bbdc-2c7865c0f33f"
       }
     }

  Response sample::

     {
       "flavor": {
           "OS-FLV-DISABLED:disabled": false,
           "disk": 10,
           "OS-FLV-EXT-DATA:ephemeral": 0,
           "os-flavor-access:is_public": true,
           "id": "f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
           "links": [
               {
                   "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "self"
               },
               {
                   "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "bookmark"
               }
           ],
           "name": "2vcpu-1024ram-10disk-baremetal-10gb",
           "description": "Baremetal flavor with 10GB network card.",
           "ram": 1024,
           "swap": "",
           "rxtx_factor": 1.0,
           "vcpus": 2
       }
     }

* GET /flavors/detail and GET /flavors/{flavor_id}

  Add a required ``description`` field in the response when getting flavor
  details. If the flavor does not have a description, None will be returned.

  GET /flavors/detail response sample::

     {
       "flavors": [
           {
              "OS-FLV-DISABLED:disabled": false,
              "disk": 10,
              "OS-FLV-EXT-DATA:ephemeral": 0,
              "os-flavor-access:is_public": true,
              "id": "f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
              "links": [
                  {
                      "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                      "rel": "self"
                  },
                  {
                      "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                      "rel": "bookmark"
                  }
              ],
              "name": "2vcpu-1024ram-10disk-baremetal-10gb",
              "description": "Baremetal flavor with 10GB network card.",
              "ram": 1024,
              "swap": "",
              "rxtx_factor": 1.0,
              "vcpus": 2
           }
       ]
     }

  GET /flavors/{flavor_id} response sample::

     {
       "flavor": {
           "OS-FLV-DISABLED:disabled": false,
           "disk": 10,
           "OS-FLV-EXT-DATA:ephemeral": 0,
           "os-flavor-access:is_public": true,
           "id": "f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
           "links": [
               {
                   "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "self"
               },
               {
                   "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "bookmark"
               }
           ],
           "name": "2vcpu-1024ram-10disk-baremetal-10gb",
           "description": "Baremetal flavor with 10GB network card.",
           "ram": 1024,
           "swap": "",
           "rxtx_factor": 1.0,
           "vcpus": 2
       }
     }

* PUT /flavors/{flavor_id}

  Add a PUT API for updating the flavor ``description`` field. This is useful
  for existing flavors, and for new flavors since one has to add extra specs
  to a flavor after it is initially created, which might affect the ultimate
  description. Also, flavor extra specs could change which might affect the
  scheduling behavior with host aggregates, so in that case the description may
  need to be updated also.

  The ``description`` field will be required in the request and the response.

  .. note:: The only field that can be updated is the ``description`` field.
            Nova has historically intentionally not included an API to update
            a flavor because that would be confusing for instances already
            created with that flavor. Needing to change any other aspect of a
            flavor requires deleting and/or creating a new flavor.

  Request sample::

     {
       "flavor": {
           "description": "Baremetal flavor with 10GB network card."
       }
     }

  Response sample::

     {
       "flavor": {
           "OS-FLV-DISABLED:disabled": false,
           "disk": 10,
           "OS-FLV-EXT-DATA:ephemeral": 0,
           "os-flavor-access:is_public": true,
           "id": "f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
           "links": [
               {
                   "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "self"
               },
               {
                   "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/f68c1474-4ba6-4291-bbdc-2c7865c0f33f",
                   "rel": "bookmark"
               }
           ],
           "name": "2vcpu-1024ram-10disk-baremetal-10gb",
           "description": "Baremetal flavor with 10GB network card.",
           "ram": 1024,
           "swap": "",
           "rxtx_factor": 1.0,
           "vcpus": 2
       }
     }

.. _schema: https://github.com/openstack/nova/blob/16.0.0/nova/api/validation/parameter_types.py#L266

Security impact
---------------

None. Administrators will want to keep any details about a flavor at a high
enough level to abstract low-level details about their deployment or topology
so as to not leak host aggregate details, but this is nothing new.

Notifications impact
--------------------

The ``flavor.create``, ``flavor.update`` and ``flavor.delete`` versioned
notifications will be updated to include the new nullable description field.

Other end user impact
---------------------

The python-novaclient CLI and API bindings will be updated to allow creating,
updating and showing flavor details with a description field.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Matt Riedemann <mriedem.os@gmail.com>

Work Items
----------

* Update API DB schema to add the nullable TEXT description column to
  the flavors table.
* Add a description field to the Flavor versioned object and ensure it is
  not serialized and stored in the ``instance_extras.flavor`` column.
* Add a microversion to the REST API to create, update and show flavors with a
  description.
* CLI and API binding changes to python-novaclient.


Dependencies
============

None


Testing
=======

* Unit tests for negative scenarios:

  * Create a flavor with a description before the new microversion.
  * Create/update a flavor with a description that is too large.
  * Update a flavor without specifying a description.
  * Try to update a flavor description before the new microversion.
  * Create a flavor with a description of length 65535 and use it to create
    an instance and ensure the embedded instance.flavor does not contain the
    description in the ``instance_extras`` table.
  * Create a flavor with a description, create a server with the flavor,
    get the server details out of the API and ensure the flavor description
    is not included in the server response body.

* Functional API samples tests for the new microversion.


Documentation Impact
====================

The compute REST API reference would be updated for the new microversion.

The `flavors admin guide`_ would also be updated.

.. _flavors admin guide: https://docs.openstack.org/nova/latest/admin/flavors.html

References
==========

Queens PTG discussion: https://etherpad.openstack.org/p/nova-ptg-queens


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
