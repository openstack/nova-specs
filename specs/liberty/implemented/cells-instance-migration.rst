..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Cells instance migration
========================

https://blueprints.launchpad.net/nova/+spec/cells-instance-migration

Now that there's a table to map instances to cells it needs to be populated
with data on instances that existed prior to its creation and usage.


Problem description
===================

When Nova is partitioned into cells the compute api needs to know which cell to
communicate with for a particular instance.  Instances that existed before this
mapping was maintained need to have their location added to the table.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need a lookup table to
  know which partition an instance is in.  That lookup table needs to be
  populated with information on instances that existed prior to its creation.

Project Priority
-----------------

Cells v2 is a priority for Liberty.


Proposed change
===============

The 'instance_mapping' table will be populated with data on which cell an
instance lives in.

A new nova-manage command will be added to look up instances in a database and
add an instance_mapping row for them.  The command will take a cell name/uuid
as an argument and migrate instances within that cell.  The cell name/uuid must
correspond to an entry in the cell_mapping table and the database connection
information in that row will be used for finding instances to be mapped.

For cells v1 setups where there are multiple cells a new cell_mapping entry
should be added for each cell and then the nova-manage command would need to be
run for each cell.


Alternatives
------------

The alternatives to cells v1/v2 have been discussed prior to this spec.  In the
cells v2 effort there is no alternative for this mapping requirement.

Data model impact
-----------------

None

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

Deployers will be provided with a new nova-manage command to trigger the
creation of the mappings.  This should be run once for a deployment not
currently using cellsv1, and once in each cell for a deployment currently using
cellsv1.  This command will need to be run for each cell, or to migrate the
first cell for current non cellsv1 users, before the current hardcoded database
connection method can be dropped.  The timeline for that is likely to be at the
end of a release cycle, either Liberty or M(ongoose).

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alaski

Other contributors:
  None

Work Items
----------

* Add nova-manage command to populate instance_mapping data for instances.  The
  command should migrate one cell at a time.

* Update grenade testing job, or add a new one, to call the new command and
  verify that migration works properly.



Dependencies
============

https://blueprints.launchpad.net/nova/+spec/cells-instance-mapping


Testing
=======

Testing will be a combination of Nova in-tree functional tests and a grenade
test to verify that upgrades work.


Documentation Impact
====================

Documentation on the new nova-manage command will need to be written.


References
==========

``https://etherpad.openstack.org/p/YVR-nova-cells-v2``
