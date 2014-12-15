..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Cells v2 mapping
==========================================

https://blueprints.launchpad.net/nova/+spec/cells-v2-mapping

In order for compute api nodes to communicate with cells they will need to have
knowledge on how to connect to each cell.  A new database and table will be
created which can store this information for use by the database and RPC layers
of Nova.


Problem description
===================

When Nova is partitioned into cells, the compute api needs to be able to
communicate with each one via a message bus and a database connection.  There
is currently no mapping of a cell identifier to a message queue and database
connection.  And there is no mechanism to dispatch RPC message or database
queries to different endpoints on a per call basis.

Use Cases
----------

* Developers who want to make database queries or send RPC messages to a
  specific cell.


Project Priority
-----------------

Cells v2 has been made a project priority for Kilo.


Proposed change
===============

The change being proposed is a new database and table for storing a mapping of
cell to database and message queue.  A new database is being proposed because
the new tables that will be added to it belong with the compute api layer of
Nova, as compared to some of the current tables which belong in a cells
database.  The exact split of which information belongs where is an in-progress
effort.

The new database will require a separate line of migrations to be applied to
it.  Since there have been discussions for a while now around potential
benefits of using alembic to handle db migrations this might be a good
opportunity to do so.  I think it should be researched and used if there's
consensus that it would be beneficial and continue to use sqlaclhemy-migrate if
not.

Nova will need a connection string to connect to this new database and at the
same time continue to connect to the current 'nova' database until we can fully
migrate away from that.  A new config option will be introduced to store the
connection info for the 'nova_api' database.

Additionally the database and rpc abstractions in Nova need to be capable of
communicating with an arbitrary endpoint for every call/query.

There is nothing in place to use this yet so the scope of work ends at just
having the capability to do it.

The following diagram may help visualize it.  When a request comes in for an
instance in a cell nova-api will query the cell_mapping table to get the
necessary information for interacting with the cell database or message queue.
The instance to cell mapping is described in another spec.::

              api/cell boundary
                    |
                    |
            +------------>cell-db
            |       |
        nova-api+--------->cell-mq
            +       |
            |       |
            |       |
            v       |
    cell_mapping    |


Alternatives
------------

We could continue to use the nova-cells model in place today.

Data model impact
-----------------

A new 'cell_mapping' table will be added.  And it will be added outside of the
current 'nova' database in a new 'nova_api' database.  This new database will
have deployment ramifications as described below

The table will look like:::

  CREATE TABLE `cell_mapping` (
    `created_at` datetime DEFAULT NULL,
    `updated_at` datetime DEFAULT NULL,
    `deleted_at` datetime DEFAULT NULL,
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uuid` varchar(36) NOT NULL,
    `name` varchar(255) DEFAULT NULL,
    `deleted` int(11) DEFAULT NULL,
    `transport_url` mediumtext NOT NULL,
    `database_connection` mediumtext NOT NULL)

REST API impact
---------------

None

Security impact
---------------

The transport_url and database_connection fields in the database could contain
sensitive data.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

On its own this change does not introduce a performance impact.  When it is
used by later specs it does introduce another database lookup for many actions
within Nova.  For example a 'nova show <uuid>' will require Nova to look up the
database that an instance is in before it can query it for instance data.  This
data will remain relatively stable and could be cached quite easily to help
offset any performance penalty.

Other deployer impact
---------------------

This blueprint introduces the concept of a database that is conceptually
distinct from the current nova database.  Deployers will need to consider how
they want to manage a second database, whether it resides on the same host as
their current nova database or not.  It will be used primarily by the nova-api
service so that should be considered when considering how to deploy it.

Developer impact
----------------

This change means that developers should understand that RPC messages or
database queries may hit one of many endpoints.  At this point it should not
affect developers work within Nova.  Developers adding future database
migrations will need to consider whether it goes at the API or cell level and
add it to the appropriate set of migrations.


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

* Ensure Nova database API can communicate with an arbitrary database on each
  call.

* Add config option for connecting to the new database.

* Research how to have a separate migration path within Nova for a new
  database.

* Setup separate database migration path for migrations on a new database.

* Add database migration for 'cell_mapping' table.


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

The existence and management of a new database will need to be documented.  It
is not required that the database be deployed at this time but deployers should
be prepped on how to start managing it.


References
==========

``https://etherpad.openstack.org/p/kilo-nova-cells``
