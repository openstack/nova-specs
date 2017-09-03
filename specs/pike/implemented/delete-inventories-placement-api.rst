..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
DELETE all inventories for a resource provider
==============================================

https://blueprints.launchpad.net/nova/+spec/delete-inventories-placement-api

This is a small feature request: Implement the DELETE method for all
inventories for a resource provider. It is possible to delete a single
inventory at a time, but there is no way to DELETE all inventories at once.

Problem description
===================

Currently (version 1.4 or before of the placement API), in order to delete
all inventory for a resource provider, one must call
PUT /resource_providers/{uuid}/inventories and pass in the following request
payload::

    {
      'generation': <int>,
      'resources': {}
    }

It would be easier and more intuitive to support
DELETE /resource_providers/{uuid}/inventories with no request payload and
returning a 204 No Content on success.

The existing method for deleting a single inventory is referenced below::

    'DELETE': inventory.delete_inventory

https://github.com/openstack/nova/blob/15.0.0/nova/api/openstack/placement/handler.py#L88

Use Cases
---------

As an operator or developer, I want to delete all inventories for a resource
provider with the DELETE method using the placement api.

Proposed change
===============

Add DELETE /resource_providers/{uuid}/inventories and return 204 no content
on success. Changes include:

* /nova/api/openstack/placement/handlers/inventory.py, delete_inventories(req)
* A release note advertising the additional placement REST API microversion
  and functionality

The handler file for inventory.py should just take a call to
DELETE /resource_providers/{uuid}/inventories and construct a call to
ResourceProvider.set_inventory(), passing in an empty InventoryList() object.

We still want the DELETE /resource_providers/{uuid}/inventories call to return
a 409 if the inventory is in use or if there was a concurrent attempt to
update the inventory.
Thus, reuse nova.objects.ResourceProvider.set_inventory() as much as possible.

There's no need to modify anything in the nova/objects/resource_provider.py.

Alternatives
------------

* Continue non-intuitive delete of all inventory through the PUT method with
  empty resources in the request payload.
* The other alternative is to get all inventories from a resource provider and
  use the DELETE method one at a time.

These methods are ugly and require a new microversion with a new method for
deleting all inventories from a resource provider at once, which should report
the appropriate return codes.

Data model impact
-----------------

None

REST API impact
---------------

New API method: ``DELETE /resource_providers/{uuid}/inventories``

Empty request payload.

Return 204 `No Content` on success.

Return 409 `Conflict` on the following errors:

* resource generation out of sync
* inventory in use

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

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

  Rafael Folco <rfolco@br.ibm.com>

Other contributors:

  Jay Pipes <jaypipes@gmail.com>

  Chris Dent <cdent@anticdent.org>

Work Items
----------

* Add a Reno with the REST API change
* Add a new DELETE method to /resource_providers/{uuid}/inventories
* Support the new DELETE method

Dependencies
============

None. The majority of the groundwork for this was completed in the
`Generic Resource Pools`_ blueprint.

.. _Generic Resource Pools: https://blueprints.launchpad.net/nova/+spec/generic-resource-pools

Testing
=======

New API test(s) with the DELETE method will be added to
nova/tests/functional/api/openstack/placement/gabbits/inventory.yaml.

Documentation Impact
====================

The in-tree API reference will be updated for the placement REST API
documentation.

References
==========

https://bugs.launchpad.net/nova/+bug/1653122

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
