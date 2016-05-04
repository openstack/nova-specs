..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 A
 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
CellsV2 - Keypairs API DB migrations
====================================

https://blueprints.launchpad.net/nova/+spec/cells-keypairs-api-db

Keypair database tables that currently reside in the nova database must be
migrated to the API database. This is because Keypairs are exposed in the API
and must span across cells.

Problem description
===================

The ``key_pairs`` table is currently located in the cell database. As Keypairs
is a concept that is exposed in the API it must be moved to the API database.

Use Cases
---------

As a developer, I need to ensure all data that applies across multiple cell
partitions is stored in the global API database.


Proposed change
===============

A new ``key_pairs`` database model will be created in the API database::

    class KeyPair(API_BASE):
        """Represents a public key pair for ssh / WinRM."""
        __tablename__ = 'key_pairs'
        __table_args__ = (
            schema.UniqueConstraint("user_id", "name",
                                name="uniq_key_pairs0user_id0name"),
        )
        id = Column(Integer, primary_key=True, nullable=False)

        name = Column(String(255), nullable=False)

        user_id = Column(String(255))

        fingerprint = Column(String(255))
        public_key = Column(MediumText())
        type = Column(Enum('ssh', 'x509', name='keypair_types'),
                      nullable=False, server_default='ssh')

The ``KeyPair`` object will be modified to use the new API database model.
Methods related to keypairs that are currently in the database API will be
moved to the ``KeyPair`` object.

Migration to the API database will follow the existing pattern established
by the merged flavor migration series. [1]_

The metadata service currently reads the ``key_pairs`` table directly. We
would like to prevent this once the table has been moved to the API database.
Instead the entire ``KeyPair`` object will be serialized in-to the
``instance_extra`` table. This will require an additional column::

    keypair = orm.deferred(Column(Text))

Database migrations will be performed to include this new column on instance
extra. It will be populated on creation of the instance object if a key pair
is to be inserted. It will be read out from the metadata service.

Alternatives
------------

I do not believe that there is an alternative to putting the Keypairs table
in the API db. Alternatives for passing the keypair information to the
metadata service could be adding a field to the instance object to store
``key_type``. Fields are already present for ``key_name`` and ``key_data``.
This alternative is not preferred as it involves a modification of the
instance object and continues an existing bad practice of duplicating
object fields.

Data model impact
-----------------

There will be a large data model impact as many new tables will be created
in the API database. The data models have been detailed in the above sections.

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

Deployers must be aware that Keypairs data is being migrated on upgrade, but
this should take place during their normal upgrade operations.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <dms@danplanet.com>

Other contributors:
  None

Work Items
----------

* Create new database table and database migration for ``keypairs``.
* Update the ``KeyPair`` object to use the new models.
* Create migration methods for moving data to the API database.
* Modify nova-compute service to use keypair information from instance-extra.

Dependencies
============

None

Testing
=======

* Add required unit tests for database access functions to the API db.
* Add functional testing for migration of keypair data.
* Add new unit tests for access to keypair data in metadata service.

Documentation Impact
====================

None past other documentation for CellsV2. In CellsV2 documentation
there should be a list of migrated tables.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
