..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Optional Placement Database
===========================

https://blueprints.launchpad.net/nova/+spec/optional-placement-database

Since its inception there's been a long term goal of extracting the placement
services to its own repository from which it can be packaged and operated as an
independent service. Work to make this happen has been in progress for quite
some time, but one limiting factor is management of the placement database
connection and the placement data. At the moment placement data is kept in the
same database as the nova API.

Discussion at the Rocky PTG and elsewhere indicates that providing deployers
with options for how to manage the placement data will ease migration. This
spec proposes separating the configuration of the placement database connection
to its own setting that falls back to the nova api database setting when not
defined. This provides a variety of management options and also cleans up the
code for eventual migration in a useful way (details below).

Problem description
===================

We'd like to make it easy for deployers to manage their placement data in
whatever way they like. While there are many factors in this, one thing that
makes doing so more complicated now is that the connection to the placement
database is configured using the ``[api_database]/connection`` configuration
setting, so isolating placement database configuration is not easy. There are
many ways around this problem (see the :ref:`alternatives` below) but using a
distinct configuration option is explicit and translates well into a future
when the same configuration setting can be used (limiting changes to the name
of a file, rather than the name of a configuration setting).

At the same time we'd like to make it easy for developers of placement to start
limiting the extent to which other nova code is imported into code that is
dedicated to placement. Using a separate configuration setting makes it
possible to easily isolate establishing the database session (see the
`isolation work in progress`_).

Similarly, we'd like to provide opportunities for packagers to lay the
groundwork for migrations where data management has a clearly identifiable
entry point.


Use Cases
---------

As a deployer, I want to configure my new placement service to save data to its
own database because I know that in the future I will be able to use it
separately.

As a different deployer, I want to configure my placement service to continue
using the nova api database because I don't care about having separate
databases.

As a packager, I want to allow my users to have granular control over the
location of the placement database by using the "normal" method of setting
configuration.

As a developer, I want to prepare for placement's extraction by limiting
overlap between placement and nova code.

Proposed change
===============

There are two main changes proposed here.

Placement database connection
-----------------------------

One is to add a configuration group, ``placement_database`` that operates in
the same fashion (and with the same options) as the existing ``api_database``
group. If ``[placement_database]/connection`` is set, then its value is used
for an independent connection to the described database. If it is not set, the
connection string from ``[api_database]/connection`` is used, but it is
identified as a separate SQLAlchemy session.

This has the advantage of being reusable once placement is extracted. The same
configuration group and names can continue to be used in the future.

There is a `database connection work in progress`_.

Isolated placement database configuration
-----------------------------------------

Once there is a separate SQLAlchemy session for the connection to whatever
hosts the placement data, it is possible to manage that session independently
of the main nova code. This is useful for centralizing the placement code into
itself, easing the eventual extraction and supporting the ongoing cleanup of
the placement code. There is an `isolation work in progress`_.

.. _alternatives:

Alternatives
------------

The primary alternative here is to do nothing other than document the way that
deployers can run the placement service with its own configuration file; one
that sets the API database connection to whatever database the deployer would
like to use for placement. This is definitely a workable solution but does not
lay the foundation for a cleaner configuration, nor the isolation of the
database configuration mentioned above.

Data model impact
-----------------

This change does not involve changing the data model itself. For the time being
migrations and database schema continue to be managed in the same way. If there
is simultaneously both an API and placement database, they will create the
same tables and run the same migrations (in different databases). Future work
will address managing migrations and schema within placement.

REST API impact
---------------

None.

Security impact
---------------

If a new database is used, then deployments will need to adapt any security
measures to be aware of it.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Database management in placement should be invisible to end users of placement.

Performance Impact
------------------

Using a separate database increases options for managing scaling and
performance. Presumably separating placement and nova API activity into
different database servers could be useful.

Other deployer impact
---------------------

Besides the configuration options already mentioned, deployers will need to be
aware of the several different ways they can manage and migrate their placement
data. At this time the plan is to document these things, based on
experimentation that has not yet been done. These changes will enable some of
that experimentation.

This spec explicitly does not provide definite guidance for how a deployer
would upgrade from a placement-within-nova deployment to a
placement-not-in-nova deployment. It is laying groundwork for that.

Developer impact
----------------

Other than being aware of it, there's no functional change to how developers
will work on placement.

Upgrade impact
--------------

This spec explicitly does not address concerns related to upgrading come a
system where placement is not extracted to one where it is. This work is a
precursor to that.

If this configuration change is merged in Rocky but placement is not extracted
in the *S* cycle, then there will be no upgrade concerns. Existing
configurations will continue to work.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  volunteers

Work Items
----------

This work has started in `database connection work in progress`_ and
`isolation work in progress`_.

* Create the [placement_database] configuration group.
* Document that group.
* Update test fixtures to reflect the new placement database session.
* Update unit and functional tests to use the new session.
* Update placement database context managers to use the new session.
* Isolate session configuration within placement.
* Update contributor and user documentation that discusses the placement
  database.

Dependencies
============

None.


Testing
=======

Existing functional tests will continue to exercise the use of the database. If
we choose to do so, we can add or adjust an existing gate job to set and use a
different placement database connection.

Documentation Impact
====================

A medium term goal of this work is to make it easy to do experiments that will
help create clear documentation for migration strategies when placement is
extracted.

References
==========

* Placement extraction `blog post`_.
* Placement extraction mailing `list post`_.

.. _database connection work in progress: https://review.openstack.org/#/c/362766/
.. _isolation work in progress: https://review.openstack.org/#/c/541435/
.. _blog post: https://anticdent.org/placement-extraction.html
.. _list post: http://lists.openstack.org/pipermail/openstack-dev/2018-March/128004.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
