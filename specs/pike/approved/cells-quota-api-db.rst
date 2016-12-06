..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
CellsV2 - Move quota tables to API database
===========================================

https://blueprints.launchpad.net/nova/+spec/cells-quota-api-db

As part of the CellsV2 work we are in the process of splitting the current cell
database. Quotas in nova are global and should apply across cells. Because
of this their data needs to reside in the API database.

Problem description
===================

Quotas for projects and users need to be enforced across cell boundaries.
Quotas are also exposed in the API.  If quotas remain in the cell
database then the API would have to me modified to expose cell information.
Alternatively quota data would have to be replicated across all cells which
would make it difficult to enforce a global quota.

Use Cases
---------

Operators and users wish to enforce a quota that is applicable across cells.

Proposed change
===============

We propose to move the quota related tables that currently reside in the
cell database to the API database. These tables are::

    quotas
    quota_classes
    quota_usages
    project_user_quotas
    reservations

Database models will be created in the API database. These will closely
match the existing models in the cell database. Some modifications may be
made to these tables to clean up the existing data model.

The ``Quotas`` object in nova makes use of functions in ``quota.py``. It is
mostly an RPC facade to the ``quota.py`` API. To handle the transition period
where both the main database and API database are used, all database access
will be moved to the ``Quotas`` object. The ``DbQuotaDriver`` in ``quota.py``
will be modified to use the ``Quotas`` object for queries.

Wrapper methods will be created for the existing database access. Wrapper
methods that perform any ``get`` type operation on the ``quotas``,
``quota_classes``, ``project_user_quotas`` tables will be modified to load
initially from the API database. If the item is not found then it will be
searched for in the cell database.

Migration functions will be created to migrate data from the cell to API
database. These methods will be added to the nova manage
``online_data_migrations`` command.

Migration of flavors has already been completed and for the above tables we
will generally follow this example. [3]_

The ``quota_usages`` and ``reservations`` tables will not be used going forward
because we will count resources instead of tracking usage and reservations as
separate entities.

Alternatives
------------

Without changing the nature of quotas there is likely no alternative for
the ``DbQuotaDriver`` but to move its tables to the API database. Alternatives
for quotas in general include 'Quotas Reimagined' [1]_ and the 'Delimiter' [2]_
project. The former specification would likely still make use of some of the
existing tables that would require migration. A separate quotas library or
service would create an entirely new quota data store.

Data model impact
-----------------

The data model impact will be large as many new tables will be created in
the API database. The models will not be detailed here as they are
essentially unchanged from the cell database.

REST API impact
---------------

None - Cells implementation should not be exposed in the API.

Security impact
---------------

None, moving the Quota data to the API databse keeps the implementation
as close as possible to the current model. It should be no more or less
difficult than now to break quota enforcement.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The performance impact of the changes will be negligible. However, the
performance of the ``DbQuotaDriver`` will also not be improved for the
large-scale deployments that CellsV2 is targeting.

During migration there will be a larger performance impact to quota operations
and therefore build requests. This comes as database accesses for the
``quota``, ``project_user_quota``, and ``quota_classes`` tables may require
two database requests.

This performance impact will be short term and will last until data has been
migrated.

Other deployer impact
---------------------

Deployers will have to be aware of the data migration when upgrading. They
will have to know about ``nova-manage`` commands to migrate data to the API
database.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  None

Work Items
----------

* Create database models and migrations for quota tables in the API database.
* Create database access and wrapper methods for API datbase.
* Modify the ``DbQuotaDriver`` to use the new database access methods.
* Create migration methods to move data to the API database and add this
  method to ``online_data_migrations``.

Dependencies
============

None


Testing
=======

* Add unit and functional tests for new database models.
* Add new unit tests for database access wrapper methods.
* Add new functional tests for data migration.
* Modify unit tests for the quota driver.
* Enhance existing functional tests for quotas.

Documentation Impact
====================

Operator documentation may need to me modified to include details of
upgrading and migrating data using ``nova-manage`` command.

References
==========

.. [1] https://review.openstack.org/#/c/182445/
.. [2] https://review.openstack.org/#/c/284454/
.. [3] https://blueprints.launchpad.net/nova/+spec/flavor-cell-api

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced but no changes merged.
   * - Ocata
     - Re-proposed.
   * - Pike
     - Re-proposed.
       Updated without use of ``quota_usages`` and ``reservations``.
