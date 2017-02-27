..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Live-Migration force after timeout
==================================

https://blueprints.launchpad.net/nova/+spec/live-migration-force-after-timeout

Replace the existing flawed automatic post-copy logic with the option to
force-complete live-migrations on completion timeout, instead of aborting.

Problem description
===================

In an ideal world, we could tell when a VM looks unable to move, and warn
the operator sooner that the completion timeout. This was the progress
timeout. Sadly we do not get enough information from QEMU and libvirt to
correctly detect this case. As we were were sampling a saw tooth wave, it was
possible for us to think little progress was being made, when in fact that
was not the case. In addition, only memory was being monitoring, so large
block_migrations always looked like they were making no progress.

Last cycle we deprecated that progress timeout, and disabled it by default.
Given there is no quick way to make that work, it should be removed in Pike.
The automatic post-copy is using the same flawed data, so that logic should
also be removed.

Nova currently optimizes for limited guest downtime, over ensuring the
live-migration operation always succeeds. When performing a host maintenance,
operators may want to move all VMs from the affected host to an unaffected
host. In some cases, the VM could be too busy to move before the completion
timeout, and currently that means the live-migration will fail with a timeout
error.

Automatic post-copy used to be able to help with this use case, ensuring Nova
does its best to ensure the live-migration completes, at the cost of a little
more VM downtime. We should look at a replacement for automatic post-copy.

Use Cases
---------

* Operators wants to patch a host and want to move all the VM's out of that
  host, with minimal impact to the VMs, so they use live-migration. If the VM
  isn't live-migrated there will be significant VM downtime, so its better to
  take a little more VM downtime during the live-migration so the VM is able
  to avoid the much larger amount of downtime should the VM not get moved
  by the live-migration.

Proposed change
===============

* Config option ``libvirt.live_migration_progress_timeout`` was deprecated in
  Ocata, and can now be removed.
* Curent logic in libvirt driver to auto trigger post-copy will be removed.
* A new configuration option ``libvirt.live_migration_timeout_action`` will be
  added. This new option will have choice to ``abort`` (default) or
  ``force_complete``. This option will determine what actions will be taken
  against a VM after ``live_migration_completion_timeout`` expires. Currently
  nova just aborts the LM operation after completion timeout expires.
  By default, we keep the same behavior of aborting after completion timeout.

Please note the ``abort`` and ``force_complete`` actions that are options in
``live_migration_timeout_action`` config option are the same as if you were to
call the existing REST APIs of the same name. In particular,
``force_complete`` will either pause the VM or trigger post_copy depending on
if post copy is enabled and available.

Alternatives
------------

We could just remove the automatic post copy logic and not replace it, but
this stops us helping operators with the above use case.

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
  Raj Singh (raj_singh)

Other contributors:
  John Garbutt (johnthetubaguy)
  OSIC

Work Items
----------

* Remove ``libvirt.live_migration_progress_timeout`` and auto post copy logic.
* Add a new libvirt conf option ``live_migration_timeout_action``.

Dependencies
============

None

Testing
=======

Add tempest and unit tests to test new logic.

Documentation Impact
====================

Document new config options.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced

