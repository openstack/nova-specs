..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add Aggregate tables to the API Database
==========================================

https://blueprints.launchpad.net/nova/+spec/cells-aggregate-api-db

CellsV2 needs aggregate information to span cells. This is because
aggregates can be a global concept that may apply to compute nodes in multiple
cells.

Problem description
===================

Aggregates may be applied to compute nodes in multiple cells and are a global
concept.

Currently aggregates are stored in the cell database but to keep their global
nature they must be migrated to the API database [1]_.

Use Cases
---------

 * Operators wish to apply the same host aggregate to compute nodes in
   multiple cells.

Proposed change
===============

With this spec we propose to create new aggregate tables in the API database.

The tables to be created are::

* aggregate_hosts
* aggregate_metadata
* aggregates

The following objects will be modified to interact with the API database
tables::

* Aggregate
* AggregateList

Methods currently located in the db/sqlachemy/api.py will be moved to the
``Aggregate`` and ``AggregateList`` objects. This is following the established
pattern that there will be no single 'api' file for api database methods.

These methods will be modified to access the API database first and fall-back
to the cell database. Migration methods will be added that will migrate
aggregates from the cell to API database. These methods will be added to
the nova manage ``online_data_migrations`` command.

The ``Flavor`` tables have already been migrated to the API db. In general
the proposed changes will follow those methods. [2]_

Alternatives
------------

It would be possible to leave all aggregate tables within the cells. This
would mean data duplication as operators would have to create identical
aggregates for each cell.

It would also be possible to leave just the ``aggregate_hosts`` table within
the cell database as it pertains to hosts that are located within the cells.

In this case the following ``aggregate_hosts`` functions would be modified::

    aggregate_host_add
    aggregate_host_delete

These methods are accessed by the api service and the conductor. As they take
a host argument, it should be trivial to decide upon a cell for these
functions to operate on by looking up the cell for the host using the
``HostMapping`` object.

The ``AggregateList.get_all`` method accesses the ``aggregate_hosts`` table.
It will need to be modified to look at the ``aggregate_host`` values obtained
from all cells.

In this case there might be a negative performance impact due to the fact that
``AggregateList.get_all`` method will now have to perform a database query
per cell to obtain the aggregate host mapping information. Currently this
method is called within the scheduler to initialise or re-populate the
HostState objects.

Data model impact
-----------------

The data model impact is extensive as aggregate tables will be created in the
API database.

The proposed table models are::

    class AggregateHost(API_BASE):
        """Represents a host that is member of an aggregate."""
        __tablename__ = 'aggregate_hosts'
        __table_args__ = (schema.UniqueConstraint(
            "host", "aggregate_id",
             name="uniq_aggregate_hosts0host0aggregate_id"
            ),
        )
        id = Column(Integer, primary_key=True, autoincrement=True)
        host = Column(String(255))
        aggregate_id = Column(Integer, ForeignKey('aggregates.id'),
                              nullable=False)

    class AggregateMetadata(API_BASE):
        """Represents a metadata key/value pair for an aggregate."""
        __tablename__ = 'aggregate_metadata'
        __table_args__ = (
            schema.UniqueConstraint("aggregate_id", "key",
                name="uniq_aggregate_metadata0aggregate_id0key"
                ),
            Index('aggregate_metadata_key_idx', 'key'),
        )
        id = Column(Integer, primary_key=True)
        key = Column(String(255), nullable=False)
        value = Column(String(255), nullable=False)
        aggregate_id = Column(Integer, ForeignKey('aggregates.id'),
                              nullable=False)

    class Aggregate(API_BASE):
        """Represents a cluster of hosts that exists in this zone."""
        __tablename__ = 'aggregates'
        __table_args__ = (
            Index('aggregate_uuid_idx', 'uuid'),
            schema.UniqueConstraint("uuid",
                name="uniq_aggregate0aggregate_uuid"
                ),
        )
        id = Column(Integer, primary_key=True, autoincrement=True)
        uuid = Column(String(36))
        name = Column(String(255))

        hosts = orm.relationship(AggregateHost,
                              primaryjoin=(
                              'Aggregate.id == AggregateHost.aggregate_id')

        metadata = orm.relationship(AggregateMetadata,
                            primaryjoin=(
                            'Aggregate.id == AggregateMetadata.aggregate_id')

As use of soft-delete is deprecated the soft-delete mixin will not be applied
to these schemas. Otherwise they are the same as currently found in the
nova database.

Despite many changes to existing objects, no new objects are proposed.


REST API impact
---------------

There is no API impact. External aggregate behavior should be unmodified.

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

Performance impact should be minimal to none in current deployments.

As CellsV2 is intended to improve performance for very large scale deployments
it is also worth considering whether this design meets those demands. As the
number of hosts grows the ``aggregate_hosts`` table will grow with them.
However we believe that this is manageable as the row size for this table
is very small. Even in extremely large deployments indexed queries over hosts
in this table should be capable of being performant. Through the unique
constraint, the table will maintain an index over all the columns queried on
for aggregate hosts.

Other deployer impact
---------------------

As well as online data migration deployers will have the option to perform
a one time migration of aggregate data from the nova database to the
api database. Deployers must be made aware of this option and its impact.

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

* Create the ``aggregate``, ``aggregate_hosts`` and ``aggregate_metadata``
  database models in the api database.
* Database schema update and migration to remove foreign key link in
  the ``aggregate_hosts`` table to the aggregate id.
* Create new test fixtures that simulate multiple cell databases.
* Modify the Aggregate and AggregateList objects to use api database.

Dependencies
============

None

Testing
=======

* Functional tests for the Aggregate object will be added where missing.

* New functional tests will be created for data migration to API DB.

* New test fixtures will be provided that set up multiple cell databases and
  cell mappings.

* Unit testing will be provided for database access methods and object access
  methods. These will make use of the new test fixtures.

Documentation Impact
====================

No documentation impact of this change specifically. Cells documentation
will cover any changes in this specification.

References
==========

.. [1] http://eavesdrop.openstack.org/meetings/nova_cells/2016/nova_cells.2016-03-02-17.00.log.html
.. [2] https://blueprints.launchpad.net/nova/+spec/flavor-cell-api

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
