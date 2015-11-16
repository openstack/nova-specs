..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Scheduling interaction for cells
================================

https://blueprints.launchpad.net/nova/+spec/cells-scheduling-interaction

In order to schedule instance builds to compute hosts Nova and the scheduler
will need to take into account that hosts are grouped into cells.  It is not
necessary that this is apparent when Nova is requesting a placement decision.


Problem description
===================

In order to partition Nova into cells the scheduler will need to be involved
earlier in the build process.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need to have flexible
  scheduling that can make decisions on cells and hosts.


Proposed change
===============

The scheduler will be queried at the api level so that it knows which cell to
pass the build to.  The instance table exists in a cell and not in the api
database, so to create an instance we will first need to know which cell to
create it in.

The scheduler will continue to return a (host, node) tuple and the calling
service will look up the host in a mapping table to determine which cell it is
in.  This means the current select_destinations interface will not need to
change.  Querying the scheduler will take place after the API has returned a
response so the most reasonable thing to do is pass the build request to a
conductor operating outside of any cell.  The conductor will call the scheduler
and then create the instance in the cell and pass the build request to it.

Rescheduling will still take place within a cell via the normal
compute->conductor loop, using the conductors within the cell.  Adding
rescheduling at a cell level will be a later effort.

Information about cells will need to be fed into the scheduler in order for it
to account for that during its placement decisions, but that is outside the
scope of this spec.


Alternatives
------------

We could query the scheduler at two points like in cellsv1.  This creates more
deployment complexity and creates an unnecessary coupling between the
architecture of Nova and the scheduler.

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

Nova-conductor will need to be deployed for use by nova-api.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alaski

Other contributors:
  None

Work Items
----------

* Add a conductor method to call the scheduler and then handle the latter half
  of what the api currently does for a build request(create instance in db and
  cast to the cell conductor).

* Update the conductor build_instances interface to take a scheduling decision
  and not call the scheduler if it's provided.  This allows for bypassing
  scheduling when it comes from the api conductor but still call the scheduler
  when a compute requests a reschedule.

* Update devstack to spin up a conductor for use by the nova-api service.


Dependencies
============

None


Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice.  At some point we will want to look at how to test multiple cells or
potentially exposing the concept of a cell in the API and we will tackle
testing requirements then.


Documentation Impact
====================

Documentation will be written describing the flow of an instance build and how
and where scheduling decisions are made.


References
==========

``https://etherpad.openstack.org/p/kilo-nova-cells``
``https://etherpad.openstack.org/p/nova-cells-scheduling-requirements``
