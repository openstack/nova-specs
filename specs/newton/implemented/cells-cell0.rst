..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
Add a CellZero
==============

https://blueprints.launchpad.net/nova/+spec/cells-cell0

In order to maintain the API contract when using cells we need to store enough
information to fulfill an instance show request even when the instance could
not be scheduled to a cell.


Problem description
===================

When an API request is made to build an instance there is a certain response
contract that we need to honor.  This means that we need to have stored certain
information from the request such as image, flavor, name, uuid, etc...  Under
ideal circumstances the instance will have been scheduled to a host in a cell
and the data will be in that cells database.  In the event that no cell/host
can hold the instance that data needs to be stored outside of any live cells.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need to maintain the
  current API contract.


Proposed change
===============

A cell0 will be added which consists of the database tables needed by an
instance within a live cell.  Instances, and necessary relations, can be stored
here and included in API responses.  The only available action for instances
within this cell will be to delete them as they are in an error state.
Instances that are stored here will have a regular instance_mapping set so that
requests for those instances can follow the normal code path.

The boot process for instances will be updated to create instances in cell0
when the scheduler fails to pick a location for the instance.

Alternatives
------------

An alternative would be to store the instance records, and relations, within
the nova api database in a serialized format for easy retrieval for API
responses.  This was dismissed because it would require multiple upgrade paths
when making changes to the instance table schema or related schemas.

Another alternative would be to maintain an instance table and related tables
in the nova api database.  This is very similar to what's being proposed
however having a cell0 construct is beneficial to avoid special casing
lookups/deletes for instances here.  They will have a normal instance_mapping
set so operations will find them normally.

Data model impact
-----------------

All database tables necessary for storing an instance and related objects, like
security_groups or instance_extra, will be created and managed for this new
cell.  For now it would be best to just deploy a normal cell database for cell0
though it will contain unnecessary tables such as compute_nodes.  Later work
can trim this down if it's deemed worthwhile.


REST API impact
---------------

None

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

Instances that were not schedulable will exist in this special cell.
Deployers will need to be aware of this to aid proper debugging.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  doffm

Other contributors:
  None

Work Items
----------

 * Devstack changes to setup a cell0.

 * Add logic to create instances in cell0 when they can not be scheduled.

 * Document deployment instructions for cell0.

Dependencies
============

 * Spec to call the scheduler earlier in the boot process
   https://review.openstack.org/#/c/239995/


Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice.  At some point we will want to look at how to test multiple cells or
potentially exposing the concept of a cell in the API and we will tackle
testing requirements then.


Documentation Impact
====================

Documentation will be written describing the flow of an instance build and how
this affects it.


References
==========


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced but no changes merged.
   * - Newton
     - Re-proposed.
