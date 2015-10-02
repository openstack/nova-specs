..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Libvirt real time instances
===========================

https://blueprints.launchpad.net/nova/+spec/libvirt-real-time

The CPU pinning feature added to the ability to assign guest virtual CPUs
to dedicated host CPUs, providing guarantees for CPU time and improved worst
case latency for CPU scheduling. The real time feature builds on that work
to provide stronger guarantees for worst case scheduler latency for vCPUs.

Problem description
===================

The CPU pinning feature allowed guest vCPUs to be given dedicated access to
individual host pCPUs. This means virtual instances will no longer suffer
from "steal time" where their vCPU is pre-empted in order to run a vCPU
belonging to another guest. Removing overcommit eliminates the high level
cause of guest vCPU starvation, but guest vCPUs are still susceptible to
latency spikes from various areas in the kernel.

For example, there are various kernel tasks that run on host CPUs, such as
interrupt processing that can preempt guest vCPUs. QEMU itself has a number
of sources of latency, due to its big global mutex. Various device models
have sub-optimal characteristics that will cause latency spikes in QEMU,
as may underling host hardware. Avoiding these problems requires that the
host kernel and operating system be configured in a particular manner, as
well as the careful choice of which QEMU features to exercise. It also
requires that suitable schedular policies are configured for the guest
vCPUs.

Assigning huge pages to a guest ensures that guest RAM cannot be swapped out
on the host, but there are still other arbitrary memory allocations for the
QEMU emulator. If parts of QEMU get swapped out to disk, then can have an
impact on the performance of the realtime guest.

Enabling realtime is not without cost. In order to meet the strict worst
case requirements for CPU latency, overall throughput of the system must
necessarily be compromised. As such it is not reasonable to have the
real time feature unconditionally enabled for an OpenStack deployment.
It must be an opt-in that is used only in the case where the guest workload
actually demands it.

As an indication of the benefits and tradeoffs of realtime, it is useful
to consider some real performance numbers. With bare metal and dedicated
CPUs but non-realtime schedular policy, worst case latency is on the order
of 150 microseconds, and mean latency is approx 2 microseconds. With KVM
and dedicated CPUs and a realtime schedular policy, worst case latency
is 14 microseconds, and mean latency is < 10 microseconds. This shows
that while realtime brings significant benefits in worst case latency,
the mean latency is still significantly higher than that achieved on
bare metal with non-realtime policy. This serves to re-inforce the point
that realtime is not something to unconditionally use, it is only
suitable for specific workloads that require latency guarantees. Many
apps will find dedicated CPUs alone to be sufficient for their needs.


Use Cases
---------

Tenants who wish to run workloads where CPU execution latency is important
need to have the guarantees offered by a real time KVM guest configuration.
The NFV appliances commonly deployed by members of the telco community are
one such use case, but there are plenty of other potential users. For example,
stock market trading applications greatly care about scheduling latency, as
may scientific processing workloads.

It is expected that this feature would predominently be used in private
cloud deployments. As well as real-time compute guarantees, tenants will
usually need corresponding guarantees in the network layer between the
cloud and the service/system it is communicating with. Such networking
guarantees are largely impractical to achieve when using remote public
clouds across the internet.

Project Priority
----------------

None

Proposed change
===============

The intention is to build on the previous work done to enable use of NUMA
node placement policy, dedicated CPU pinning and huge page backed guest
RAM.

The primary requirement is to have a mechanism to indicate whether realtime
must be enabled for an instance. Since real time has strict pre-requisites
in terms of host OS setup, the cloud administrator will usually not wish
to allow arbitrary use of this feature. Realtime workloads are likely to
comprise a subset of the overall cloud usage, so it is anticipated that
there will be a mixture of compute hosts, only some of which provide a
realtime capability.

For this reason, an administrator will need to make use of host aggregates
to partition their compute hosts into those which support real time and
those which do not.

There will then need to be a property available on the flavor

* hw:cpu_realtime=yes|no

which will indicate whether instances booted with that flavor will be
run with a realtime policy. Flavors with this property set to 'yes'
will need to be associated with the host aggregate that contains hosts
supporting realtime.

