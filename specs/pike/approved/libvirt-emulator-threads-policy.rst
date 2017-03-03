..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Libvirt driver emulator threads placement policy
================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-emulator-threads-policy

The Nova scheduler determines CPU resource utilization and instance
CPU placement based on the number of vCPUs in the flavor. A number of
hypervisors have operations that are being performed on behalf of the
guest instance in the host OS. These operations should be accounted
and scheduled separately, as well as have their own placement policy
controls applied.

Problem description
===================

The Nova scheduler determines CPU resource utilization by counting the
number of vCPUs allocated for each guest. When doing overcommit, as
opposed to dedicated resources, this vCPU count is multiplied by an
overcommit ratio. This utilization is then used to determine optimal
guest placement across compute nodes, or within NUMA nodes.

A number of hypervisors, however, perform work on behalf of a guest
instance in an execution context that is not associated with the
virtual instance vCPUs. With KVM / QEMU, there are one or more threads
associated with the QEMU process which are used for the QEMU main
event loop, asynchronous I/O operation completion, migration data
transfer, SPICE display I/O and more. With Xen, if the stub-domain
feature is in use, there is an entire domain used to provide I/O
backends for the main domain.

Nova does not have any current mechanism to either track this extra
guest instance compute requirement in order to measure utilization,
nor to place any control over its execution policy.

The libvirt driver has implemented a generic placement policy for KVM
whereby the QEMU emulator threads are allowed to float across the same
pCPUs that the instance vCPUs are running on. In other words, the
emulator threads will steal some time from the vCPUs whenever they
have work to do. This is just about acceptable in the case where CPU
overcommit is being used. However, when guests want dedicated vCPU
allocation though, there is a desire to be able to express other
placement policies, for example, to allocate one or more pCPUs to be
dedicated to a guest's emulator threads. This becomes critical as Nova
continues to implement support for real-time workloads, as it will not
be acceptable to allow emulator threads to steal time from real-time
vCPUs.

While it would be possible for the libvirt driver to add different
placement policies, unless the concept of emulator threads is exposed
to the scheduler in some manner, CPU usage cannot be expressed in a
satisfactory manner. Thus there needs to be a way to describe to the
scheduler what other CPU usage may be associated with a guest, and
account for that during placement.

Use Cases
---------

With current Nova real time support in libvirt, there is a requirement
to reserve one vCPU for running non-realtime workloads. The QEMU
emulator threads are pinned to run on the same host pCPU as this
vCPU. While this requirement is just about acceptable for Linux
guests, it prevents use of Nova to run other real time operating
systems which require realtime response for all vCPUs. To broaden the
realtime support it is necessary to pin emulator threads separately
from vCPUs, which requires that the scheduler be able to account for
extra pCPU usage per guest.

Project Priority
----------------

None

Proposed change
===============

A pre-requisite for enabling the emulator threads placement policy
feature on a flavor is that it must also have ‘hw:cpu_policy’ set to
‘dedicated’.

Each hypervisor has a different architecture, for example QEMU has
emulator threads, while Xen has stub-domains. To avoid favoring any
specific implementation, the idea is to extend
`estimate_instance_overhead` to return 1 additional host CPU to take
into account during claim. A user which expresses the desire to
isolate emulator threads must use a flavor configured to accept that
specification as:

* hw:cpu_emulator_threads=isolate

Would say that this instance is to be considered to consume 1
additional host CPU. That pCPU used to make running emulator threads
is going to always be configured on the related guest NUMA node ID 0,
to make it predictable for users. Currently there is no desire to make
customizable the number of host CPUs running emulator threads since
only one should work for almost every use case. If in the future there
is a desire to isolate more than one host CPU to run emulator threads,
we would implement instead I/O threads to add granularity on
dedicating used resources to run guests on host CPUs.

As we said an additional pCPU is going to be consumed but this first
implementation is not going to update the user quotas, that in a
spirit of simplicity since quotas already leak on different scenarios.

Alternatives
------------

