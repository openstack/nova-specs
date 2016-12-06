..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Improve Scheduler Logging
=========================

https://blueprints.launchpad.net/nova/+spec/improve-sched-logging

The nova scheduler includes a number of very complicated filters with
non-obvious failure modes (the NUMATopologyFilter in particular comes to mind).
It is possible to have a situation where a given instances fails to schedule,
and it is not immediately apparent as to what exactly caused the failure.
Accordingly, it is proposed that we allow for optional detailed messages about
precisely *why* a scheduler filter is failing.


Problem description
===================

If the nova scheduler fails to find a suitable compute node for an instance, it
is sometimes tricky to figure out what the problem was.  For simple filters
(CPU/RAM/disk) the checks are fairly straightforward, but for more complicated
filters (PCI, IO ops, and especially NUMA-related things like CPU pinning, huge
pages, and hyperthreading) its difficult to manually determine why things
failed from looking at the logs.  Even with debug logging enabled, there are
scenarios where the NUMATopologyFilter filter can fail with no useful logs.

As an example, if the NUMATopologyFilter filter fails a compute node, it
logs a pretty generic message:

*"%(host)s, %(node)s fails NUMA topology requirements. The instance does not
fit on this host."*

There are quite a few different ways that we could end up getting to that point
without emitting any other logs.  For example, in
objects.numa.NUMACell.can_fit_hugepages(), there is a case where it can raise
exception.MemoryPageSizeNotSupported.  If that happens, we propose that it
would be better to have a more detailed error like:

*"%(host)s, %(node)s does not support page size %(size)d."*

Or if the numa node doesn't have enough CPU/RAM to satisfy the requirements,
we propose that the exact problem should be indicated in the log:

*"%(host)s, %(node)s CPUs avail(%d) < required(%d)"*

Use Cases
---------

The primary use case is when an end-user tries to perform an operation that
requires scheduling an instance, and it fails.  They then ask the Deployer why
it failed, but there is no obvious failure reason in the logs.

Proposed change
===============

As discussed at the Summit, the proposal is two-pronged.

First, we will attempt to ensure that all scheduler filter failures have a
useful log message describing why the filter failed for that host.

Second, we propose adding a new "sched_detailed_log_only_on_failure" option,
which will default to True.  When this option is set, we will accumulate
debug logs in memory (the current plan is to use a sched-filter-specific
logging mechanism, but we could likely use
https://review.openstack.org/#/c/227766/ or similar if it gets merged) and
then emit them only if the overall scheduling operation fails (i.e.
exception.NoValidHost is raised).  If the scheduling operation passes, the
logs will be thrown out.  Since the logging would happen only on failure, it
is proposed that we log the detailed filter logs at the "info" level.
(The actual NoValidHost error log will still be logged at the current logging
level.) If this config option is set to False, we will emit logs exactly the
way we do currently.

Third, in order to further reduce the logging, it is proposed that a new
"scheduler_suppressed_log_filters" config option be added.  This will consist
of a list of filter names (analogous to "scheduler_default_filters") for which
we want to suppress debug logging.  In this way operators could avoid logging
for cases which fail for trivial reasons like lack of CPU/RAM/disk.  We propose
that this option default to ['CoreFilter', 'RamFilter', 'DiskFilter',
'ComputeFilter'].  This option would apply regardless of which way the
"log only on failure" config option is set, for several reasons:

* When logging only on NoValidHost we would still need to do work to store
  the logs for the success path, so this would give a way to reduce the
  overhead and also reduce the amount of logging on a scheduler failure.
* If the operator decides they don't need logging from particular filters
  then it likely doesn't matter whether we only log on failure.
* If an operator does want to change the suppressed filters when changing
  the  "sched_detailed_log_only_on_failure" config option, then they have
  the option of doing so.


Alternatives
------------

The alternative would be to enhance the existing debug logs so that all failure
cases are covered.  For this to be useful the deployer would need to run the
scheduler with debug logging enabled, and the extra logging would apply to all
cases, including ones that were ultimately successful.

Data model impact
-----------------

None

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

Expected to be low, assuming the simple filters (CPU/RAM/disk/etc.) have
their logs suppressed.  There will be some additional CPU time spent
processing logs and some additional memory consumed during scheduling.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cbf123 (aka cfriesen)

Other contributors:
  lbeliveau

Work Items
----------

* Add the new config option.
* Add the core scheduler code to log the error messages (if there are any) if
  the scheduler is unable to locate a suitable compute node.
* For each filter, ensure that all failure modes are covered by an error
  message.  This can be parallelized, since the logging for each filter is
  essentially independent of the other filters.


Dependencies
============

* None


Testing
=======

There should be no end-user-visible changes, so current Tempest and functional
tests should suffice for proving correctness.

To exercise the additional logging, some additional unit tests will be added
covering a number of strategic scenarios where different filters fail.


Documentation Impact
====================

The Operations Guide would be updated with information on the existance of the
config option and how it would simplify debugging scheduling failures.

A new config option is being introduced, so it would need to be documented
appropriately.

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
