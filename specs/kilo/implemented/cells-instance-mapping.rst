..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Cells instance mapping
==========================================

https://blueprints.launchpad.net/nova/+spec/cells-instance-mapping

In order for compute api nodes to communicate with the correct cell for an
instance there will need to be a mapping of instance to cell.  A new table will
be created which can store this mapping.


Problem description
===================

When Nova is partitioned into cells, the compute api needs to know which cell
to communicate with for a particular instance.  There is currently no mapping
of instance to cell in which it lives.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need a lookup table to
  know which partition an instance is in.

Project Priority
-----------------

Cells v2 has been made a project priority for Kilo.


Proposed change
===============

The change being proposed is a new table in the 'nova_api' database for storing
a mapping of instance to cell.  The database APIs and objects that interact
with this table will be updated to use it.  Migration of data into this table
will be tackled in a separate spec.

The following diagram may help visualize it.::

                             api/cell boundary
     nova show <uuid>               |
                 |                  |
                 v                  |
            nova-api+-------------------->cell-db
             +     +                |
             |     +----+           |
             |          |           |
             v          v           |
    instance_mapping  cell_mapping  |


Alternatives
------------

We could continue to use the nova-cells model in place today.

Data model impact
-----------------

A new 'instance_mapping' table will be added to the 'nova_api' database.

The table will look like:::

    CREATE TABLE `instance_mapping` (
      `created_at` datetime DEFAULT NULL,
      `updated_at` datetime DEFAULT NULL,
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `instance_uuid` varchar(36) NOT NULL,
      `cell_uuid` varchar(36) NOT NULL,
      `project_id` varchar(255) NOT NULL)

And instance_uuid will be an indexed column.  Other indexes are likely as well
and can be discussed in the code review.

It should be noted that there is no 'deleted' or 'deleted_at' column here.
This mapping is still valid even if the instance is deleted, so there is no
requirement to delete the mapping.  A listing of deleted instances, for
example, will still need to know which cell those instances are in.

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

On its own this change does not introduce a performance impact.  When it's used
by later specs it does introduce another database lookup for many actions
within Nova.  For example a 'nova show <uuid>' will require Nova to look up the
database that an instance is in before it can query it for instance data.  This
can be optimized later with a memcached cache of this mapping.

Other deployer impact
---------------------

This introduces a new table into the 'nova_api' database.  And as described in
the "Data model impact" section above it should be considered when running any
cleanup on the instances table.  If instances are removed from the instances
table they can be removed from the instance_mapping table as well.

Developer impact
----------------

Developers should be beginning to see that all instances in a deployment may
not be in the same database.  But no development changes should necessary at
this point.


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

* Add database migration for 'instance_mapping' table.


Dependencies
============

https://blueprints.launchpad.net/nova/+spec/cells-v2-mapping


Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice.  At some point we will want to look at how to test multiple cells or
potentially exposing the concept of a cell in the API and we will tackle
testing requirements then.


Documentation Impact
====================

Documentation should be added about the new table and what its usage will be.


References
==========

``https://etherpad.openstack.org/p/kilo-nova-cells``
``https://review.openstack.org/#/c/139191/``
