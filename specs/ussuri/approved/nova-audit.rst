..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Add a nova-audit service for periodic maintenance
=================================================

https://blueprints.launchpad.net/nova/+spec/nova-audit

Nova is a distributed system, which means that things fail in strange
ways and data stored across multiple systems gets out of sync with the
actual state of reality. Hosts and instances come and go, along with
network connectivity, the message bus and database. Recently we have
gained a number of "heal $thing" routines that operators can run
either periodically or on demand to synchronize the states of various
services and data stores to resolve or prevent problems. The number of
these tasks is already overwhelming for the average operator, and
tracking new tasks each cycle is not realistic [1]_.

Problem description
===================

As described above, we have an increasing number of maintenance tasks
that need to be run in various scenarios. In most cases, these tasks
are idempotent and safe to run even when nothing is wrong. Operators
need a single mechanism for performing these maintenance tasks and
healing activities that can be run periodically in the background with
minimal impact to runtime performance, other than to hopefully fix
problems related to inconsistencies before they become acute enough to
get an human involved.

Use Cases
---------

As an operator, I would like Nova to heal itself whenever possible to
minimize the number of support incidents requiring human intervention.

As a user, I would like Nova to heal itself whenever possible to avoid
having to involve support for transient issues, which may be
impossible or expensive, especially during off-hour periods.

Proposed change
===============

We already have a number of these maintenance activities codified in
one-shot commands [2]_ that can be run on-demand once a problem has been
identified. Since most of them are not harmful or overly expensive, we
should be able to run those things periodically to attempt to fix
problems automatically before the operator gets involved.

This spec proposes a new binary called ``nova-audit`` to encapsulate
these tasks. Ideally it should be usable in multiple ways:

- As a singleton daemon that periodically runs tasks at various
  intervals according to their potential impact on the system and
  need.
- As a one-shot "fix stuff" command that can be run from cron or
  otherwise scheduled or executed.
- As a daemon or one-shot command that purely audits potential
  problems, but makes no changes.

A new config section of ``[audit]`` would be added with timers and
default values for each task.

Current heal/sync/fix/cleanup tasks we have that could be integrated:

``heal_allocations``
--------------------

This task checks the consistency of allocations in Placement for
instances in Nova. It has a runtime performance impact on both
Placement and the Nova database. Many instances means this should
probably check one instance per cycle, but potentially a short cycle
time.

``sync_aggregates``
-------------------

This task checks that host aggregates match between Nova and
Placement. It is required for some scheduler activities, but not all
cases. It has a runtime performance impact on both Placement and the
Nova database. Many hosts means this should probably check one
aggregate per cycle. Aggregates generally change infrequently, so a
long cycle time of an hour or more is probably reasonable.

``map_instances``
-----------------

This task checks that instances have a suitable mapping to a cell. It
has a runtime performance impact on the Nova database. Many instances
means this should probably check one instance per cycle, with a
relatively short cycle time. It may also be better to check one cell
at a time, very infrequently such as once per day.

``discover_hosts``
------------------

This task ensures that newly-registered hypervisor hosts are mapped to
the appropriate cell. This has a runtime impact on the Nova database,
but there is an efficient way to query for unmapped hosts, so this can
run relatively frequently, such as every ten minutes.

.. note:: There is already a mechanism by which to run this
          periodically in the scheduler service, which should be
          deprecated and replaced by ``nova-audit``.

``archive_deleted_rows``
------------------------

This task archives deleted data from the main database tables into the
shadow tables. It has a runtime performance impact on the Nova
database, both negative (while running) and positive (after
running). Some people never run this, so a cycle time of once per day
or week should be fine. This also needs a parameter to limit the scope
of archived changes to a date range, defaulting to some multiple of
the cycle time.

.. note:: This (and others) may need a configuration element to
          control its execution only between certain hours or days.

``purge``
---------

This task removes data from the shadow tables entirely. It has a
runtime performance impact on the Nova database, but it is just
deleting data from tables accessed only during the
``archive_deleted_rows`` operation. In reality, this should probably
be run directly after the archival process, potentially with a
different age scope.

``heal_instance_mappings`` (proposed)
-------------------------------------

This task scans for orphaned instance mappings in the API database
that have no build request or matching instance in a cell. It has a
runtime performance impact on the Nova API and cell databases, but
only looks for mappings with no cell id. It is bounded by the number
of in-flight instance builds plus the number of orphans, which should
be small. Thus it should be fine to run this relatively frequently,
such as every ten minutes.


Alternatives
------------

We could obviously do nothing. People are managing the complexity
today, so we could simply choose to let them continue.

We could eliminate the daemon and scheduling nature of the proposal
and just provide a very unified interface to running these commands --
a single place to find all the periodic maintenance tasks separate
from the setup sort of things that ``nova-manage`` does.

We could integrate this into ``nova-manage`` itself, under a
"maintenance" subcommand or similar.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None. You could argue that notifications sent about audit activity
would be useful, but doing so would require more setup and
configuration of this utility, as well as connectivity and credentials
to the message bus. We could implement that later if there is a need.

Other end user impact
---------------------

None.

Performance Impact
------------------

There will be some runtime performance impact due to the background
nature of the audit and any cleanup that happens. Mitigation is to not
run it, tune the intervals to be longer, or run it in single-shot mode
when desired.

Other deployer impact
---------------------

Deployers will have to learn about and deploy a new
command/service. This will hopefully be completely offeset by the
reduced complexity of managing and maintaining Nova in the longer
term.

Developer impact
----------------

New maintenance tasks that are added will need to be done in an
idempotent and efficient way and according to whatever interface for
these commands is defined.

Upgrade impact
--------------

A new binary will be added, which will have some impact on
upgrades. Any existing periodic maintenance jobs that call ``nova-manage``
for various tasks will need to convert over to the new command. The
interfaces we have for existing things in ``nova-manage`` can be
deprecated but maintained for an extended period to avoid breaking
existing deployments.

.. note:: Specific tasks like ``db archive_deleted_rows`` may make
          sense to continue to exist in ``nova-manage`` as well.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Feature Liaison
---------------

Feature liaison:
  danms

Work Items
----------

* Create a new ``nova-audit`` command and define scheduling
  mechanisms and internal interfaces.
* Create the new config section and items.
* Implement connectors to integrate the existing tasks we have into
  the new command.
* Modify the ``nova-next`` job to run the audit command in single-shot
  mode after the tempest run, ideally removing the existing
  archive/purge invocation.


Dependencies
============

None.

Testing
=======

Unit and functional testing of the daemon and internal architecture,
and the continued requirement for testing of the actual tasks.  A
single-shot run in the ``nova-next`` job as we currently do today for
archive/purge.

Documentation Impact
====================

Operator documentation about the new command, how to deploy it, and
per-knob documentation about the impacts and suggested intervals.

References
==========

.. [1] Proposed new ``heal_instance_mappings`` command for Ussuri: https://review.opendev.org/#/c/655908/
.. [2] Commands in ``nova-manage``: https://docs.openstack.org/nova/latest/cli/nova-manage.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
