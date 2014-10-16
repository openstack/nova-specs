..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Query lock status of instance
==================================================

https://blueprints.launchpad.net/nova/+spec/get-lock-status-of-instance

Currently we only support locking/unlocking an instance but we are not able
to query whether the instance is locked or not.
This proposal is to add the lock status to the detailed view of an instance.

Problem description
===================

We are able to lock/unlock an instance through nova API now.
But we don't return the lock status of the servers.

Use Cases
---------
This is useful when user to know status of an instance

Project Priority
-----------------
None

Proposed change
===============

Display the lock status as part of the detailed view of an instance
(that is, 'nova show')

Alternatives
------------

The lock status can be identified by attempting to lock the instance,
but if the instance is not already locked this has the side-effect of
locking it. If another process simultaneously tries to query the lock
status in the same fashion, it may get a false positive.
Equally if another process tries to delete the instance while it is
locked due to a query, it will fail when it shouldn't.

Data model impact
-----------------

None

REST API impact
---------------

Add following output to the response body of
GET /v2/45210fba73d24dd681dc5c292c6b1e7f/
servers/a9dd1fd6-27fb-4128-92e6-93bcab085a98

Following lock info will be added in addition to
existing output info.

+---------------+---------------------+--------------------------------------+
| Parameter     |  Type               | Description                          |
+===============+=====================+======================================+
| locked        | boolean             | whether the instance is locked       |
+---------------+---------------------+--------------------------------------+
| locked_by     | string              | User locked the instance, current    |
|               |                     | valid value are 'admin' and 'owner'  |
+---------------+---------------------+--------------------------------------+

If the locked is True, following info will be added into output:

+---------------+-----------------------------------------+
| Parameter     | Data                                    |
+===============+=========================================+
| locked        | True                                    |
+---------------+-----------------------------------------+
| locked_by     | 'admin'                                 |
+---------------+-----------------------------------------+

If the locked is false, this will return following info:

+---------------+-----------------------------------------+
| Parameter     | Data                                    |
+===============+=========================================+
| locked        | False                                   |
+---------------+-----------------------------------------+
| locked_by     | None                                    |
+---------------+-----------------------------------------+

Both v2 and v3 API will be affected.

* In v2 API, extension os-server-locked-status will be added to
  advertise the extra information.
  alias: os-server-locked-status
  name: ServerLockStatus
  namespace: http://docs.openstack.org/compute/ext/server_locked_status/api/v2
  When the new extension "os-server-locked-status" is loaded,
  2 new fields 'locked', 'locked_by' will be added to
  the os-hypervisor API.

* In v3 API, locked information will be directly added to extended_status.py
  since locked_by is already there.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

This will allow user to query the lock status of an instance.

python-novaclient will be updated in order to show the lock status
in the 'nova show' commands.

If there is no lock status info in the output from older v2 API,
the new python-novaclient will exclude the lock status,
locked_by fields.

Performance Impact
------------------

None

Other deployer impact
---------------------

None.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jichenjc

Work Items
----------

Nova v2 API update.
Nova v3 API update.
Tempest cases update for locked field check.

Dependencies
============

None


Testing
=======

Tempest cases will be added, especially the
lock/unlock related cases will check through the APIs to be added,
e.g. the new lock status fields will be mandatory required fields.

Documentation Impact
====================

API document will be updated in order to list the lock status.

References
==========

None
