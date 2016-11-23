..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Resource Providers - Scheduler Filters in DB
============================================

https://blueprints.launchpad.net/nova/+spec/resource-providers-scheduler-db-filters

This blueprint aims to have the scheduler calling the placement API for getting
the list of resource providers that could allow to pre-filter compute nodes
from evaluation during `select_destinations()`.

Problem description
===================

Currently, on each call to the scheduler's `select_destinations()` RPC method,
the scheduler retrieves a list of `ComputeNode` objects, one object for *every*
compute node in the entire deployment. The scheduler constructs a set of
`nova.scheduler.host_manager.HostState` objects, one for each compute node.
Once the host state objects are constructed, the scheduler loops through them,
passing the host state object to the collection of
`nova.scheduler.filters.Filter` objects that are enabled for the deployment.

Many of these scheduler filters do nothing more than calculate the amount of a
particular resource that a compute node has available to it and return `False`
if the amount requested is greater than the available amount of that type of
resource.

Having to return all compute node records in the entire deployment is
extremely wasteful and this inefficiency gets worse the larger the deployment
is. The filter loop is essentially implementing a `SQL` `WHERE` clause, but in
Python instead of a more efficient database query.

Use Cases
----------

As a CERN user, I don't want to wait for the nova-scheduler to process 10K+
compute nodes to find a host on which to build my server.

Proposed change
===============

We propose to winnow the set of compute nodes the FilterScheduler evaluates by
only returning the compute node resource providers that meet requested resource
constraints.  This will dramatically reduce the amount of compute node records
that need to be pulled from the database on every call to
`select_destinations()`.  Instead of doing that database call, we would rather
make a HTTP call to the placement API on a specific REST resource with a
request that would return the list of resource providers' UUIDs that would
match requested resources and traits criterias based on the original
RequestSpec object.

This blueprint doesn't aim to change the CachingScheduler driver, which
overrides the method that fetches the list of hosts. That means the
CachingScheduler will *not* call the placement API.

Alternatives
------------

We could create an entirely new scheduler driver instead of modifying the
`FilterScheduler`. Jay is not really in favor of this approach because it
introduces more complexity to the system than directly using the placement API
for that purpose.

Data model impact
-----------------

None.

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

Jay built a benchmarking harness_ that demonstrates that the more compute nodes
in the deployment, the greater the gains are from doing filtering on the
database side versus doing the filtering on the Python side and returning a
record for each compute node in the system. That is directly reading the DB but
we assume the extra HTTP penalty as something not really impactful.

.. _harness: http://github.com/jaypipes/placement-bench

Other deployer impact
---------------------

In Pike, the CoreFilter, RAMFilter and DiskFilter scheduler filters will be
removed from the list of default scheduler filters. Of course, for existing
deployments they will continue to have those filters in their list of enabled
filters. We will log a warning saying those filters are now redundant and can
safely be removed from the nova.conf file.

For deployers who disabled the RAMFilter, DiskFilter or CoreFilter, they may
manually want to set the allocation ratio for the appropriate inventory records
to a very large value to simulate not accounting for that particular resource
class in scheduling decisions. For instance, if a deployer disabled the
DiskFilter in their deployment because they don't care about disk usage, they
would set the `allocation_ratio` to 10000.0 for each inventory record of
`DISK_GB` resource class for all compute nodes in their deployment via the new
placement REST API.

These changes are designed to be introduced into Nova in a way that
"self-heals". In Newton, the placement REST API was introduced and the
nova-computes would begin writing inventory and allocation records to the
placement API for their VCPU, MEMORY_MB, and DISK_GB resources. If the
placement service was not set up, the nova-compute logged a warning about the
placement service needing to be started and a new service endpoint created in
Keystone so that the nova-computes could find the placement API.

In Ocata, the placement service is required, however we will build a sort of
self-healing process into the new behaviour of the scheduler calling to the
placement API to winnow the set of compute hosts that are acted upon. If the
placement service has been set up and the deployer upgrades her control plane
to Ocata and restarts her nova-scheduler services, the new Ocata scheduler will
attempt to contact the placement service to get a list of resource providers
(compute hosts) that meet a set of requested resource amounts.

Initially, since no nova-computes had successfully run through their periodic
audit interval, the placement database would be empty and thus the request from
the scheduler to the placement API for resource providers would return an empty
list. We will place code into the scheduler that, upon seeing an empty list of
resource providers returned from the placement API, will fall back to the
legacy behaviour of calling ComputeNodeList.get_all(). This will allow the old
scheduler behaviour to take over in between the time when the new placement
service is brought online and when nova-compute nodes are restarted (triggering
a fresh call out to the placement service, which can now be contacted, and
populating the placement DB with records).

As restarts (or upgrades+restarts) of the nova-computes are rolled out, the
placement database will begin to fill up with allocation and inventory
information. There may be a short period of time while the scheduler receives a
smaller-than-accurate set of resource providers that meet the requested
resource amounts. This may result in a few retry events but under no
circumstances should there be a NoValidHost returned since the scheduler will
fall back to its old ComputeNodeList.get_all() behaviour.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  bauzas

Other contributors:
  cdent
  jaypipes

Work Items
----------

* Add a new method that accepts a `nova.objects.RequestSpec` object and
  transform that object into a list of resource and traits criteria
* Provide a method to call the placement API for getting the list of
  resource providers that match those criteria.
* Translate that list of resource providers into a list of hosts and replace
  the existing DB call by the HTTP call for the FilterScheduler driver only.
* Leave NUMA and PCI device filters on the Python side of the scheduler for now
  until the `nested-resource-providers` blueprint is completed. We can have
  separate blueprints for handling NUMA and PCI resources via filters on the
  DB side.


Dependencies
============

The following blueprints are dependencies for this work:

* `resource-providers-get-by-request`

Testing
=======

Existing functional tests should adequately validate that swapping out DB-side
filtering for Python-side filtering of RAM, vCPU and local disk produces no
different scheduling results from `select_destinations()` calls.

Documentation Impact
====================

Make sure we document the redundant filter log warnings and how to remedy as
well as document how to use the `allocation_ratio` to simulate disabled
filters.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
   * - Ocata
     - Re-proposed
