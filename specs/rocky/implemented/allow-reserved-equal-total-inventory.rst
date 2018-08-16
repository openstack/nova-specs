..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
Allow having placement inventories with reserved value equal to total
=====================================================================

https://blueprints.launchpad.net/nova/+spec/allow-reserved-equal-total-inventory

Currently, we delete ironic node resource provider inventory from placement
to indicate that the node is not available for deployment during the cleaning
process or when in maintenance. This causes placement to report the incorrect
inventory and capacity information, as the node is actually still present, and
its inventory remains the same. Reserving all the inventory describes more
accurately what is going on. Also doing the resource reservation will allow
us to fix bugs like [1] properly, as it is possible to set reservation for
inventory before deleting the allocation, even if inventory gets exceeded
because of that. But placement API does not allow to set reserved value to be
equal to total in the inventory record.


Problem description
===================

Placement API does not allow to set reserved value to be equal to total in the
inventory record. This makes ironic virt driver to delete inventory records
from placement e.g. during node cleaning instead of reserving them.

Deleting resource provider inventory should mean that it is actually gone.
For purposes of indicating that resources are temporarily unavailable
placement provides the ``reserved`` field in the inventory object. This will
enable placement to report the correct inventory and capacity information.
It will also enable us to fix ironic virt driver issue [1].

Use Cases
---------

1. Reserve ironic node inventory during node cleaning or maintenance.

2. Reserve FPGA inventory during its programming by cyborg.


Proposed change
===============

Add a new microversion to placement API that will allow to set reserved value
of the inventory record to be equal to total value. It will become the
placement behaviour for all subsequent microversion.

This new microversion will be used by nova scheduler report client when
doing the inventory update calls. This will enable virt drivers in nova
to decide whether they need to report all the inventory resources as reserved
in the ``get_inventory()`` call.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

``POST /resource_providers/<UUID>/inventories``,
``PUT /resource_providers/<UUID>/inventories`` and
``PUT /resource_providers/<UUID>/inventories/<RC>`` API endpoints will return
response code ``200`` instead of ``400`` when called with
new microversion and body containing inventory records that have reserved
value equal to total.

Example request:

path -- ``PUT /resource_providers/UUID/inventories``

headers -- ``Content-type: application/json``,
           ``Openstack-API-Version: placement 1.NEW_MV``

body::

    {
        "inventories": {
            "CUSTOM_GOLD": {
                "total": 1,
                "reserved": 1
            }
        },
        "resource_provider_generation": 5
    }

Example response:

``200 OK``

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

Virt drivers now are able to set the ``reserved`` key in the
``get_inventory()`` returned dictionary to a total inventory value when needed.

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vdrok

Work Items
----------

* change to placement API adding the logic and new microversion

* change scheduler report client to use the new microversion during inventory
  update calls

* change ironic virt driver to report resources as reserved during cleaning
  and maintenance


Dependencies
============

None


Testing
=======

Unit and functional testing will be added.


Documentation Impact
====================

API reference will be updated.


References
==========

[0] https://etherpad.openstack.org/p/nova-ptg-Rocky

[1] https://bugs.launchpad.net/nova/+bug/1771577


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
