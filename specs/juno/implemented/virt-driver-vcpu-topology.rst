..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Virt driver guest vCPU topology configuration
=============================================

https://blueprints.launchpad.net/nova/+spec/virt-driver-vcpu-topology

This feature aims to give users and administrators the ability to control
the vCPU topology exposed to guests. This enables them to avoid hitting
limitations on vCPU topologies that OS vendors place on their products.

Problem description
===================

When a guest is given multiple vCPUs, these are typically exposed in the
hardware model as discrete sockets. Some operating system vendors will
place artificial limits on the topologies that their product will support.
So for example, a Windows guest may support 8 vCPUs only if it is exposed
as 2 sockets with 4 cores each. If the vCPUs were exposed as 8 sockets
with 1 core each, some of the vCPUs will be inaccessible to the guest.
It is thus desirable to be able to control the mixture of cores and
sockets exposed to the guest. The cloud administrator needs to be able
to define topologies for flavors, to override the hypervisor defaults,
such that commonly used OS' will not encounter their socket count limits.
The end user also needs to be able to express preferences for topologies
to use with their images.

While the choice of sockets vs cores does not have a significant impact
on performance, if a guest is given threads or is running on host OS
CPUs which are thread siblings, this can have a notable performance impact.
It only makes sense to expose a value of threads > 1 to a guest if all the
guest vCPUs are strictly pinned to host pCPUs and some of the host pCPUs
are thread siblings. While this blueprint will describe how to set the
threads count, it will only make sense to set this to a value > 1 once
the CPU pinning feature is integrated in Nova.

If the flavor admin wishes to define flavors which avoid scheduling on
hosts which have pCPUs with threads > 1, then can use scheduler aggregates
to setup host groups.

Proposed change
===============

The proposal is to add support for configuration of aspects of vCPU topology
at multiple levels.

At the flavor there will be the ability to define default parameters for the
vCPU topology using flavor extra specs

* hw:cpu_sockets=NN - preferred number of sockets to expose to the guest
* hw:cpu_cores=NN - preferred number of cores to expose to the guest
* hw:cpu_threads=NN - preferred number of threads to expose to the guest
* hw:cpu_max_sockets=NN - maximum number of sockets to expose to the guest
* hw:cpu_max_cores=NN - maximum number of cores to expose to the guest
* hw:cpu_max_threads=NN - maximum number of threads to expose to the guest

It is not expected that administrators will set all these parameters against
every flavor. The simplest expected use case will be for the cloud admin to
set "hw:cpu_max_sockets=2" to prevent the flavor exceeding 2 sockets. The
virtualization driver will calculate the exact number of cores/sockets/threads
based on the flavor vCPU count and this maximum sockets constraint.

For larger vCPU counts there may be many possible configurations, so the
"hw:cpu_sockets", "hw:cpu_cores", "hw:cpu_threads" parameters enable the
cloud administrator to express their preferred choice from the large set.

The "hw:max_cores" parameter allows the cloud administrator to place an upper
limit on the number of cores used, which can be useful to ensure a socket
count greater than 1 and thus enable a VM to be spread across NUMA nodes.

The "hw:max_sockets", "hw:max_cores" & "hw:max_threads" settings allow the
cloud admin to set mandatory upper limits on the permitted configurations
that the user can override with properties against the image.

At the image level the exact same set of parameters will be permitted,
with the exception that image properties will use underscores throughout
instead of an initial colon.

* hw_cpu_sockets=NN - preferred number of sockets to expose to the guest
* hw_cpu_cores=NN - preferred number of cores to expose to the guest
* hw_cpu_threads=NN - preferred number of threads to expose to the guest
* hw_cpu_max_sockets=NN - maximum number of sockets to expose to the guest
* hw_cpu_max_cores=NN - maximum number of cores to expose to the guest
* hw_cpu_max_threads=NN - maximum number of threads to expose to the guest

If the user sets "hw_cpu_max_sockets", "hw_cpu_max_cores", or
"hw_cpu_max_threads", these must be strictly lower than the values
already set against the flavor. The purpose of this is to allow the
user to further restrict the range of possible topologies that the compute
host will consider using for the instance.

The "hw_cpu_sockets", "hw_cpu_cores" & "hw_cpu_threads" values
against the image may not exceed the "hw_cpu_max_sockets", "hw_cpu_max_cores"
& "hw_cpu_max_threads" values set against the flavor or image. If the
upper bounds are exceeded, this will be considered a configuration error
and the instance will go into an error state and not boot.

