..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Scheduling interaction for cells
================================

https://blueprints.launchpad.net/nova/+spec/cells-scheduling-interaction

In order to schedule instance builds to compute hosts Nova and the scheduler
will need to take into account that hosts are grouped into cells. It is not
necessary that this is apparent when Nova is requesting a placement decision.


Problem description
===================

In order to partition Nova into cells the scheduler will need to be involved
earlier in the build process.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons. When partitioned, we need to have flexible
  api level scheduling that can make decisions on cells and hosts.


Proposed change
===============

The scheduler will be queried by Nova at the api level so that it knows which
cell to pass the build to. The instance table exists in a cell and not in the
api database, so to create an instance we will first need to know which cell to
create it in.

The scheduler will continue to return a (host, node) tuple and the calling
service will look up the host in a mapping table to determine which cell it is
in. This means the current select_destinations interface will not need to
change. Querying the scheduler will take place after the API has returned a
response so the most reasonable thing to do is pass the build request to a
conductor operating outside of any cell. The conductor will call the scheduler
and then create the instance in the cell and pass the build request to it.

While much of Nova is being split between being api-level or cell-level the
scheduler remains outside of either distinction. It can be thought of as a
separate service in the same way that Cinder/Neutron are. As a result the
scheduler will require knowledge of all hosts in all cells. This is different
from the cellsv1 architecture and may be a surprise for those familiar with
that setup. A separate effort can address scalability for the scheduler and the
potential for partitioning it along some boundary, which may be a cell.

Because the existing build_instances conductor method assumes that the instance
already exists within a cell database and makes some assumptions about cleaning
up resources on failure we will not complicate that method with an alternate
path. Instead a new conductor method will be added which can take the task of
querying the scheduler and then creating the instance and associated resources
within the cell indicated by the scheduler.

The new boot workflow would look like the following:

 - nova-api creates and persists a BuildRequest object, not an Instance.
 - Cast to the api level conductor to execute the new method proposed here. The
   api level conductor is whatever is configured in DEFAULT/transport_url.
   - Conductor will call the scheduler once.
   - Conductor will create the instance in the proper cell
   - Conductor will cast to the proper nova-compute to continue the build
     process. This cast will be the same as what is currently done in the
     conductor build_instances method.
   - In the event of a reschedulable build failure nova-compute will cast to a
     cell conductor to execute the current build_instances method just as it's
     currently done.

Rescheduling will still take place within a cell via the normal
compute->conductor loop, using the conductors within the cell. Adding
rescheduling at a cell level will be a later effort.

Information about cells will need to be fed into the scheduler in order for it
to account for that during its reschedule/migration placement decisions, but
that is outside the scope of this spec.


Alternatives
------------

We could query the scheduler at two points like in cellsv1. This creates more
deployment complexity and creates an unnecessary coupling between the
architecture of Nova and the scheduler.

A reschedule could recreate a BuildRequest object, delete the instance and any
associated resources in a cell, and then let the scheduler pick a new host in
any cell. However there is a fair bit of complexity in doing that cleanup and
resource tracking and I believe that this is an effort best left for a later
time. It should also be noted that any time a build crosses a cell boundary
there are potential races with deletion code so it should be done as little as
possible.

Rather than requiring an api level set of conductor nodes nova-api could
communicate with the conductors within a cell thus simplifying deployment. This
is probably worth doing for the single cell case so another spec will propose
doing this.

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

* Add a conductor method to call the scheduler, create an instance in the db of
  the cell scheduled to, then cast to the selected compute host to proceed with
  the build.

* Update the compute api to not create the instance in the db during a build
  request, and change it to cast to the new scheduler method.

* Ensure devstack is configured to that nova-api shares the cell level
  conductors. This makes the single cell setup as simple as possible. A later
  effort can investigate making this configurable in devstack for multiple cell
  setups.


Dependencies
============

None


Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice. At some point we will want to look at how to test multiple cells or
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


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - Re-proposed; partially implemented.
   * - Newton
     - Re-proposed; partially implemented.
   * - Ocata
     - Re-proposed.