We could use a host level tunable to just reserve a set of host pCPUs
for running emulator threads globally, instead of trying to account
for it per instance. This would work in the simple case, but when NUMA
is used, it is highly desirable to have more fine grained config to
control emulator thread placement. When real-time or dedicated CPUs
are used, it will be critical to separate emulator threads for
different KVM instances.

Another option is to hardcode an assumption that the vCPUs number set
against the flavour implicitly includes 1 vCPUs for emulator. eg a
vCPU value of 5 would imply 4 actual vCPUs and 1 system pseudo-vCPU.
This would likely be extremely confusing to tenant users, and
developers alike.

Do nothing is always an option. If we did nothing, then it would limit
the types of workload that can be run on Nova. This would have a
negative impact inparticular on users making use of the dedicated vCPU
feature, as there would be no way to guarantee their vCPUs are not
pre-empted by emulator threads. It can be worked around to some degree
with realtime by setting a fixed policy that the emulator threads only
run on the vCPUs that have non-realtime policy. This requires that all
guest OS using realtime are SMP, but some guest OS want realtime, but
are only UP.

Data model impact
-----------------

The InstanceNUMATopology object will be extended to have a new field
used to store requested policy

* emulator_threads_policy=CPUEmulatorThreadsPolicy()

This field will be implemented as an enum with two options:

* share - The emulator threads float across the pCPUs associated to
  the guest.
* isolate - The emulator threads are isolated on a single pCPU.

By default 'shared' will be used. It's important to note that: Since
[1] on kernel the load-balancing on CPU isolated from the kernel
command line using 'isolcpus=' has been removed. It means that the
emulator threads are not going to float on the union of pCPUs
dedicated to the guest but instead be constrained to the pCPU running
vCPU 0.

The InstanceNUMACell object will be extended to have a new field where
physical CPUs ID will be stored and used by the driver layer to pin
emulator threads

* cpuset_reserved=SetOfIntegersField(nullable=True)


[1] https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable/+/47b8ea7186aae7f474ec4c98f43eaa8da719cd83%5E%21/#F0


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

For end users, using the option 'cpu_emulator_threads' is going to
consume an additional host CPU on the resources quota regarding the
guest vCPUs allocated.

Performance Impact
------------------

The NUMA and compute scheduler filters will have some changes to them,
but it is not anticipated that they will become more computationally
expensive to any measurable degree.

Other deployer impact
---------------------

Deployers who want to use that new feature will have to configure
their flavors to use a dedicated cpu policy (hw:cpu_policy=dedicated),
in a same time set 'hw:cpu_emulator_threads' to 'isolate'.

Developer impact
----------------

* Developers of other virtualization drivers may wish to make use of
  the new flavor extra spec property and scheduler accounting. This
  will be of particular interest to the Xen hypervisor, if using the
  stub domain feature.

* Developers of metric or GUI systems have to take into account that
  host CPU overhead which are going to be consumed by instances with a
  `cpu_emulator_threads` set as `isolate`.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid-ferdjaoui

Other contributors:
  berrange

Work Items
----------

* Enhance flavor extra spec to take into account hw:cpu_emulator_threads
* Enhance InstanceNUMATopology to take into account cpu_emulator_threads
* Make resource tracker to handle 'estimate_instance_overhead' with vcpus
* Extend estimate_instance_overhead for libvirt
* Make libvirt to corretly pin emulator threads if requested.

Dependencies
============

The realtime spec is not a pre-requisite, but is complementary to
this work

* https://blueprints.launchpad.net/nova/+spec/libvirt-real-time
* https://review.openstack.org/#/c/139688/

Testing
=======

This can be tested in any CI system that is capable of testing the
current NUMA and dedicated CPUs policy. i.e. It requires ability to
use KVM and not merely QEMU. Functionnal tests for the scheduling and
driver bits (libvirt) are going to be added.

Documentation Impact
====================

The documentation detailing NUMA and dedicated CPU policy usage will need
to be extended to also describe the new options this work introduces.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Proposed
   * - Ocata
     - Re-proposed
   * - Pike
     - Re-proposed
