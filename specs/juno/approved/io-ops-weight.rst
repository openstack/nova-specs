..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Create Nova Scheduler IO Ops Weighter
=====================================

https://blueprints.launchpad.net/nova/+spec/io-ops-weight

Add a new nova scheduler weighter, sort the filter hosts according to host io
ops number, aims to booting instances on light workload hosts.


Problem description
===================

Currently, Nova scheduler can use host ram or metrics as hosts weight to choice
host to booting instance, but have a large free ram host maybe have this many
or more instances currently in build, resize, snapshot, migrate, rescue or
unshelve task states, especially in some cases of the ram resource of compute
hosts is very uneven. For example, We had two compute hosts, they had large
enough free ram(hostA:64G and hostB:10G) to booting instances, by default Nova
scheduler always choose hostA to booting instance and don't consider the
concurrent instance task. The io_ops_filter can filter out the heavy workload
hosts, but it can't help us to choose a most free compute host to booting.
Using CONF.scheduler_host_subset_size can spread instances on suitable randomly
compute hosts, but we think it's better that consider instance io ops as weight
value.


Proposed change
===============

Create a new scheduler weighter class 'IoOpsWeigher', use host_state.num_io_ops
as weigh_object. Add a new CONF.io_ops_weight_multiplier, default value is
-1.0.

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

The new code itself will introduce some performance impact, new scheduler
weighter 'IoOpsWeigher' add new calculation logic about hosts weight value.
Direct use of the attribute 'num_io_ops' of HostState will not bring a big
performance impact.

Other deployer impact
---------------------

* Add a new weighter class 'IoOpsWeighter', it takes effect by default.
* Add a new config option CONF.io_ops_weight_multiplier in nova.conf, default
  value is -1.0, positive numbers mean to prior choose heavy workload compute
  hosts.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <kiwik-chenrui>

Work Items
----------

* Add new weighter class 'IoOpsWeighter'.
* Add some unit tests and tempest.


Dependencies
============

None

Testing
=======

New unit tests and tempest about 'IoOpsWeighter' will be added.


Documentation Impact
====================

The docs about 'IoOpsWeighter' need to be drafted and new config option
'io_ops_weight_multiplier' in nova.conf should be introduced, default value is
-1.0, negative numbers mean to preference choose light workload compute hosts,
positive numbers mean to the opposite thing.


References
==========

None
