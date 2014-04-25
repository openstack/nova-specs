..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Stop using the scheduler run_instance method
============================================

https://blueprints.launchpad.net/nova/+spec/remove-cast-to-schedule-run-instance

Currently the scheduler is used to both pick a host for an instance to be built
on and to handle some setup and failure conditions for booting an instance.
The scheduler should be responsible for placement logic and everything else
should be moved elsewhere.  This will make efforts to introduce new scheduler
drivers or split the scheduler out of Nova easier to tackle by keeping a clean
interface with a clear responsibility.


Problem description
===================

The flow of execution for spawning an instance is complicated and highly
distributed.  Some amount of distribution is necessary but there is work
happening and decisions being made in unexpected parts of the code.  This makes
it very difficult to look at separating the scheduler out, and means that it
will need intimate integration with Nova that should be unnecessary.  It is
also unecessarily difficult to reason about what is happening at which point in
the code which makes it challenging to improve those parts of the code.


Proposed change
===============

In Havana it became possible to query the scheduler for a list of hosts to
provision an instance to.  The conductor service also emerged as a place to
help orchestrate tasks that don't logically belong in either the api or compute
nodes.  There has already been work to move some of the spawn instance workflow
into the conductor and the final part of that effort is to have the conductor
communicate with compute nodes rather than the scheduler.

There is a new, currently unused, build_and_run_instance method in the compute
manager which mimics the currently used run_instance method, but handles a
failed build by sending an RPC cast to the conductor service rather than the
scheduler.  The proposed change is to have the conductor query the scheduler
and send a message to a compute which invokes the new build_and_run_instance
method.  Because the new method is unused and therefore untested by Tempest
there will likely be some work required to achieve full compatibility with the
current run_instance method.

Alternatives
------------

An alternative would be to rework the run_instance method to cast back to
conductor rather than use the new build_and_run_instance method.  This was
decided against because the amount of refactoring that would need to happen
there meant it was easier to rebuild that method from scratch.

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

None.  The notifications being sent by the scheduler will be ported over to
conductor to maintain the same behaviour.

Other end user impact
---------------------

None

Performance Impact
------------------

Some database updates that were occuring within the scheduler will be moved out
to less performance critical sections of code.  This should speed up the
scheduler.

There may be a decrease in the amount of time to boot an instance if it needs
to be rescheduled.  The new build_and_run_instance performs some pre-build
checks earlier and doesn't generally deallocate and reallocate networks for a
rescheduled instance.  It will deallocate/reallocate if the baremetal driver is
in use as the networking there is host specific.

Other deployer impact
---------------------

None.

Developer impact
----------------

Developers will need to be aware of the new code path being used.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alaski

Other contributors:
  None

Work Items
----------

  * Change the conductor to query the scheduler and cast to a compute.

    * Move notifications from the scheduler into the conductor.


Dependencies
============

None


Testing
=======

This is essentially a refactoring of the current spawn process.  So the current
Tempest tests will act as good integration tests for this change since the new
method will be used on every instance boot.


Documentation Impact
====================

None


References
==========

None
