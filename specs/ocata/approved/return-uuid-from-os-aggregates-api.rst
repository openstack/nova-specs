..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Return uuid from os-aggregates API
==================================

`<https://blueprints.launchpad.net/nova/+spec/return-uuid-from-os-aggregates-api>`_

This spec proposes that the os-aggregates REST API returns the aggregate UUID
in a new microversion so that the aggregate UUID can be used to associate an
aggregate with resource providers in the Placement service.

Problem description
===================

In Mitaka we started auto-generating UUIDs for aggregates and in Ocata the
Placement API allows associating aggregates to resource providers via the
aggregate UUID. However, the os-aggregates REST API does not yet return the
UUID for a given aggregate so administrators cannot make the association in
the Placement API without doing direct queries in the Nova API DB. This change
proposes that the os-aggregates REST API returns the aggregate UUID in a new
microversion.

Use Cases
---------

As an operator, I want to associate an aggregate of compute hosts to a shared
storage pool (modeled as a resource provider in the Placement service) so that
those compute hosts reported disk inventory and allocation comes from the
shared storage pool and not local disk.

As an operator, I want to associate an aggregate of compute hosts to a subnet
IP allocation pool (modeled as a resource provider in the Placement service) so
that when creating servers with Neutron ports in that pool the servers are
placed on those specific compute hosts.

Proposed change
===============

The proposed change is relatively simple, we just need to expose the aggregate
UUID in responses from the os-aggregates REST API in a new microversion.

Alternatives
------------

Operators could query the database directly for aggregate UUIDs but this is a
workaround at best and not an ideal long-term solution from a usability
standpoint.

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion, return the aggregate UUID field in all responses from
the os-aggregates REST API which return a full representation of an aggregate
resource today. These would be every method except for DELETE.

An example GET response with the uuid returned::

   {
       "aggregate": {
           "availability_zone": "nova",
           "created_at": "2016-12-27T23:47:30.563527",
           "deleted": false,
           "deleted_at": null,
           "hosts": [],
           "id": 1,
           "metadata": {
               "availability_zone": "nova"
           },
           "name": "name",
           "updated_at": null,
           "uuid": "fd0a5b12-7e8d-469d-bfd5-64a6823e7407"
       }
   }

Security impact
---------------

None

Notifications impact
--------------------

None

.. note:: We currently do not have versioned notifications for operations on
   aggregate resources, but when we do we should include the Aggregate.uuid
   field in those versioned notifications.

Other end user impact
---------------------

As part of this effort we will also need to add the microversion support to
python-novaclient so that when getting details about aggregates we also show
the UUID.

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
  Jay Pipes <jaypipes@gmail.com>

Other contributors:
  Matt Riedemann <mriedem@us.ibm.com>

Work Items
----------

* Add a new microversion to the os-aggregates REST API such that the UUID field
  is returned in responses which show the full aggregate representation.
* Support the new microversion in python-novaclient when showing aggregate
  details.


Dependencies
============

None. The majority of the groundwork for this was completed in the
`Generic Resource Pools`_ blueprint.

.. _Generic Resource Pools: https://blueprints.launchpad.net/nova/+spec/generic-resource-pools


Testing
=======

* Tests will be added to Tempest for testing the new microversion and
  validating the response schema.
* Unit tests and functional tests will be added to Nova for testing the new
  microversion.


Documentation Impact
====================

The in-tree API reference will be updated for the os-aggregates REST API
documentation.

References
==========

* Change which added the Aggregates.uuid field in Mitaka: https://review.openstack.org/#/c/282520/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
