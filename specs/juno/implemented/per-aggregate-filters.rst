..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Scheduler: Adds per-aggregate filters
=====================================

https://blueprints.launchpad.net/nova/+spec/per-aggregate-disk-allocation-ratio
https://blueprints.launchpad.net/nova/+spec/per-aggregate-max-instances-per-host
https://blueprints.launchpad.net/nova/+spec/per-aggregate-max-io-ops-per-host

The aim of this bp is to add the ability to the filters DiskFilter,
NumInstancesFilter and IoOpsFilter to set our options by aggregates.

Problem description
===================

Operator wants to define different filtering options (disk_allocation_ratio,
max_instances_per_host, max_io_ops_per_host) for a subset of compute hosts.

Proposed change
===============

Create new filters that extend DiskFilter, NumInstancesFilter and
IoOpsAggregateFilter to provide the ability to read the metadata from
aggregates. If no valid values found fall back to the global default
configurations set in nova.conf.

Alternatives
------------

None

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

Not related with this bp but a performance impact has been reported
to the bug 1300775_
about using aggregate with the scheduler on large
cluster.

.. _1300775: https://bugs.launchpad.net/nova/+bug/1300775

Other deployer impact
---------------------

The operator needs to update the scheduler's nova.conf to activate filters,
also he has to set metadata of the aggregates with the configurations options
disk_allocation_ratio, max_instances_per_host, max_io_ops_per_host.

::

  $ # This one provides for hosts in the aggregate 'agr1' the possibility to
  $ # host 60 instances.
  $ nova aggregate-set-metadata agr1 set metadata max_instances_per_host=60

  $ # This one provides for hosts in the aggregate 'agr2' the possibility to
  $ # oversubscribe disk allocation and configures the scheduler to ignore
  $ # hosts that have currently more than 3 heavy operations.
  $ nova aggregate-set-metadata agr2 set\
  $   metadata max_io_ops_per_host=3
  $   disk_allocation_ratio=3

The operator also needs to reload the scheduler service to activate this new
filter.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid-ferdjaoui

Other contributors:
  <None>

Work Items
----------

 * New filter AggregateNumInstancesFilter
 * New filter AggregateDiskFilter
 * New filter AggregateIoOpsFilter

Dependencies
============

 * A bug has been open to factory per-aggregate logic.
   https://bugs.launchpad.net/nova/+bug/1301340

Testing
=======

We need to add unit tests in test_host_filters.py also we probably need to
think about adding functional tests in tempest.

Documentation Impact
====================

We need to refer these new filters in the documentation, also
'doc/source/devref/filter_scheduler.rst' needs to be updated.

References
==========

These blueprints was accepted for icehouse but because of a work started to add
helper that provides utility methods to get metadata from aggregates and so
remove duplicate code between filters (bug 1301340_). The blueprints was
deferred.

.. _1301340: https://bugs.launchpad.net/nova/+bug/1301340
