..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Cleanup 'scheduled_at' column in nova instances table
=====================================================

https://blueprints.launchpad.net/nova/+spec/cleanup-scheduled-at

The 'scheduled_at' field is a part of the Nova instances table
Currently, the 'scheduled_at' field is no longer updated by the
Nova scheduler, instead the 'launched_at' field is used.
The 'scheduled_at' column is now redundant and should
be removed as a part of DB clean up.

Problem description
===================

The 'scheduled_at' column in the nova instances table is now
redundant. This field was erstwhile used by the scheduler to denote
the time of the instance scheduling. The commit that removed it is:
https://review.openstack.org/#/c/143725/

Now since all of the basic VM lifecyle operations go through the
scheduler, the 'launched_at' field is sufficient for the above
mentioned scenario.

This is a nova DB cleanup effort to get removed the 'scheduled_at'
column from the instances table and ensure backward compatibility.

Use Cases
----------

This is a cleanup effort on the instances table.


Project Priority
-----------------

This is a refactoring effort to make nova code cleaner.


Proposed change
===============
Estimated changes are going to be in the following places:
* Remove the sqlalchemy initializations for the 'scheduled_at' field

* Remove all unit tests, involving this field.

* Ensure that the NovaObjects adapt to this change for handling
  migration related issues.


Alternatives
------------
Continue to live with dormant code in nova.


Data model impact
-----------------
The 'scheduled_at' column can be dropped from the Instances table since
there appears to be no code, that updates it currently.


REST API impact
---------------

None

Security impact
---------------

None.

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

* Sudipta Biswas sbiswas7


Work Items
----------

1. Drop the column for 'scheduled_at' from Sqlalchemy model.
2. Add migration to drop the column from the instances table.
3. Change the instances object module for migration related issues.


Dependencies
============

None


Testing
=======

The changes will be exercised through the existing CI.

Documentation Impact
====================

None


References
==========

