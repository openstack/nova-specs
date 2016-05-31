..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Automate Live Migration Completion Strategies
============================================================

Blueprint:
https://blueprints.launchpad.net/nova/+spec/auto-live-migration-completion

There are number of strategies which can be used to help a live
migration operation complete. It is desirable to automate the use of
these based on how important it is to the operator that the live
migration completes.

Problem description
===================

When an operator performs a live migration they need to monitor it to
ensure it is making progress and take actions to help it complete.
This is labor intensive and expensive in terms of cloud operating
costs. It would be preferable if the live migration process could
automatically take action to try and complete the migration.

Use Cases
----------

As an operator of an OpenStack cloud, I would like live migrations to,
as far as possible, progress to completion without operator
intervention.

Proposed change
===============

The live migration processing will automatically determine what
strategies to employ if the live migration is struggling to complete
due to the instance's memory access or disk I/O rates.

The options available are as follows:

Maximum Downtime Setting

In order to perform the switch over from the source to target instances
the live migration process needs to pause the instance for a short
period. The default value is 500 milliseconds but this can be adjusted
during the live migration process via a libvirt API call. Increasing
this value may enable the migration to complete.

Auto-converge

This feature provides a method for slowing down guest execution speed
in order to allow the live migration to copy dirty memory pages to the
target and complete the migration. It has to be enabled prior to the
start of a live migration operation. If enabled the live migration
process will make a first pass of copying all memory pages to the
target then incrementally decrease the instances CPU speed until the
migration is completed.

By default it will initially decrease the CPU speed by 30% then reduce
it by further increments of 10% until the instance is effectively
paused. The initial decrease and increment size can be adjusted during
the live migration process via the libvirt API. However these API calls
are experimental so nova will not be using them.

Auto-converge can only be used if libvirt version 1.2.3 and qemu
version 1.6 are installed on the source compute node. A nova
configuration flag called :code:`live_migration_permit_auto_converge`
will be added. This flag can have the following values:

no   - never use auto-converge.

yes  - use auto-converge if available and no other better migration
       strategy is availble.

Post-Copy

Post-copy must be enabled prior to the migration starting if it is to
be employed.  A libvirt API call is performed to tell it to switch.
Post-copy can only be used if libvirt version 1.3.3 and qemu
version 2.5 are installed on the source and target compute nodes. A
nova configuration flag called :code:`live_migration_permit_post_copy`
will be added. This flag can have the following values:

no   - never use post-copy.

yes  - use post-copy if it is available.

Nova will allow the live migration process will make a first pass of
copying all memory pages to the target before considering a switch
to post copy mode. The switch to post-copy will cause the instance
on the target to become active instead of the instance on the source
node. Qemu will then start pulling memory pages that have not yet
been updated on the target from the source. If the target instance
tries to access a page of memory that has not yet been copied to the
target qemu will fetch the page from the source.

The use of Post-Copy has an impact on instance performance after the
switch to post copying mode. Also, once in post copy mode if the
migration processing fails then the instance will crash and need to
be rebooted.

Live Migration Strategy

If the migration is not completed but has copied most of the memory
then gradually increase the downtime allowed during the switch-over
until the migration completes or the configured maximum downtime is
reached.

Auto-converge will only be used if
:code:`live_migration_permit_auto_converge` is set to 'yes' and
:code:`live_migration_permit_post_copy` is set to no or unavailable
due to the version of libvirt and qemu in use.

If available, post-copy will be employed if needed to complete the
migration. Nova should allow the migration to run in pre-copy mode for
one iteration of memory page copying and thereafter it should start
monitoring the data remaining high water mark. If the data remaining
high water mark does not decrease by at least 10% on each iteration,
then it is a sign that live migration will not complete in suitable
timeframe. At this point Nova will automatically switch to post-copy
mode.

The auto-converge feature will be enabled if it is available and
post-copy is not available.

Live-migration-force-complete

The 'live-migration-force-complete' operation on an ongoing live
migration can be used to place the instance in suspended (paused
in libvirt parlance) state in order to allow the migration to
complete. It will be automatically resumed when the migration
completes and it switches to the target.

It is proposed that when the operator executes a
live-migration-force-complete operation the action taken will depend
on whether the post-copy feature is available.  If it is available,
i.e. :code:`live_migration_permit_post_copy` is set to 'yes' and it is
supported by the libvirt/qemu versions in use, a switch to post-copy
mode will be performed instead of suspending the instance. However,
if the live-migration-force-complete operation is performed before the
completion of the first iteration of memory pages copying it will defer
the switch to post-copy until the first iteration of memory page
copying is complete. The migration memory counters will be used to
determine if the first cycle of memory copying has been completed. This
can be achieved by comparing the memory processed and the memory total.
If the memory processed exceeds the memory total then at least one
complete cycle of memory copying has been completed.

An attempt to abort a live-migration after the switch to post-copy will
be rejected. Libvirt will reject an abort job API call if the migration
has switched to post-copy mode.  However when the driver issues the
request to switch to post-copy mode it  could update the migration
status to indicate that post-copy mode is in effect, i.e. update it
from 'running' to  'running (post-copy)'. The API method called by
'live-migration-abort' could be enhanced to check the migration status
to ensure it is not in post-copy mode. If the switch to post-copy
occurs after the check in the API but before the execution of the abort
by the driver then we will rely on libvirt to reject the abort request.

Note that live-migration-force-complete cannot be used to suspend an
instance once the switch to post-copy has been performed.  Note that
if post-copy feature is available then the
'live-migration-force-complete' operation will switch to post-copy
rather than attempt to suspend the instance so this shouldn't be an
issue, libvirt will reject an attempt to switch a migration operation
to post-copy if it is already in post-copy mode. If the
:code:`live_migration_permit_post_copy` flag is changed during the
live migration operation (i.e. it is set to mutable in the future, see
https://review.openstack.org/#/c/280851/) then there is a risk that
a 'live-migration-force-complete' operation will attempt to suspend
an instance that is in post-copy mode. This can be addressed by the
API method called by 'live-migration-force-complete' checking the
migration status as decribed above. If the switch to post-copy occurs
after the check in the API but before the execution of the suspend
by the driver then the instance will be suspended unnecessarily but
this should do no harm since the source instance will not be active
at after the switch to post-copy.

Alternatives
------------

One alternative is not doing this, leaving it up to operators to
manage live migrations.

An alternative would be to either enable or disable migration options
(such as post copy, auto-converge and the maximum down time setting)
via nova configuration flags. Enabling these options globally could
lead to customer complaints about instance performance and availability
because use of these features can potentially have a significant impact
on instance performance.

Another approach would be to provide the operator with APIs so they
could select and tune these settings before and during live migrations.
However it is not desirable to expose driver specifics to Nova API.

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

The impact of the live-migration-force-complete operation will change
if post-copy is available and enabled.

Performance Impact
------------------

No significant impact on Nova management application performance (i.e.
the compute manager). However the impact on the instance being migrated
will depend on the migration strategies utilized.

Other deployer impact
---------------------

Operators need to be careful when performing actions that impact
libvirt or qemu to ensure that they do not adversely impact on going
operations such as live migration.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
Paul Carlton (irc: paul-carlton2)

Other assignees:
None

Work Items
----------

* Update live migration start and monitor code.

Dependencies
============

See References below.

Testing
=======

Unit tests will be added as required.

Documentation Impact
====================

None

References
==========

Analysis of techniques for ensuring migration completion with KVM
https://www.berrange.com/posts/2016/05/12/analysis-of-techniques-for-ensuring-migration-completion-with-kvm/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced

