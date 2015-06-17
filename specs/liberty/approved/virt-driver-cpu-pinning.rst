..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Virt driver pinning guest vCPU threads policies
===============================================

https://blueprints.launchpad.net/nova/+spec/virt-driver-cpu-thread-pinning

This feature aims to implement the remaining functionality of the
virt-driver-cpu-pinning spec. This entails implementing support for thread
policies.

Problem description
===================

Some applications must exhibit real-time or near real-time behavior. This
is general possible by making use of processor affinity and binding vCPUs to
pCPUs. This functionality currently exist in Nova. However, it is also
necessary to consider thread affinity in the context of simultaneous
multithreading (SMT) enabled systems. In these systems, competition for shared
resources can result in unpredictable behavior.

Use Cases
----------

Depending on the workload being executed the end user or cloud admin may
wish to have control over how the guest used hyperthreads. To maximise cache
efficiency, the guest may wish to be pinned to thread siblings. Conversely
the guest may wish to avoid thread siblings (i.e. only pin to one sibling)
or even avoid hosts with threads entirely. This level of control is of
particular importance to Network Function Virtualization (NFV) deployments
which care about maximizing cache efficiency of vCPUs.

Project Priority
-----------------

None

Proposed change
===============

The flavor extra specs will be enhanced to support one new parameter:

* hw:cpu_threads_policy=avoid|separate|isolate|prefer

This policy is an extension to the already implemented CPU policy parameter:

* hw:cpu_policy=shared|dedicated

The threads policy will control how the scheduler / virt driver places guests
with respect to CPU threads. It will only apply if the scheduler policy is
'dedicated'

 - avoid: the scheduler will not place the guest on a host which has
   hyperthreads.
 - separate: if the host has threads, each vCPU will be placed on a
   different core. ie no two vCPUs will be placed on thread siblings
 - isolate: if the host has threads, each vCPU will be placed on a
   different core and no vCPUs from other guests will be able to be
   placed on the same core. ie one thread sibling is guaranteed to
   always be unused,
 - prefer: if the host has threads, vCPU will be placed on the same
   core, so they are thread siblings.

The image metadata properties will also allow specification of the
threads policy:

* hw_cpu_threads_policy=avoid|separate|isolate|prefer

This will only be honored if the flavor does not already have a threads
policy set. This ensures the cloud administrator can have absolute control
over threads policy if desired.

Alternatives
------------

None.

Data model impact
-----------------

None.

The necessary changes were already completed in the original spec.

REST API impact
---------------

No impact.

The existing APIs already support arbitrary data in the flavor extra specs.

Security impact
---------------

No impact.

Notifications impact
--------------------

No impact.

The notifications system is not used by this change.

Other end user impact
---------------------

No impact.

Support for flavor extra specs is already available in the Python clients.

Performance Impact
------------------

None.

Support for CPU policies already exists and this is merely an extension of
that functionality.

Other deployer impact
---------------------

The cloud administrator will gain the ability to define flavors with explicit
threading policy. Although not required by this design, it is expected that
the administrator will commonly use the same host aggregates to group hosts
for both CPU pinning and large page usage, since these concepts are
complementary and expected to be used together. This will minimize the
administrative burden of configuring host aggregates.

Developer impact
----------------

It is expected that most hypervisors will have the ability to support the
required thread policies. The flavor parameter is simple enough that any Nova
driver would be able to support it.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sfinucan

Work Items
----------

* Enhance the scheduler to take account of threads policy when choosing
  which host to place the guest on.

* Enhance the scheduler to take account of threads policy when mapping
  vCPUs to pCPUs

Dependencies
============

None.

Testing
=======

It is not practical to test this feature using the gate and tempest at this
time, since effective testing will require that the guests running the test
be provided with multiple NUMA nodes, each in turn with multiple CPUs.

These features will be validated using a third-party CI (Intel Compute CI).

Documentation Impact
====================

None.

The documentation changes were made in the previous change.

References
==========

Current "big picture" research and design for the topic of CPU and memory
resource utilization and placement. vCPU topology is a subset of this
work:

* https://wiki.openstack.org/wiki/VirtDriverGuestCPUMemoryPlacement

Current CPU pinning validation tests for Intel Compute CI:

* https://github.com/stackforge/intel-nfv-ci-tests

Existing CPU Pinning spec:

* http://specs.openstack.org/openstack/nova-specs/specs/kilo/implemented/virt-driver-cpu-pinning.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
