..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Isolate Scheduler Database for Aggregates
=========================================

https://blueprints.launchpad.net/nova/+spec/isolate-scheduler-db

We want to split out nova-scheduler into gantt. To do this, this blueprint is
the second stage after scheduler-lib split. These two blueprints are
independent however.

In this blueprint, we need to isolate all accesses to the database that
Scheduler is doing and refactor code (manager, filters,
weighters) so that scheduler is only internally accessing scheduler-related
tables or resources.

Note : this spec is only targeting changes to the Aggregates-related filters.


Problem description
===================

When making decisions involving information about an aggregate, the scheduler
accesses the Nova DB's aggregates table either directly or indirectly via
nova.objects.AggregateList. In order for the split of the scheduler to be
clean, any access by the Nova scheduler to tables that will stay in the Nova DB
(i.e. aggregates table) must be refactored so that the scheduler has an API
method that allows nova-conductor or other services to update the scheduler's
view of aggregate information.

Below is the summary of all filters impacted by that proposal

  * AggregateImagePropertiesIsolation,
  * AggregateInstanceExtraSpecsFilter,
  * AggregateMultiTenancyIsolation,
  * AvailabilityZoneFilter,
  * AggregateCoreFilter (calls n.objects.aggregate.AggregateList.get_by_host)
  * AggregateRamFilter (calls n.objects.aggregate.AggregateList.get_by_host)
  * AggregateTypeAffinityFilter (calls
    n.objects.aggregate.AggregateList.get_by_host)


Use Cases
----------

N/A, this is a refactoring effort.

Project Priority
-----------------

This blueprint is part of the 'scheduler' refactoring effort identified as a
priority for Kilo.


Proposed change
===============

The strategy will consist in updating the scheduler each time a change comes
to an Aggregate (adding or removing a host or changing metadata).

As the current Scheduler design scales with the number of requests (for each
request, a new HostState object is generated using get_all_host_states method
in the HostManager module), we can't hardly ask the Scheduler to update a DB
each time a new compute comes in an aggregate. It would then create a new
paradigm where the Scheduler would scale with the number of computes added
to aggregates and which could create some race conditions.

Instead, we propose to create an in-memory view of all the aggregates in the
Scheduler which would be populated when the scheduler is starting by calling
the Nova Aggregates API and leave the filters access these objects instead of
calling by themselves the Nova aggregates DB table indirectly.
Updates to the Aggregates which are done using the
``nova.compute.api.AggregateAPI`` will also call the Scheduler RPC API to ask
the Scheduler to update the relevant view.


Alternatives
------------

Obviously, the main concern is about duplicating aggregates information and the
potential race conditions that can occur. In our humble opinion, duplicating
the information in the Scheduler memory is a small price to pay for making sure
that the Scheduler could one day live by its own.

A corollary would be to consider that if duplication is not good, then the
Scheduler should fully *own* the Aggregates table. Consequently, all the calls
in the nova.compute.api.AggregatesAPI would be treated as "external" calls and
once the Scheduler would be splitted out, the Aggregates would no longer reside
in Nova.

Another mid-term approach would be to envisage a second service for the
Scheduler (like nova-scheduler-updater - still very bad at naming...) which
would accept RPC API calls and write the Scheduler DB separatly from the
nova-scheduler service which would actually be treated like a "nova-api"-ish
thing because we could consider that the warmup period for the Scheduler for
populating the relative HostState informations could be problematic and we
could prefer to persist all these objects into the Scheduler DB.

Finally, we definitely are against calling Aggregates API from the Scheduler
each time a filter needs information because it doesn't scale.


Data model impact
-----------------

None, we only create an in-memory object which won't be persisted.


REST API impact
---------------

None

Security impact
---------------

None


Notifications impact
--------------------

None. The atomicity of the operation (adding/modifying an Aggregate) remains
identical, we don't want to add 2 notifications for the same operation.


Other end user impact
---------------------

None

Performance Impact
------------------

Accesses should be done against a memory object instead of accessing the DB,
so we definitely expect better access times and scalability should be improved.


Other deployer impact
---------------------

None


Developer impact
----------------

Ideally:

* Filters should no longer place calls to other bits of code except Scheduler.
  This will be done by modifying Scheduler component to proxy conductor calls
  to a Singleton which will refuse anything but scheduler-related objects.
  See footnote [1] as example. As said above, we will still provide a failback
  mode for Kilo release in order to have compatibility with N-1 release.



Implementation
==============


Here, we propose to set the collection of ``nova.objects.Aggregate`` objects
by calling ``nova.objects.AggregateList.get_all()`` during the initialization
of ``nova.scheduler.host_state.HostManager`` as an attribute to HostManager.

In order to access the list of aggregates than an host belongs to, we plan
to add a list of references to the corresponding Aggregate objects as an
extra attribute of ``nova.scheduler.host_state.HostState`` during that
initialization phase.


The second phase would consist to provide updates to that caching system
by amending the Scheduler RPC API by adding a new
update_aggregate() method, which nova.scheduler.client would expose it too.

The update_aggregate() method would take only one argument, a
``nova.objects.Aggregate`` object and would properly update the
``HostManager.aggregates`` attribute so that the ``HostState.aggregates``
reference would implicetely be updated.

Every time that an Aggregate would be updated, we would hook the existing
nova.compute.api.AggregateAPI class and each method in it by adding another
call to nova.scheduler.client which would RPC fanout the call to all
nova-scheduler services.

Once all of that would be done, filters would just have to look into
HostState.aggregates to access all aggregate information (incl. metadata)
related to the aggregates the host belongs to.


Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Other contributors:
  None


Work Items
----------

* Instanciate HostManager.aggregates and HostState.aggregates
  when scheduler is starting

* Add update_aggregate() method to the Scheduler RPC API and bump a version

* Create nova.scheduler.client method for update_aggregate()

* Modify nova.api.AggregateAPI methods to call the scheduler client method

* Modify filters so they can look to HostState

* Modify scheduler entrypoint to block conductor accesses to Aggregates
  (once Lxxx release development will be open)


Dependencies
============

None


Testing
=======

Covered by existing tempest tests and CIs.


Documentation Impact
====================

None


References
==========

* https://etherpad.openstack.org/p/icehouse-external-scheduler

* http://eavesdrop.openstack.org/meetings/gantt/2014/gantt.2014-03-18-15.00.html

[1] http://git.openstack.org/cgit/openstack/nova/commit/?id=e5cbbcfc6a5fa31565d21e6c0ea260faca3b253d
