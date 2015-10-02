..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Add a service version number to the database
============================================

https://blueprints.launchpad.net/nova/+spec/service-version-number

We have previously identified online data migrations as critical for
supporting live upgrades. We do well with that today, as long as
control services are upgraded together (conductor, api, etc). In order
to extend this further, we need a way to determine that some of the
control services have been upgraded, but not all. This information
will allow us to avoid upgrading data online until all of the services
are upgraded to the point at which they can handle the new schema.

Problem description
===================

Partially upgrading control services will result in newer conductors
beginning to convert data to expand into new schema before older
conductors and other control services are ready. If you upgrade all
your control services together, this works well, but if you don't (as
would be more realistic) you have the potential to break some of the
older control services.

For example, in Kilo we can apply the database schema before starting
to upgrade any of the code. However, once we upgrade any one component
that talks to the database directly, online migrations will begin to
happen, and any other nodes that read from the database directly will
be confused as things are starting to move.  Since services like
nova-api, nova-scheduler, nova-conductor, etc all talk directly to the
database, we're currently unable to upgrade these services
independently. If we had this service version number available, we
could avoid doing any online migrations until all the affected
services are upgraded to a new-enough point.

Use Cases
----------

As a deployer, I want to be able to stage my upgrades of control
services, without having to take down *all* of my conductor, api,
scheduler, etc nodes and restart them together spanning a live data
migration.

Project Priority
-----------------

This is an upgrades enhancement.

Proposed change
===============

The proposed change is adding a version number column to the services
table. Each service will report its version number when it updates its
service record. We will be able to determine if all services are on
the same level of code by checking to see if there is more than one
version in the table (optionally grouped by service). We can use this
information to conditionally enable online data migrations. For
example, we can check to see if all the conductors are upgraded to the
same level by doing something like this:

  SELECT DISTINCT version FROM services WHERE binary='conductor';

If we do that at conductor startup, we can set a flag to not enable
migrations that require conductor services to be newer than a specific
version. We could also refresh this on SIGHUP like we currently do for
config reload.

Initially, the column will be created with a default of NULL, and the
Service object will treat NULL as "version 1". Subsequent changes will
set versions to 2. Any time we do an online data migration, we will
need to bump the service version number.

Longer-term we could try to tie RPC versions to this information to
make pinning easier. Because that has potentially hard-to-quantify
implications on backports (which occasionally do need to modify RPC
interfaces), I propose we leave that out of the scope of this work for
now. Even still, tying RPC versions to this service version would be
work for the next cycle once this is in place and we can depend on
it.

The other thing that this enables is the ability to have a service
start up and know that it is massively out of date. Presumably we
should be able to have a conductor start up and say "wow, I'm much
older than the other conductors, I should log an error and exit."
Determining what the minimum version is and should be is something we
would do in M when we have this for the N and N-1 releases such that
we can depend on it.

We need to do this in L so that we can leverage it in M. If we delay
this until M, we won't be able to rely on it until N.

Why not use semver?
-------------------

In things like our RPC API versions, we use semver-like version
numbers. This allows us to make decisions about incoming calls and
whether they're compatible with a newer node, and generally define
rules for what is a breaking (i.e. major bump) change.

This service version number doesn't imply any semantics itself, but
rather just provides a vector with which we can orient ourselves in
time to make other decisions. As described elsewhere in this spec,
that may mean that we can decide what RPC version to use, or whether
it is safe to start doing online data migrations. *Those* decisions
extract semantic meaning out of the service version vector, and they
may have significantly different rules (as would certainly be the case
with the aforementioned RPC and DB decisions).

Alternatives
------------

We can continue to do what we do today, which is start converting data
from one schema to the other as soon as we roll new code. We keep the
restriction of all control services being required to update together.

We could also codify this in config somehow, but that will require
much more operator intervention, and increases the likelihood of error.

Data model impact
-----------------

A schema migration will be written to add a version column to the
table. The version will be an integer, nullable, default to NULL.

The Service object will be extended to support this version, and will
treat a NULL version as version "1", which will avoid us having to do
any data migrations on existing service records. New saves will
initially write version "2" for all services.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

This will make upgrading nova services easier and more
flexible/forgiving for deployers.

Developer impact
----------------

Developers (and reviewers) will need to ensure that the service
version number is bumped across any online data migration that we do
(like the recent flavor restructuring).

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Other contributors:
  alaski

Work Items
----------

* Write the schema migration
* Update the sqlalchemy models and service object
* Write some object methods to help with querying service version
  numbers in ways that will be friendly for determining upgrade
  feasibility.
* Extend the service startup code to check version spread and persist
  so that we can use that as a static flag for enabling migrations.

Dependencies
============

None. This is mostly early setup for being able to do more interesting
upgrade things in M.

Testing
=======

This should be fully testable with unit tests.

Documentation Impact
====================

Ideally, this should make upgrades require less documentation.

References
==========

* http://specs.openstack.org/openstack/nova-specs/specs/kilo/approved/flavor-from-sysmeta-to-blob.html
