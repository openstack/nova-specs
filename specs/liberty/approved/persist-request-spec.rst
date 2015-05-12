..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Persist RequestSpec object
==========================

https://blueprints.launchpad.net/nova/+spec/persist-request-spec

Persist the RequestSpec object used for scheduling an instance.


Problem description
===================

There are a few times that it would be useful to have the RequestSpec used for
originally scheduling an instance where it is not currently available, such as
during a resize/migrate.  In order to have later scheduling requests operate
under the same constraints as the original we should retain the RequestSpec for
these later scheduling calls.

Going forward with cells it will be necessary to store a RequestSpec before an
instance is created so that the API can return details on the instance before
it has been scheduled.

Use Cases
---------

* Operators/users want to move an instance through a migration or resize and
  want the destination to satisfy the same requirements as the source.

Project Priority
----------------

Priorities for Liberty have not yet been decided.


Proposed change
===============

A save() method will be added to the RequestSpec object.  This will store the
RequestSpec in the database.  Since this is also a part of the cells effort it
will be possible to stor in both the api and regular nova database.  Which
database it's stored in on save() will be determined by the context used.

Alternatives
------------

Parts of it could be put into the instance_extra table.  Because later this
will be persisted in the api database before scheduling and then moved to the
cell database after scheduling it is beneficial to just store it in a table
that can exist in both.

Data model impact
-----------------

A new database table will be added to both the api and cell database.  The
schema will match what is necessary for the RequestSpec object to be stored.
Since it is not yet implemented it's of little use to finalize the design here.

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

None here, but this will allow for resizes to be scheduled like the original
boot request.

Performance Impact
------------------

An additional database write will be incurred.

Other deployer impact
---------------------

Same as for users, nothing here but this opens up future changes.

Developer impact
----------------

None


Implementation
==============


Assignee(s)
-----------

Primary assignee:
  alaski

Work Items
----------

 * Add a new table to the api and cell/current database
 * Add the save() method to the RequestSpec object
 * Call the save() method in the code at the appropriate place


Dependencies
============

https://blueprints.launchpad.net/nova/+spec/request-spec-object


Testing
=======

New unit tests will be added.  This is not externally facing in a way that
Tempest can test.


Documentation Impact
====================

Devref documentation will be added explaining the existence of this data for
use in scheduling.


References
==========

None
