..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Per aggregate scheduling weight
===============================

https://blueprints.launchpad.net/nova/+spec/per-aggregate-scheduling-weight

This spec proposes to add ability to allow users to use ``Aggregate``'s
``metadata`` to override the global config options for weights to achieve
more fine-grained control over resource weights.


Problem description
===================

In the current implementation, the weights are controlled by config options
like [filter_scheduler] cpu_weight_multiplier, the total weight of a compute
node is calculated by combination of several weigher:
weight = w1_multiplier * norm(w1) + w2_multiplier * norm(w2) + ...

As it is controlled by config options, the weights are global across the whole
deployment, this is not convenient enough for operators and users.

Use Cases
---------

As an operator I may want to have a more fine-grained control over resource
scheduling weight configuration so that I can control my resource allocations.

Operators may divide the resource pool by hardware type and their(hardware)
suitable workloads with host aggregates. Setting independent scheduling weight
for each aggregate can make it easier to control the scheduling behavior(
spreading or concentrate). For example, by default I want my deployment to
stack resources to conserve energy, but for my HPC aggregate, I want to set
``cpu_weight_multiplier=10.0`` to spread instances across the hosts in that
aggregate because I want to avoid noisy neighbors as much as possible.

Operators may also restrict flavors/images to host aggregates, and those
flavors/images may have preferences about the importance of CPU/RAM/DISK,
setting a suitable weight for this aggregate other than the global weight
could provide a more suitable resource allocation for the corresponding
workloads. For example, I want to deploy a big data analysis cluster(for
example Hadoop), there are different roles for each vm in this cluster,
for some of them the amount of CPU and RAM is much more important than DISK,
like the ``HDFS NameNode`` and nodes that runs ``MapReduce`` tasks; for some
of them, the size of DISK is more important, like the ``HDFS DataNodes``.
By creating different flavor/image and restrict them to aggregates that have
suitable scheduling weight can have a overall better resource allocation and
performance.

Proposed change
===============

This spec proposes to add abilities in existing weighers to read the
``*_weight_multiplier`` from ``aggregate metadata`` to override the
``*_weight_multiplier`` from config files to achieve a more flexible
weight during scheduling.

This will be done by making the ``weight_multiplier()`` method take a
``HostState`` object as a parameter and get the corresponding
``weight_multiplier`` from the aggregate metadata similar to how
``nova.scheduler.utils.aggregate_values_from_key()`` is used by the
``AggregateCoreFilter`` filter. If the host is in multiple aggregates and
there are conflicting weight values in the metadata, we will use the minimum
value among them.


Alternatives
------------

Add abilities to read the above mentioned multipliers from
``flavor extra_specs`` to make them per-flavor.

This alternative will not be implemented because:

- It could be very difficult to manage per-flavor weights in a
  cloud with a lot of flavors, e.g. public cloud.

- Per-flavor weights does not help the case of an image that
  requires some kind of extra weight to the host it is used on, so
  per-flavor weights is less flexible, but with the proposed solution
  we can apply the weights to aggregates which can then be used to
  restrict both flavors (AggregateInstanceExtraSpecsFilter) and
  images (AggregateImagePropertiesIsolation).


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

There could be a minor decrease in the scheduling performance as
some data gathering and calculation will be added.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng


Work Items
----------

#. Add the ability to existing weigher to read the
   ``*_weight_multiplier`` from ``aggregate metadata`` to override
   the ``*_weight_multiplier`` from config files to achieve a more
   flexible weight during scheduling

#. Update docs about the new change


Dependencies
============

None.

Testing
=======

Unit tests for verifying when a ``*_weight_multiplier`` is provided in
aggregate metadata.


Documentation Impact
====================

Update the weights user reference documentation here:

https://docs.openstack.org/nova/latest/user/filter-scheduler.html#weights

The aggregate metadata key/value for each weigher will be called out in
the documentation.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
