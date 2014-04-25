..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
 Create Scheduler Python Library
=================================

https://blueprints.launchpad.net/nova/+spec/scheduler-lib

We want to split out nova-scheduler into gantt. To do this, we need to
isolate the scheduler from the rest of nova.

In this blueprint, we need to define in a clear library all accesses to the
Scheduler code or data (compute_nodes DB table) from other Nova bits (conductor
and ResourceTracker).

No scheduler bits of code will be impacted by this blueprint, the change is
only affecting other Nova components and provides a new module for Scheduler.


Problem description
===================

To create the gantt project we need to introduce a much cleaner "seam" between
nova-scheduler and the rest of Nova. This will allow the existing
nova-scheduler code to remain in Nova, while at the same time giving us a clean
way to test the new gantt scheduler.

This split will also be useful to allow efforts such as the no-db-scheduler
to evolve in a way that allows multiple patterns to co-exist, thus encouraging
more innovation, while keeping the existing stable and pluggable solution.

This change in approach for the gantt project was agreed at the Nova
Icehouse mid-cycle meetup:
https://etherpad.openstack.org/p/icehouse-external-scheduler


Proposed change
===============

The basic points to note about this change are:

* No change in behaviour. This is just a refactor.

* Produce a scheduler lib, a prototype interface for python-ganttclient

* Assume select_destinations will be the single call to the scheduler from nova
  by the end of Juno. This is the first bit of the interface.

* Move all accesses to the compute_nodes table behind the new scheduler lib.
  This is the second part of the interface.

Here we need to define a line in the sand by exposing a Scheduler interface
that Nova can use (mostly the ResourceTracker) for updating stats to the
Scheduler instead of directly calling DB for updating compute_nodes table.

In addition, calls to the Scheduler RPC API will now go through the scheduler
lib, so as to have all current interfaces going to the same module .But given
the above assumptions, we need only do this for select_destinations.

As said, all interfaces will go into a single module (nova.scheduler.client).

The current interfaces we identify are ::

    select_destinations(context, request_spec, filter_properties)
        """Returns a list of resources based on request criterias.
        """
        :param context: security context
        :param request_spec: specification of requested resources
        :type requested_resources: dict
        :param filter_properties: scheduler hints and instance spec

    update_resource_stats(context, name, stats)
        """Update Scheduler state for a set of resources."""
        :param context: context
        :param name: name, as returned by select_destinations
        :type name: tuple or string
        :param stats: dict of stats to send to scheduler

If we still need to support the node and host distinction in nova, this can be
done by passing a tuple (host, node) as the resource name, instead of a string.

In a similar way, resource_request, will, for now, contain both
request_spec and filter_properties in a generic dict.

The stats parameter is planned to be 1:1 matched with conductor/DB
compute_node_update() (or create()) values parameter, ie. a dict matching
compute_nodes fields in a JSON way.


This proposal is just drawing a line in the sand. In the future we will need to
make more invasive changes that are not triggered for this blueprint, such as:

* Adding more data into compute_nodes, so the scheduler doesn't need access to
  any other Nova objects. For example, filters that need to know about the AZ,
  that could be included in the stats that are added into compute_nodes

* Having a data collection plugin system, so data is extracted and sent from
  the resource tracker to the scheduler in a format that the matches the
  filters and/or weights on the receiving end. Also ensuring, only the data
  that is required for your particular set of filters and/or weights are sent.
  This is very similar to the extensible resource tracker blueprint or could
  leverage it.

* Proxying select_destinations by another method for having it less Nova
  specific and allowing in the future a python-ganttclient client to use it.


Alternatives
------------

The other alternative would be to fork the scheduler code at a point in time to
a separate Git repository, do the necessary changes within the code (unittests,
imports). However neither syncing changes or having a code freeze on
nova-scheduler seem like the best approach.

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

None. This effort is just refactoring, not splitting now into a separate
repository.


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

Ideally:

* All new operations will be scheduled using select_destinations.

* ResourceTracker will only take use of update_resource_stats.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Other contributors:
  None

Work Items
----------

* Create scheduler lib for calls to select_resources

* Add update_resource_stats to lib


Dependencies
============

* https://review.openstack.org/#/c/86988/
  (bp/remove-cast-to-schedule-run-instance)


Testing
=======

Covered by existing tempest tests and CIs.


Documentation Impact
====================

None


References
==========

* Other effort related to RT using objects is not mandatory for this blueprint
  but both efforts can mutally benefit
  https://blueprints.launchpad.net/nova/+spec/make-resource-tracker-use-objects
  (pmurray)

* Cast to scheduler for running instances is mandatory for the Gantt forklift
  but not for this blueprint
  https://blueprints.launchpad.net/nova/+spec/remove-cast-to-schedule-run-instance
  (alaski)

* https://etherpad.openstack.org/p/icehouse-external-scheduler

* http://eavesdrop.openstack.org/meetings/gantt/2014/gantt.2014-03-18-15.00.html
