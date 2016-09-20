..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
CellsV2 - Instance Groups API DB migrations
===========================================

https://blueprints.launchpad.net/nova/+spec/cells-instance-groups-api-db

Instance group tables that currently reside in the cell database must be
migrated to the API database. Instance groups are exposed in the API and
generally accessed in the scheduler.

Problem description
===================

Use Cases
---------

Users wish to create instance groups that operate globally across deployments
without worrying about cells implementation.

Proposed change
===============

New ``instance_groups`` and ``instance_group_policy`` and
``instance_group_member`` tables will be created in the API database. The
models for these will closely match the existing models in the nova database
but they will no longer have soft delete.

Methods currently located in ``db/sqalchemy/api.py`` will be mirrored in
``objects/instance_group.py`` and modified to access the API database. The
``InstanceGroup`` and ``InstanceGroupList`` objects will be modified to
access the API database initially and the fall-back to the cell database
if neccessary. ``InstanceGroupList`` methods will return items from both
the cell and API databases. These methods will, if-neccessary remove duplicates
from the returned items.

Migration methods will be created to move data from the cell to API database.
These migration methods will be added to the ``online_data_migrations``
nova manage command.

The ``Flavor`` tables have already been migrated to the API db. In general
the proposed changes will follow those methods. [1]_

Alternatives
------------

It may be possible to leave the ``instance_group_member`` table in the
cell database as this table will grow with the number of instances.

The ``InstanceGroup`` function ``get_hosts`` accesses the
``instance_group_member`` table. It is used in both the scheduler and the
compute manager for affinity. As this table is generally accessed outside
of the cells it is likely that there would be a greater performance hit
from placing this in the cell database.

Data model impact
-----------------

There will be a large data model impact as many new tables will be created
in the API database. The data models have been omitted as they are essentially
unchanged from those currently in the cell database.

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

Deployers must be aware of the ``nova-manage`` command that will perform
one time data migration for the tables mentioned.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <mjdoffma@us.ibm.com>

Other contributors:
  None

Work Items
----------

* Create a new database table and database migration for ``instance_groups``
  , ``instance_group_policy`` and ``instance_group_members``.
* Modify functions in ``InstanceGroup`` and ``InstanceGroupList`` to
  access the API database.
* Create migration functions for the affected tables and add these to
  ``online_data_migrations`` command.

Dependencies
============

None

Testing
=======

* Unit tests for API database access functions.
* Functional tests for data migration of instance group tables.

Documentation Impact
====================

Documentation must mention the one time data migration tool in
the ``nova-manage`` command and the data that is migrated.

References
==========

.. [1] https://blueprints.launchpad.net/nova/+spec/flavor-cell-api

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
