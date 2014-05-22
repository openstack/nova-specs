..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Attach All Local Disks During Rescue
====================================

https://blueprints.launchpad.net/nova/+spec/rescue-attach-all-disks

Attach all local disks during rescue to allow users access to all of
their data.


Problem description
===================

Currently only the root disk of the original instance is attached to the
rescue instance. If an instance is unbootable, then there is no way to
salvage data off ephemeral or other local disks.


Proposed change
===============

When an instance is placed into rescue, attach all local disks in addition
to the root disk already attached.

This explicitly does not attach any non-local disks, such as volumes. Any
attempt to rescue a volume-backed instance will continue being
rejected.


Alternatives
------------

None


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
  johannes.erdfelt

Other contributors:
  None


Work Items
----------

Implement feature for each virt driver.


Dependencies
============

None


Testing
=======

Each virt driver will be expected to test that all disks are attached
during rescue as part of the existing Nova tests.

Tempest will be updated to assert that the original disks are attached
during rescue.


Documentation Impact
====================

It should be documented that this is a behavior change when rescuing
instances.


References
==========

https://bugs.launchpad.net/nova/+bug/1223396
