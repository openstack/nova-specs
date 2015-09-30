..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Report host memory b/w as a metric in Nova
==========================================

https://blueprints.launchpad.net/nova/+spec/memory-bw

This spec proposes to introduce host memory b/w as a host metric.
Memory b/w can be a essential piece in determining VM performance
bottlenecks and further can be used for better NUMA based placements.

Using Linux platform interface like linux perf APIs, nova-compute
should be able to expose host's memory bandwidth utilization on
every NUMA node.
This memory b/w can be leveraged in Openstack by exposing it as a
monitor.

This will follow a similar approach as the already existing monitor
for CPU.(cpu_monitor.py)

Problem description
===================

Workload optimization for high CPU/Memory intensive workload can be
challenging. This applies to workloads running Redis/Hadoop etc.
Host Memory B/W utilization data is a key indicator to denote the
memory bus overload and can be exposed via the Linux Perf APIs.
This metric can then be leveraged for better placement/optimization
of high CPU/memory intensive workloads.


Use Cases
----------

* Get memory b/w stats as a metric data by adding a new subclass
  of BaseResourceMonitor.


Project Priority
-----------------

None


Proposed change
===============

Performance co-pilot (PCP) is a system performance and analysis
framework available with most of the popular distros. The linux perf
APIs are called via the PCP tool. The PCPD daemon can be used to
obtain/fetch values of the Nest/Uncore memory PMU counters on each
NUMA node.

PCP provides the python bindings that would be called via openstack
monitor code in nova to obtain the desired values for memory bandwidth
utilization.

Estimated changes are going to be in the following places:

* Extend the Resource monitor framework to implement a optional
  monitor for Memory B/W utilization, much in line with the CPU
  monitor.

* Define two methods in the virt driver parent class and implement
  them in the livirt driver:

  - `get_max_memory_bw`: Returns the maximum memory bandwidth for each
    NUMA node.

  - `get_memory_bw_counter_agg`: Returns the value of the aggregated counter
    values associated with memory bandwidth for each NUMA node.

  Nova shall calculate the diff of the aggregated counter values over two calls
  and calculate the rate. This rate will be compared against the maximum bw
  value to obtain the utilization. get_max_memory_bw shall be called only once
  during the initialization of the monitor.

  The unit of representation of the rate will be made consistent with the
  value obtained from the counters.

* Introduce a nova object model representation of the data.


Alternatives
------------

The alternative is to call the perf APIs directly but that introduces
platform specific dependencies. PMU counter names and the math to derive
memory bandwidth shall vary across platforms and types of hardware. This
gap shall be bridged by PCP.


Data model impact
-----------------

None


REST API impact
---------------

None

Security impact
---------------

None.

Notifications impact
--------------------

None

Other end user impact
---------------------

None


Performance Impact
------------------

The performance impact is negligible since the data is aggregated by the
hardware and accessed via PCP. Openstack will call this API once a minute
with an option to increase the interval.

Other deployer impact
---------------------

The following packages should be added to the system:

    * pcp
    * python-pcp

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sudipta Biswas sbiswas7

Other assignee:
  Pradipta Banerjee bpradipt


Work Items
----------

1. Use pcp python bindings to obtain the memory bw utilization.

2. Perform data sampling in the monitoring code.

3. Create metrics plugin to sample the memory b/w data.


Dependencies
============

None


Testing
=======

The changes will be exercised through unit tests.

Documentation Impact
====================

None


References
==========

http://pcp.io/


