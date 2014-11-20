..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Validate database migrations and model
======================================

https://blueprints.launchpad.net/nova/+spec/validate-migrations-and-model

Database migrations and the database model are managed independently in
Nova. When a new database migration is added, changes are often needed
to the database model and vice versa. However, there are no tests or
checks that the database model matches the results of the database
migrations leaving them to often drift apart.


Problem description
===================

* Database migrations affect the correctness of the database model.

* No tests or checks exist to ensure the database model matches the results
  of the database migrations.


Use Cases
---------

Providing a consistent database model to implement the online-schema-changes
spec.

Helping operators determine when local changes to their running schema
differs from the Nova model.


Project Priority
----------------
This is a dependency for another spec that fits under the 'Live Upgrades'
kilo priorities.


Proposed change
===============

A new unit test would be added that uses alembic to compare the result
of the database migrations wit the database model defined in
nova/db/sqlalchemy/models.py.

A new 'db compare' command to nova-manage would allow an operator
to list the differences between their running database and the database
model defined in nova.


Alternatives
------------

Using the database model as a single source for all schema changes. This
would avoid any drift between database migrations and the database model
by generating DDL dynamically based on a comparison between the running
schema and the model.

This option is the original goal, but it was decided that it would be
best to split the spec into two parts: validating the schema against
the model and then dynamically updating the schema to match the model.
See the dependent spec online-schema-changes.


Data model impact
-----------------

The existing model needs to be brought in line with changes migrations
make. These are limited to a handful of cases:

- PostgreSQL index name limitations
- PostgreSQL Enum type naming
- MySQL index length restrictions
- Foreign key names


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

The new unit test is expected to add only a fraction of a second to the
total time it takes to run tests.


Other deployer impact
---------------------

The new 'db compare' command to nova-manage provides a means of viewing
differences between the current running schema and Nova's model.


Developer impact
----------------

Since the model will now be checked against the results of the database
migrations, it is required to keep the model updated.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johannes.erdfelt

Other contributors:
  None


Work Items
----------

- Bring model into line with existing migrations
- Implement schema comparator
- Implement new 'db compare' command to 'nova-manage'


Dependencies
============

The schema synchronizer is implemented on top of alembic for its DDL
generating functionality. This is already in the OpenStack global
requirements list, but will be a new addition for Nova.


Testing
=======

No extra tests beyond the added unit test.


Documentation Impact
====================

Documentation will need to be updated to include the new 'db compare'
command to 'nova-manage'.


References
==========

https://etherpad.openstack.org/p/kilo-nova-zero-downtime-upgrades
