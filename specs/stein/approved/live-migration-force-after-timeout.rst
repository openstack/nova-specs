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
the operator sooner than the `completion timeout`_. This was the idea with the
`progress timeout`_. Sadly we do not get enough information from QEMU and
libvirt to correctly detect this case. As we were sampling a saw tooth
wave, it was possible for us to think little progress was being made, when in
fact that was not the case. In addition, only memory was being monitored, so
large block_migrations always looked like they were making no progress. Refer
to the `References`_ section for details.

In Ocata we `deprecated`_ that progress timeout, and disabled it by default.
Given there is no quick way to make that work, it should be removed now.
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

.. _completion timeout: https://docs.openstack.org/nova/rocky/configuration/config.html#libvirt.live_migration_completion_timeout
.. _progress timeout: https://docs.openstack.org/nova/rocky/configuration/config.html#libvirt.live_migration_progress_timeout
.. _deprecated: https://review.openstack.org/#/c/431635/

Use Cases
---------

* Operators want to patch a host and want to move all the VMs out of that
  host, with minimal impact to the VMs, so they use live-migration. If the VM
  isn't live-migrated there will be significant VM downtime, so its better to
  take a little more VM downtime during the live-migration so the VM is able
  to avoid the much larger amount of downtime should the VM not get moved
  by the live-migration.

Proposed change
===============

* Config option ``libvirt.live_migration_progress_timeout`` was deprecated in
  Ocata, and can now be removed.
* Current logic in libvirt driver to auto trigger post-copy will be removed.
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

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Kevin Zheng

Other contributors:
  Yikun Jiang

Work Items
----------

* Remove ``libvirt.live_migration_progress_timeout`` and auto post copy logic.
* Add a new libvirt conf option ``live_migration_timeout_action``.

Dependencies
============

None

Testing
=======

Add in-tree functional and unit tests to test new logic. Testing these types
of scenarios in Tempest is not really possible given the unpredictable nature
of a timeout test. Therefore we can simulate and test the logic in functional
tests like those that `already exist`_.

.. _already exist: https://github.com/openstack/nova/blob/89c9127de/nova/tests/functional/test_servers.py#L3482

Documentation Impact
====================

Document new config options.

References
==========

* Live migration progress timeout bug: https://launchpad.net/bugs/1644248
* OSIC whitepaper: http://superuser.openstack.org/wp-content/uploads/2017/06/ha-livemigrate-whitepaper.pdf
* Boston summit session: https://www.openstack.org/videos/boston-2017/openstack-in-motion-live-migration

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Approved but not implemented
   * - Stein
     - Reproposed
