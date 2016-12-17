.. _ocata-priorities:

========================
Ocata Project Priorities
========================

List of efforts the Nova development team is prioritizing for reviews in the
Ocata release (in no particular order).

+-------------------------------------------+-----------------------+
| Priority                                  | Primary Contacts      |
+===========================================+=======================+
| `Cells V2`_                               | `Dan Smith`_          |
|                                           | `Melanie Witt`_       |
+-------------------------------------------+-----------------------+
| `Resource Providers`_                     | `Jay Pipes`_          |
|                                           | `Sylvain Bauza`_      |
|                                           | `Chris Dent`_         |
+-------------------------------------------+-----------------------+
| `API Improvements`_                       | `Alex Xu`_            |
|                                           | `Kevin Zheng`_        |
+-------------------------------------------+-----------------------+
| `Network Aware Scheduling`_               | `John Garbutt`_       |
+-------------------------------------------+-----------------------+

.. _Dan Smith: https://launchpad.net/~danms
.. _Melanie Witt: https://launchpad.net/~melwitt
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Sylvain Bauza: https://launchpad.net/~sylvain-bauza
.. _Chris Dent: https://launchpad.net/~cdent
.. _Alex Xu: https://launchpad.net/~xuhj
.. _Kevin Zheng: https://launchpad.net/~zhengzhenyu
.. _John Garbutt: https://launchpad.net/~johngarbutt

Cells v2
--------

A single cells v2 deployment was made possible in the Newton release, and CI
testing was added, but cells v2 was still optional as of Newton.

In Ocata, the goal is to support multiple cells v2 cells in a deployment. There
are several priority efforts to get us there.

* `Scheduler interaction for cells v2`_: This moves instance creation to the
  nova-conductor service so that when the scheduler picks a host, the instance
  is built in a specific cell. There are no plans in Ocata to support rebuilds
  or other instance move operations, i.e. migrations, between cells.
* `Quotas in the API cell`_: The quotas tables have moved to the API database
  but we want to avoid an 'up-call' from the compute cells to the API when
  handling quota commits and rollbacks. With cells v2 we have an opportunity to
  rethink how Nova supports counting resources and tracking quota, so this
  effort aims to move quota handling to a more simplified solution which is
  more eventually consistent and avoids invalid over-quota failures by design.
* Support a simple python merge operation when sorting and/or filtering a list
  of instances across multiple cells. Long-term this should be handled by
  `Searchlight`_ but for Ocata we will have a simple but albeit less performant
  solution.
* Continuous integration testing with cells v2 enabled by default. We aim to
  make cells v2 required in Ocata deployments, and to get there we need to have
  the community CI jobs running with cells v2. This will require changes to
  grenade for upgrade testing and also testing multiple cells v2 cells with the
  multinode job.

.. _Scheduler interaction for cells v2: ../specs/ocata/approved/cells-scheduling-interaction.html
.. _Quotas in the API cell: ../specs/ocata/approved/cells-count-resources-to-check-quota-in-api.html
.. _Searchlight: http://docs.openstack.org/developer/searchlight/

Resource Providers
------------------

* `Placement / Scheduler interaction`_: The Nova Filter Scheduler will make
  requests to the placement API for simple compute node resources such as VCPU,
  RAM and disk. This allows the scheduler to offload that work to the placement
  service rather than query all compute nodes from the Nova database and then
  iterate those potential hosts through all of the python filters. The
  placement service can optimize by performing the compute node resource
  provider filtering with SQL queries directly.
* `Handle aggregate resources`_: This is continuing work from Newton where we
  need to be able to model resource provider aggregates for things like shared
  storage and IP allocation pools. Then the resource tracker in the compute
  nodes can pull this information from the placement service when a request is
  made for shared storage in a compute node within a particular aggregate. The
  allocation claim is then made on the resource provider rather than the
  compute node.
* `Custom resource classes`_: A REST API will be provided for working with
  resource classes and creating custom resource classes which will be used when
  creating inventory and allocation records for Ironic nodes.

.. _Placement / Scheduler interaction: ../specs/ocata/approved/resource-providers-scheduler-db-filters.html
.. _Handle aggregate resources: ../specs/newton/implemented/generic-resource-pools.html
.. _Custom resource classes: ../specs/ocata/approved/custom-resource-classes.html

API Improvements
----------------

These improvements are a priority because of their relation to being able to
sort and filter instances across multiple cells.

* `Query parameter validation`_: The v2.1 API already uses json schema
  to validate request bodies but request parameters are validated in code,
  sometimes inconsistently, and without microversion support. This effort will
  add json schema validation to request query parameters and allow the schema
  to change with microversions over time.
* `Limit instance sort/filter parameters`_: For administrators, sort and filter
  parameters are passed through to the DB API. This has a number of problems
  such as the filter parameters may be on columns that are not indexed and as
  such the query may have poor performance. The columns may also be on joined
  tables where sorting and filtering does not make sense. So this effort is to
  restrict the sort and filter parameters when listing instances to a known
  good set which could be expanded later if needed using microversions.

.. _Query parameter validation: ../specs/ocata/approved/consistent-query-parameters-validation.html
.. TODO(mriedem): Replace the gerrit review link with a spec once merged.
.. _Limit instance sort/filter parameters: https://review.openstack.org/#/c/393205/

Network Aware Scheduling
------------------------

In Newton we started refactoring the internal Neutron v2 API code such that
port create and update operations were decoupled. Port update is where the host
binding happens. The `goal is to move`_ these operations out of the
nova-compute service and into the nova-conductor service, where the placement
service can eventually be used with IP allocation pools (for Neutron routed
networks), and to also make a port binding or build failure less expensive from
which to recover as it will be centrally managed in the conductor service
rather than on each compute. Supporting Neutron routed networks is a dependency
for using Neutron with multiple cells.

.. _goal is to move: ../specs/ocata/approved/prep-for-network-aware-scheduling-ocata.html