A pre-requisite for enabling the realtime feature on a flavor is that
it must also have 'hw:cpu_policy' is set to 'dedicated'. ie all real
time guests must have exclusive pCPUs assigned to them. You cannot give
a real time policy to vCPUs that are susceptible to overcommit, as that
would lead to starvation of the other guests on that pCPU, as well as
degrading the latency guarantees.

The precise actions that a hypervisor driver takes to configure a guest
when real time is enabled are implementation defined. Different hypevisors
will have different configuration steps, but the commonality is that all
of them will be providing vCPUs with an improved worst case latency
guarantee, as compared to non-realtime instances. The tenant user does
not need to know the details of how the requirements are met, merely
that the cloud can support the necessary latency guarantees.

In the case of the libvirt driver with the KVM hypervisor, it is expected
that setting the real time flavor will result in the following guest
configuration changes

* Entire QEMU and guest RAM will be locked into memory
* All vCPUs will be given a fixed realtime scheduler priority

As well as the vCPU workload, most hypervisors have one or more other
threads running in the control plane which do work on behalf of the
virtual machine. Most hypervisors hide this detail from users, but
the QEMU/KVM hypervispor exposes it via the concept of emulator
threads. With the initial support for dedicated CPUs, Nova was set
to confine the emulator threads to run on the same set of pCPUs
that the guest's vCPUs are placed. This is highly undesirable in
the case of realtime, because these emulator threads will be
doing work that can impact latency guarantees. There is thus a
need to place emulator threads in a more fine precise fashion.

Most guest OS will run with multiple vCPUs and have at least one of
their vCPUs dedicated to running non-realtime house keeping tasks.
Given this, the intention is that the emulator threads be co-located
with the vCPU that is running non-realtime tasks. This will in turn
require another tunable, which can be set either on the flavor, or
on the image. This will indicate which vCPUs will have realtime policy
enabled:

* hw:cpu_realtime_mask=^0-1

This indicates that all vCPUs, except vCPUs 0 and 1 will have
a realtime policy. ie vCPUs 0 and 1 will remain non-realtime.
The vCPUs which have a non-realtime policy will also be used to
run the emulator thread(s). At least one vCPU must be reserved
for non-realtime workloads, it is an error to configure all
vCPUs to be realtime. If the property is not set, then the
default behaviour will be to reserve vCPU 0 for non-realtime
tasks. This property will be overridable on the image too via
the hw_cpu_realtime_mask property.

In the future it may be desirable to allow emulator threads to
be run on a host pCPU that is completely separate from those
running the vCPUs. This would, for example, allow for running
of guest OS, where all vCPUs must be real-time capable, and so
cannot reserve a vCPU for real-time tasks. This would require
the schedular to treat the emulator threads as essentially being
a virtual CPU in their own right. Such an enhancement is considered
out of scope for this blueprint in order to remove any dependency
on schedular modifications. It will be dealt with in a new blueprint

* https://blueprints.launchpad.net/nova/+spec/libvirt-emulator-threads-policy

A significant portion of the work required will be documenting the
required compute host and guest OS setup, as much of this cannot be
automatically performed by Nova itself. It is anticipated that the
developers of various OpenStack deployment tools will use the
documentation to extend their tools to be able to deploy realtime
enabled compute hosts. This is out of scope of this blueprint,
however, which will merely document the core requirements. Tenants
building disk images will also need to consume this documentation
to determine how to configure their guest OS.

Alternatives
------------

One option would be to always enable a real time scheduler policy when the
guest is using dedicated CPU pinning and always enable memory locking when
the guest has huge pages. As explained in the problem description, this is
highly undesirable as an approach. The real time guarantees are only achieved
by reducing the overall throughput of the system. So unconditionally enabling
realtime for hosts / guests which do not require it would significantly waste
potential compute resources. As a result it is considered mandatory to have
an opt-in mechanism for enabling real time.

