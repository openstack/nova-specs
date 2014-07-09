..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
 Move prep_resize to Conductor
===============================

https://blueprints.launchpad.net/nova/+spec/move-prep-resize-to-conductor

So as to prepare the scheduler to be a separate project, we need to remove
all proxy calls from the scheduler to compute nodes.
prep_resize() is still in Scheduler V3 API, so we need to modify how cold
migrations are retried.

Problem description
===================

When a cold migration is requested, there is a direct call from conductor to
compute.prep_resize() which is OK. The problem is when the cold migration is
failing, where compute node is asking Scheduler to reschedule a new migration
by calling scheduler.prep_resize(), which itself calls compute.prep_resize()
after issuing a select_destinations().

Proposed change
===============

The idea is to replace the call back by conductor.migrate_server instead of
scheduler.prep_resize in the compute prep_resize method.


Alternatives
------------

All prep_resize logic should be left to the conductor, but that's a bigger step
than just moving the scheduler logic to conductor. With regards to small
iterations, that blueprint is quicker to implement and less risky, so that
another blueprint for placing cold and hot migrations to conductor [1] could
use it as dependency.


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

None

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
  sylvain-bauza

Other contributors:
  None

Work Items
----------

- Replace call to scheduler.prep_resize by call to conductor.migrate_server
  in compute.prep_resize
- Remove prep_resize in Scheduler RPC API and note it to be removed in manager

Dependencies
============

None


Testing
=======

Covered by existing tempest tests and CIs.


Documentation Impact
====================

None


References
==========

* [1] https://blueprints.launchpad.net/nova/+spec/cold-migrations-to-conductor-final
