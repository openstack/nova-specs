..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
Cells host mapping
==================

https://blueprints.launchpad.net/nova/+spec/cells-host-mapping

Since the scheduler will return a host rather than a cell we need to know which
cell that host is in.  A new table will be created which can store this
mapping.


Problem description
===================

When Nova is partitioned into cells, the compute api needs to know which cell
to communicate with in order to build a scheduled instance, or for host API
requests.  There is currently no mapping of host to cell so given just a host
there is no way to know how to pass information to that host.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need a lookup table to
  know which partition a host is in.

Project Priority
-----------------

Priorities have not been decided for Liberty.


Proposed change
===============

The change being proposed is a new table in the 'nova_api' database for storing
a mapping of host to cell and an object to interact with it.  Migration of data
into this table will be tackled in a separate spec.

The following diagram may help visualize it.::

                                  api/cell boundary
     scheduler returns a host             |
                 |                        |
                 v                        |
            nova-api+--------------------------->cell-db/rpc
                 +                        |
                 +----+                   |
                      |                   |
                      v                   |
 host_mapping (joined with) cell_mapping  |



Alternatives
------------

We could continue to use the nova-cells model in place today.

Data model impact
-----------------

A new 'host_mapping' table will be added to the 'nova_api' database.

The table will look like:::

    CREATE TABLE `host_mapping` (
      `created_at` datetime DEFAULT NULL,
      `updated_at` datetime DEFAULT NULL,
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `host` varchar(255) NOT NULL,
      `cell_uuid` varchar(36) NOT NULL)

And host will be an indexed column.  Other indexes are possible as well
and can be discussed in the code review.

It should be noted that there is no 'deleted' or 'deleted_at' column here.  If
a host exists it should be mapped, it should only be deleted if the host is
being permanently removed in which case there is no reason to keep it here.

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
by later specs it does introduce another database lookup for some actions
within Nova.

Other deployer impact
---------------------

This introduces a new table into the 'nova_api' database.  And as described in
the "Data model impact" section above it should be considered when running any
cleanup of hosts.  If hosts are removed from a deployment they can be removed
from the host_mapping table as well.

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

  * Add database migration for 'host_mapping' table.

  * Add HostMapping object.


Dependencies
============

None


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
