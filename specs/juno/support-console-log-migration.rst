..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Support Console Log migration during Live-migration
===================================================

https://blueprints.launchpad.net/nova/+spec/support-console-log-migration

Implement console log migration during live-migration in the libvirt driver


Problem description
===================

Currently, in libvirt driver with a kvm hypervisor, console output is written
to console.log. Nova responds to a get-console-log request with the contents
of this file and this information is useful for debugging issues during boot
process. However, during a live-migration the contents of the file in the
source node is discarded.

There are two issues which play a role in this.

* The new kvm process in the destination would have already started using
  an empty console log.

* While the migration progresses the VM in the source node will continue
  to write to the console log.

Proposed change
===============

We propose the following in this blueprint to solve this issue without
depending on kvm.

* Require that VIR_MIGRATE_UNDEFINE_SOURCE is not set. Instead wait for the
  condition that the instance is shutoff at the source.

* During post-live-migration copy the console log be from source node and save
  in the destination node as console.log.1. If log rotation is implemented,
  all the rotated files need to be rotated once.

* Change get-console-log function such that console.log and console.log.1 are
  merged in the response (within the MAX_CONSOLE_BYTES limit). It log rotation
  is implemented then the function needs to read as many files as it takes to
  fill up the MAX_CONSOLE_BYTES limit.

* The source VM would get undefined by the periodic task once the database is
  updated with the new hostname.

Alternatives
------------

* Change qemu to move the file content
* Stream console output to a shared location
* If spec/libvirt-serial-console is implemented we can leverage on that
  mechanism and trigger a rotation and move it to destination.


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

* There's a brief window between the time the VM is activated in the
  destination and before post-live-migration is completed. Any nova
  console-log requests will return almost empty content during this window.

Other deployer impact
---------------------

* If people are using VIR_MIGRATE_UNDEFINE_SOURCE then they need to remove this
  option to get this feature. If this flag exists we will fallback to not
  having the console log migrated.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  parthipan

Work Items
----------

* Change live-migration to wait for shutoff state if flag
  VIR_MIGRATE_UNDEFINE_SOURCE is not set.
* Change get_console_log to handle rotated log files
* Implement console log migration during post-live-migration

Dependencies
============
None

Testing
=======

Tempest tests should be added to test that the console logs are merged in the
response and catch other corner-cases.

Documentation Impact
====================

We expect to have the following documentation changes:

* The migration flag changes to get console logs migrated
* Expected empty console log during the VM offline period in the final stages
  of the migration

References
==========

* https://bugs.launchpad.net/nova/+bug/1203193
