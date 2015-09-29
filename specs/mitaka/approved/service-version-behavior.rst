..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Service Version Behavior Changes
================================

https://blueprints.launchpad.net/nova/+spec/service-version-behavior

There are a lot of situations where operators may have multiple
versions of nova code running in a single deployment, either
intentionally or accidentally. There are several things we can do make
this safer and smoother in code to make the operator's life easier.


Problem description
===================

When running multiple versions of Nova code, care must be taken to
avoid sending RPC messages that are too new (or too old) for some of
the services to understand, as well as avoid accessing the database
with object models that are not able to handle the potential schema
skew.

Right now, during an upgrade, operators must calculate and set version
pins on the relevant RPC interfaces so that newer services (conductor,
api, etc) can speak to older services (compute) while a mix of
versions are present. This involves a lot of steps, config tweaking,
and service restarting. The potential for incorrectly executed or
missed steps is high.

Further, during normal operation, an older compute host that may have
been offlined for an extended period of time could be restarted and
attempt to join the system after compatibility code (or
configurations) have been removed.

In both of these cases, nova should be able to help identify, avoid,
and automate complex tasks that ultimately boil down to just a logical
decision based on reported versions.

Use Cases
----------

As an operator, I want live upgrades to be easier with fewer required
steps and more forgiving behavior from nova.

As an operator, I want more automated checks preventing an ancient
compute node from trying to rejoin after an extended hiatus.

Project Priority
-----------------

The priorities for Mitaka are not yet defined.

Proposed change
===============

In Liberty, we landed a global service version counter. This records
each service's version in the database, and provides some historical
information (such as the compute rpc version at each global version
bump). In Mitaka, we should take advantage of this to automate some
tasks.

The first thing we will automate is the compute RPC version
selection. Right now, operators set the version pin in the config file
during a live upgrade and remove it after the upgrade is complete. We
will add an option to set this to "auto", which will select the
compute RPC version based on the reported service versions in the
database. By looking up the minimum service version, we can consult
the SERVICE_VERSION_HISTORY structure to determine what compute RPC
version is supported by the oldest nodes. We can make this transparent
to other code by doing the lookup in the compute_rpcapi module once at
startup, and again on signals like SIGHUP.

This will only be done if the version pin is set to "auto", requiring
operators to opt-in to this new behavior while it is smoke tested. In
the case where we choose the version automatically, the decision (and
whether it is the latest, or a backlevel version) will be logged for
audit purposes.

The second change thing we will automate is checking of the minimum
service version during service record create/update. This will prevent
ancient services from joining the deployment if they are too old. This
will be done in the Service object, and it will compare its own
version to the minimum version of other services in the database. If
it is older than all the other nodes, then it will refuse to start. If
we refuse to start, we'll log the versions involved and the reason for
the refusal visibly to make it clear what happend and what needs
fixing.

Alternatives
------------

We could continue to document both of these procedures and require
manual steps for the operators.

Data model impact
-----------------

There are no data(base) model impacts prescribed by the work here, as
those were added preemptively in Liberty.

The Service object will gain at least one remotable method for
determining the minimum service version.

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

Checking the minimum version in the database on compute_rpcapi module
startup will incur a small performance penalty and additional database
load. This will only happen once per startup (or signal) and is
expected to be massively less impactful than the effort required to
manually perform the steps being automated.

It would also be trivial for conductor to cache the minimum versions
for some TTL in order to avoid hitting the database during a storm of
services starting up.

Other deployer impact
---------------------

Deployer impact should be entirely positive. One of the behaviors will
be opt-in only initially, and the other is purely intended to prevent
the operators from shooting themselves in their feet.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Add a minimum version query to the Service object
* Automate selection of the compute RPC version when the pin is set to auto
* Automate service failure on startup when the service version is too old
* Hook re-checking of the minimum version to receiving a SIGHUP

Dependencies
============

None

Testing
=======

As with all things that affect nova service startup, unit tests will
be the only way to test that the service fails to startup when the
version is too old.

The compute RPC pin selection can and will be tested by configuring
grenade's partial-ncpu job to use "auto" instead of an explicit
pin. This will verify that the correct version is selected by the fact
that tempest continues to pass with nova configured in that way.

Documentation Impact
====================

A bit of documentation will be required for each change, merely to
explain the newly-allowed value for the compute_rpc version pin and
the potential new behavior of starting an older service.


References
==========

* https://review.openstack.org/#/c/201733/
* http://specs.openstack.org/openstack/nova-specs/specs/liberty/approved/service-version-number.html