If there are multiple possible topology solutions implied by the set of
parameters defined against the flavor or image, then the hypervisor will
prefer the solution that uses a greater number of sockets. This preference
will likely be further refined when integrating support for NUMA placement
in a later blueprint.

If the user wants their settings to be used unchanged by the compute
host they should set "hw_cpu_sockets" == "hw_cpu_max_sockets",
"hw_cpu_cores" == "hw_cpu_max_cores", and "hw_cpu_threads" ==
"hw_cpu_max_threads" on the image. This will force use of the exact
specified topology.

Note that there is no requirement in this design or implementation for
the compute host topologies to match what is being exposed to the guest.
ie this will allow a flavor to be given sockets=2,cores=2 and still
be used to launch instances on a host with sockets=16,cores=1. If the
admin wishes to optionally control this, they will be able todo so by
setting up host aggregates.

The intent is to implement this for the libvirt driver, targeting QEMU /
KVM hypervisors. Conceptually it is applicable to all other full machine
virtualization hypervisors such as Xen and VMWare.

Alternatives
------------

The virtualization driver could hard code a different default topology, so
that all guest always use

   cores==2, sockets==nvcpus/cores

instead of

   cores==1, sockets==nvcpus

While this would address the immediate need of current Windows OS', this is
not likely to be sufficiently flexible for the longer term, as it forces all
OS into using cores, even if they don't have any similar licensing
restrictions. The over-use of cores will limit the ability to do an effective
job at NUMA placement, so it is desirable to use cores as little as possible.

The settings could be defined exclusively against the images, and not make
any use of flavor extra specs. This is undesirable because to have best
NUMA utilization, the cloud administrator will need to be able to constrain
what topologies the user is allowed to use. The administrator would also
like to have the ability to set up define behaviour so that guest can get
a specific topology without requiring every single image uploaded to glance
to be tagged with the same repeated set of properties.

A more fine grained configuration option would be to allow the specification
of the core and thread count for each separate socket. This would allow for
asymmetrical topologies eg

  socket0:cores=2,threads=2,socket1:cores=4,threads=1

It is noted, however, that at time of writing, no virtualization technology
provides any way to configure such asymmetrical topologies. Thus Nova is
better served by ignoring this purely theoretical possibility and keeping
its syntax simpler to match real-world capabilities that already exist.

Data model impact
-----------------

No impact.

The new properties will use the existing flavor extra specs and image
property storage models.

REST API impact
---------------

No impact.

The new properties will use the existing flavor extra specs and image
property API facilities.

Security impact
---------------

The choice of sockets vs cores can have an impact on host resource utilization
when NUMA is involved, since over use of cores will prevent a guest being
split across multiple NUMA nodes. This feature addresses this by allowing the
flavor administrator to define hard caps, and ensuring the flavor will
always take priority over the image settings.

Notifications impact
--------------------

No impact.

There is no need for this feature to integrate with notifications.

Other end user impact
---------------------

The user will gain the ability to control aspects of the vCPU topology used
by their guest. They will achieve this by setting image properties in glance.

Performance Impact
------------------

The cores vs sockets vs threads decision does not involve any scheduler
interaction, since this design is not attempting to match host topology
to guest topology. A later blueprint on CPU pinning will make it possible
todo such host to guest topology matching, and its performance impact
will be considered there.

Other deployer impact
---------------------

The flavor extra specs will gain new parameters in extra specs which a
cloud administrator can choose to use. If none are set then the default
behaviour is unchanged from previous releases.

Developer impact
----------------

The initial implementation will be done for libvirt with QEMU/KVM. It should
be possible to add support for using the cores/sockets/threads parameters in
the XenAPI and VMWare drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:

  berrange

Work Items
----------

* Provide helper methods against the computer driver base class for
  calculating valid CPU topology solutions for the given hw_cpu_* parameters.
* Add Libvirt driver support for choosing a CPU topology solution based on
  the given hw_cpu_* parameters.

Dependencies
============

No external dependencies

Testing
=======

No tempest changes.

The mechanisms for the cloud administrator and end user to set parameters
against the flavor and/or image are already well tested. The new
functionality focuses on interpreting the parameters and setting corresponding
libvirt XML parameters. This is something that is effectively covered by the
unit testing framework.

Documentation Impact
====================

The new flavor extra specs and image properties will need to be documented.
Guidance should be given to cloud administrators on how to make most
effective use of the new features. Guidance should be given to the end user
on how to use the new features to address their use cases.

References
==========

Current "big picture" research and design for the topic of CPU and memory
resource utilization and placement. vCPU topology is a subset of this
work

* https://wiki.openstack.org/wiki/VirtDriverGuestCPUMemoryPlacement
