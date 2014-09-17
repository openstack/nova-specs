..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Change compute updates from periodic to on demand
=================================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/on-demand-compute-update

Currently, all compute nodes update status info in the DB on a periodic
basis (the period is currently 60 seconds). Given that the status of
the node only changes at specific points (mainly image
creation/destruction) this leads to significant DB overhead on a large
system. This BP changes the update mechanism to only update the DB when
a node state changes, specifically at node startup, instance creation
and instance destruction.

Problem description
===================

The status information about compute nodes is updated into the DB on
a periodic basis.  This means that every compute node in the system
updates a row in the DB once every 60 seconds (the default period for
this update).  This is unnecessary and a scalability problem given that
the status info is mostly static and doesn't change very often, mainly
it changes when an instance is created or destroyed.

Proposed change
===============

Compute node only sends an update if its status changes.  On a periodic
interval (using the current default period of 60 seconds) the compute
node will compare its status with the status saved from the last update.
Only if the state or claims have changed will the DB be updated.

The advantage to this method is that it should significantly cut down
on the number of DB updates while changing almost nothing about the way
the system currently works, compute node changes will still take 60
seconds before they are updated but any change, for any reason, will
ultimately be reported.

One potential issue with this is a possible sensitivity concern, updates
shouldn't be constantly sent if, for example, steady state system activity
causes something like RAM usage to change slightly.  Some experiments will
have to be run to decide if adding in a sensitivity control for certain
status metrics is needed.  This can be a follow on optimization, if it's
necessary, since this design is no worse than the current mechanism.

Alternatives
------------

Another idea would be to only update the DB at certain well defined events.
The update code would only be called at system start up, instance creation
and instance deletion.  This would reduce the latency for status updates
(the DB is modified as soon as the system state changes) but it suffers
from some disadvantages:

1)  Finding all of the appropriate events to record a status change.  Are
statup/creation/destruction the only places where the system state changes,
maybe there are other events that should be tracked.

2)  Future changes could add new events that change status and recognizing
that an update is needed is an easy mistake to miss.

3)  Status could change unknown to the nova code, imagine something like a
hot plug add of memory.

Data model impact
-----------------

There is no change to the data that is being stored in the DB, all of the
current fields are stored exactly as before, this BP is just changing the
frequency at which those fields are updated.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

As measured by DB updates this change will clearly cause no more DB updates
than the current technique and, assuming instances are created on a node
at a rate of less then one every 60 seconds, should cause much fewer DB
updates.

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
  Don Dugger <donald.d.dugger@intel.com>

Other contributors:

Work Items
----------

Change should be fairly simple, change the current update code to only
update the DB if a 'state_modified' routine returns true.  The
'state_modified' routine returns false if the current state matches the
last recorded state.  Otherwise, it saves the current state as the last
recorded state and returns true.

The 'state_modified' routine maintains an in memory copy of the current
status of the compute node.  This copy of the state is compared with the
current state and the update to the DB only happens if the copy and the
current state differ.  Note that the in memory copy is initialized to
zero values on node startup so that the first periodic update call will
find a miss match between the two states and the DB will be updated.

Based upon experiments it has been determined that a simple comparison
of the entire current vs. the saved state is sufficient.  If, in the
future, more rapidly changing data that shouldn't be stored in the DB
is added to the compute node state then 'state_modified' can be easily
changed to ignore such data that isn't needed in the DB.

Dependencies
============

None.


Testing
=======

A unit test will be created to make sure that the DB is updated when the
compute node status changes and is not updated when the status doesn't
change.


Documentation Impact
====================

Section 5 of the Associate Training Guide

http://docs.openstack.org/training-guides/content/associate-computer-node.html

is slightly incorrect and should be fixed.  It currently says "All compute
nodes (also known as hosts in terms of OpenStack) periodically publish their
status, resources available and hardware capabilities to nova-scheduler
through the queue."  This should be modified to reflect that the status is
updated in the DB which is then queried by the scheduler.  (Note this is a
generic fix that is really unrelated to this blueprint.)


References
==========

None.
