..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Live-Migration per instance timeout
===================================

https://blueprints.launchpad.net/nova/+spec/live-migration-per-instance-timeout

Add a new microversion to live-migrate API to abort or force complete any
libvirt live-migration operation after a given timeout.

Problem description
===================

Nova currently optimizes for limited guest downtime, over ensuring the
live-migration operation always succeeds. This can make live-migration
in Nova look much less "reliable" than live-migration offered in other
cloud and server virt systems.

A key observation is that the trade off between guest liveness and how long
you are willing to wait for a live-migration to complete is not the same for
every instance, nor for each live-migration API call made on the same
instance. If a failed live-migration means the guest now has to stay on the
host you are in the process of patching and rebooting, the guest will have
significantly more downtime than if you had a small increase in the downtime
the VM would experience during live-migration.

With current live-migrate API and config options, operators do not have
fine-grained control over per instance live-migrate operations. If they want to
treat any particular instance live-migrate operation different then they have
to change the related config value to better fit and restart compute services
which makes live-migration experience very unpleasant.

Given the recent removal of the progress timeout, we have discussed with
operators that they would like to customize the timeout per live-migration
operation. Based on the VM involved and the cost of not moving the VM, they
can make the call of how long to wait. In a similar way, they want to decide
if they should abort after that timeout (avoiding the VM having any more
downtime than ``libvirt.live_migration_downtime``), or force the
live-migration to move (allowing more downtime than
``libvirt.live_migration_downtime`` to ensure the VM moves).

If we give operators the ability to set a custom timeout per live-migration
operation, this causes some conflict with some other configuration options.
Nova tells libvirt only to allow a live-migration to complete if there will be
no more than ``libvirt.live_migration_downtime`` milliseconds of downtime.
To further reduce the impact of live-migration on the guest VM, Nova slowly
ramps up the amount of allowed downtime up to that maximum value. Nova uses
the config options ``libvirt.live_migration_downtime_steps`` and
``libvirt.live_migration_downtime_delay`` to decide how long to take before
reaching ``libvirt.live_migration_downtime`` milliseconds of allowed VM
downtime. Currently these configuration values must be carefully changed to
match the value of ``libvirt.live_migration_completion_timeout``, meaning not
spend all the time ramping up and not allowing enough time for a VM to move
before completion timeout expires. If we allow operators to specify their own
timeout value per live-migration operation, we must find a way to reconcile
this with logic that ramps up the amount of allowed downtime before
the live-migration is allowed to complete.

Use Cases
---------

* Operators want to patch a host and want to move all the VM's out of that
  host. In this case they want to force a VM to move when timeout is reached
  because they find the risk of possible needing to reboot the VM less
  acceptable than pausing the VM to make it move.

* Operators want to move the busy VM out of a host to balance out their
  cluster. In this case they want flexibility to kick off live-migration
  operation with an option to cancel the operation when the timer expires.

Proposed change
===============

Add a new microversion to Live-Migrate Server API to add support for following
two optional parameters:

* ``timeout_seconds`` - Optional parameter to specify time in seconds after
  which nova will take actions on the given live-migration operation. This will
  override the config option ``libvirt.live_migration_completion_timeout``.
  Note, unlike the configuration this is an absolute timeout, not one scaled up
  to match the size of the VM.

* ``on_timeout`` - This optional parameter can be set to
  ``force_complete`` or ``abort``. This will override the config option:
  ``libvirt.live_migration_action_on_timeout``, that defaults to ``abort``.

To help upgrades, we return 400 for any requests containing either of the new
timeout paramter and before all compute nodes have been upgraded to report at
least the service version that matches when this feature was added.

To address issue with ramp up time, we propose to spend half of the specified
completion timeout ramping up to maximum downtime as normal. After that, we
jump up to ``libvirt.live_migration_downtime``. This will ensure VM will spend
half of the specified timeout with the best chance of letting live-migration
complete without having to abort or force-complete.

Alternatives
------------

Operators can call either the ``delete`` migration API to abort a running
live-migration or call ``force-complete`` to trigger post-copy or pause the
VM being live-migrated. However this is far from convenient, and can lead to
races in timeouts happening just before calling ``force-complete``.

There are many other ways we could modify the downtime ramp up logic. Given
the discussions on re-working that logic we just do the minimum to ensure
``libvirt.live_migration_downtime`` is reached before we hit the timeout
specified by the operator.

Data model impact
-----------------

The Migration object takes two new params for live-migrate API:

* timeout_seconds - integer attribute.

* on_timeout - enum of (["force_complete", "abort"]).

REST API impact
---------------

* URL: POST /v2.1/servers/{server_id}/action

  JSON request body::

    {
        "os-migrateLive": {
            "host": "target-host",
            "block_migration": "auto",
            "timeout_seconds": 60,
            "on_timeout": "force_complete"
        }
    }

A new microversion will be introduced to os-migrateLive API, which will take
two additional and optional parameters ``timeout_seconds`` and
``on_timeout``.

* JSON schema for ``timeout_seconds``::

    {
        "timeout_seconds": {
            "type": "integer",
            "minimum": 0
        }
    }

* JSON schema for ``on_timeout``::

    {
        "on_timeout": {
            "type": "string",
            "enum": [ "force_complete", "abort" ]
        }
    }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Add support for API in python-novaclient.

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
  Sarafraj Singh (raj_singh)

Other contributors:
  OSIC

Work Items
----------

* Add logic in libvirt to make use of these new parameters.
* Add API to expose per operation force-timeout and actions.

Dependencies
============

We first need the configuration added for the default timeout action:
https://blueprints.launchpad.net/nova/+spec/live-migration-force-after-timeout

Testing
=======

Need new tempest tests for the new API.

Look into busy workloads inside VMs to test the above API in the gate's
live-migration job.

Documentation Impact
====================

Need to update api-ref with details of the new API.

Should also update the API concept guide to cover how best to use
live-migration with all these new APIs we have added.

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