Do nothing is always an option. In the event of doing nothing, guests would
have to put up with the latencies inherent in non-real time scheduling, even
with dedicated pCPUs. Some of those latencies could be further mitigated by
careful host OS configuration, but extensive performance testing as shown that
even with carefully configured host and dedicated CPUs, worst case latencies
for a non-realtime task will be at least a factor of x10 worse than when
realtime is enabled. Thus not supporting realtime guests within OpenStack
will exclude Nova from use in a variety of scenarios, forcing users to
deployment alternative non-openstack solutions, or requiring openstack
vendors to fork the code and ship their own custom realtime solutions. Neither
of these are attractive options for OpenStack users or vendors in the long
term, as it would either loose user share, or balkanize the openstack
ecosystem.

Data model impact
-----------------

None required

REST API impact
---------------

None required

Security impact
---------------

The enablement of real time will only affect the pCPUs that are assigned to
the guest. Thus if the tenant is already permitted to use dedicated pCPUs
by the operator, enabling real time does not imply any further privileges.
Thus real time is not considered to introduce any new security concerns.

Notifications impact
--------------------

None

Other end user impact
---------------------

The tenant will have the ability to request real time via an image property.
They will need to carefully build their guest OS images to take advantage
of the realtime characteristics. They will to obtain information from their
cloud provider as to the worst case latencies their deployment is capable
of satisfying, to ensure that it can achieve the requirements of their
workloads.

Performance Impact
------------------

There will be no new performance impact to Nova as a whole. This is building
on the existing CPU pinning and huge pages features, so the scheduler logic is
already in place. Likewise the impact on the host is restricted to pCPUs which
are already assigned to a guest.

Other deployer impact
---------------------

The operator will have the ability to define real time flavors by setting a
flavor extra spec property.

The operator will likely wish to make use of host aggregates to assign a
certain set of compute nodes for use in combination with huge pages and CPU
pinning. This is a pre-existing impact from those features, and real time does
not alter that.

Developer impact
----------------

Other virt drivers may wish to support the flavor/image properties for
enabling real time scheduling of their instances, if their hypervisor has
such a feature.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid

Other contributors:
  berrange

Work Items
----------

The primary work items are

* Add the 'hw_cpu_realtime_mask' field to the ImageMetaProps object
* Update the libvirt guest XML configuration when the real time flavor or
  image properties are present
* Update the Nova deployment documentation to outline what host OS setup
  steps are required in order to make best use of the real time feature

Dependencies
============

* The libvirt project needs to add support for the XML feature to enable
  real time scheduler priority for guests. Merged as of 1.2.13
* The KVM/kernel project needs to produce recommendations for optimal
  host OS setup. Partially done - see KVM Forum talks. Collaboration
  will be ongoing during development to produce Nova documentation.

If the libvirt emulator threads policy blueprint is implemented, then
the restriction that real-time guests must be SMP can be lifted, to
allow for UP realtime guests. This is not a strict pre-requisite
though, merely a complementary piece of work to allow real-time to
be used in a broader range of scenarios.

* https://blueprints.launchpad.net/nova/+spec/libvirt-emulator-threads-policy
* https://review.openstack.org/225893

Testing
=======

None of the current OpenStack community test harnesses check the performance
characteristics of guests deployed by Nova, which is what would be needed to
validate this feature.

The key functional testing requirement is around correct operation of
the existing Nova CPU pinning and huge pages features and their
scheduler integration. This is outside the scope of this particular
blueprint.

Documentation Impact
====================

The deployment documentation will need to be updated to describe how to setup
hosts and guests to take advantage of real time scheduler prioritization.
Since this is requires very detailed knowledge of the system, it is expected
that the feature developers will write the majority of the content for this
documentataion, as the documentation team cannot be expected to learn the
details required.

References
==========

* KVM Forum 2015: Real-Time KVM (Rik van Riel)

  * https://www.youtube.com/watch?v=cZ5aTHeDLDE
  * http://events.linuxfoundation.org/sites/events/files/slides/kvmforum2015-realtimekvm.pdf

* KVM Forum 2015: Real-Time KVM for the Masses (Jan Kiszka)

  * https://www.youtube.com/watch?v=SyhfctYqjc8
  * http://events.linuxfoundation.org/sites/events/files/slides/KVM-Forum-2015-RT-OpenStack_0.pdf

* KVM Forum 2015: Realtime KVM (Paolo Bonzini)

  * https://lwn.net/Articles/656807/

* Linux Kernel Realtime

  * https://rt.wiki.kernel.org/index.php/Main_Page
