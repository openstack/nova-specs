..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Add Flavor tables to API Database
=====================================

https://blueprints.launchpad.net/nova/+spec/flavor-cell-api

CellsV2 need to store flavor information for booting instances. Since this
information will live at the cell API, tables related to flavors need to be
created in API DB.

Problem description
===================

Flavors are virtual hardware templates, which are used by nova, for example,
when creating a new instance.
In CellsV1, flavors are stored in parent and child cells. Considerable manual
effort is required to keep this information consistent across all the cells.

Flavors are a global concept that should be stored only in one database.
Therefore, flavor related tables for CellsV2 would be created only in the API
database.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling,
  failure domain, and buildout reasons. When partitioned, flavor
  information needs to be stored at API level.


Proposed change
===============

With this spec we propose to create all flavor related tables in the API DB.
They are::

   * instance_types
   * instance_type_extra_specs
   * instance_type_projects

The name of the tables will be changed to flavors, flavor_extra_specs and
flavor_projects respectively but the table schema will remain unchanged.

The flavor object will be modified to interact with the tables in the API
database. The create() and save() method will be updated to use the API DB
tables.

The get_by_*() methods will be modified to query the API DB and if a flavor
is not found, query the nova DB as well. The get_all() method will be modified
so that it displays all the flavors, which will be a union of what exists in
API DB and nova DB. It will query the API DB and then query the nova DB to
get the flavors not yet present in API DB.

The destroy() method will remove flavors from both the databases. This will
ensure that all flavor related operations are done on the new table and older
flavors are also actively migrated to the new table as they are used. The
existing flavor tables in nova will continue to remain but no longer accessed
and can be removed in subsequent releases.

During the transition phase, databases corresponding to both cellV1 and V2
will co-exist and tests will be written to make sure that the flavor tables
in CellsV2 have the same model as in CellV1. Any change in the tables should
be applied in both databases.

To migrate existing flavor data to the proposed cellsV2 tables a new
"nova-manage" command will be added.

This command will copy flavor entries from top-level cell DB to the new API DB.
It will take no parameters and on execution read the data from flavor tables
(instance_types, instance_type_extra_specs and instance_type_projects) and put
it into the corresponsing tables in API DB if it doesn't already exist.

Alternatives
------------

We could continue storing flavor at both api and cell level or store flavors
only at compute cell level. Both these approaches introduce addtional
complexity in flavor management.

Data model impact
-----------------

Three new tables will be created in 'nova_api' database as follows. The
corresponding schemas are detailed below,

* 'flavors':::
    CREATE TABLE `flavors` (
        `created_at` datetime DEFAULT NULL,
        `updated_at` datetime DEFAULT NULL,
        `deleted_at` datetime DEFAULT NULL,
        `name` varchar(255) DEFAULT NULL,
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `memory_mb` int(11) NOT NULL,
        `vcpus` int(11) NOT NULL,
        `swap` int(11) NOT NULL,
        `vcpu_weight` int(11) DEFAULT NULL,
        `flavorid` varchar(255) DEFAULT NULL,
        `rxtx_factor` float DEFAULT NULL,
        `root_gb` int(11) DEFAULT NULL,
        `ephemeral_gb` int(11) DEFAULT NULL,
        `disabled` tinyint(1) DEFAULT NULL,
        `is_public` tinyint(1) DEFAULT NULL,
        `deleted` int(11) DEFAULT NULL)

    This table will have unique constraints on (name, deleted) and (flavorid,
    deleted) attributes

* 'flavors_extra_specs':::

    CREATE TABLE `flavor_extra_specs` (
        `created_at` datetime DEFAULT NULL,
        `updated_at` datetime DEFAULT NULL,
        `deleted_at` datetime DEFAULT NULL,
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `flavor_id` int(11) NOT NULL,
        `key` varchar(255) DEFAULT NULL,
        `value` varchar(255) DEFAULT NULL,
        `deleted` int(11) DEFAULT NULL)

    This table will have a unique constraint on (flavor_id, key,
    deleted) attribute and an index on (flavor_id, key)

* 'flavor_projects':::

    CREATE TABLE `flavor_projects` (
        `created_at` datetime DEFAULT NULL,
        `updated_at` datetime DEFAULT NULL,
        `deleted_at` datetime DEFAULT NULL,
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `flavor_id` int(11) NOT NULL,
        `project_id` varchar(255) DEFAULT NULL,
        `deleted` int(11) DEFAULT NULL)

    This table will have a unique constraint on (flavor_id, project_id,
    deleted) attribute

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

Deployers will be provided with a new nova-manage command to migrate the
flavors to the cellsV2 DB API proposed tables. This command will need to be
run once for any existing deployments (cell or non-cell).

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mvineetmenon

Other contributors:
  None

Work Items
----------

* Create new database tables 'flavors', 'flavor_extra_specs'
  and 'flavor_projects' in API DB.

* Modify the flavor object to interact with API DB

* Create a new command in nova-manage for migrating flavors from cellsV1 to
  cellsV2

Dependencies
============

None

Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice.

Also, tests need to be written to ensure that the data model doesn't change
from what is being used in the cellsV1 model.

These tests should be kept until the final migration to cellsV2.

Documentation Impact
====================

Document the `nova-manage` command to migrate flavors from top-level cell DB to
cellsV2 API-DB.

References
==========

``https://etherpad.openstack.org/p/kilo-nova-cells``

History
=======

None
