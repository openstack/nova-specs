..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Virt driver large page allocation for guest RAM
===============================================

https://blueprints.launchpad.net/nova/+spec/virt-driver-large-pages

This feature aims to improve the libvirt driver so that it can use large pages
for backing the guest RAM allocation. This will improve the performance of
guest workloads by increasing TLB cache efficiency. It will ensure that the
guest has 100% dedicated RAM that will never be swapped out.

Problem description
===================

Most modern virtualization hosts support a variety of memory page sizes. On
x86 the smallest, used by the kernel by default, is 4kb, while large sizes
include 2MB and 1GB. The CPU TLB cache has a limited size, so when there is a
very large amount of RAM present and utilized, the cache efficiency can be
fairly low which in turn increases memory access latency. By using larger page
sizes, there are fewer entries needed in the TLB and thus its efficiency goes
up.

The use of huge pages for backing guests implies that the guest is running with
a dedicated resource allocation. ie the concept of memory overcommit is no
longer possible to provide. This is a tradeoff that cloud administrators may
be willing to make to support workloads that require predictable memory access
times, such as NFV.

While large pages are better than small pages, it can't be assumed that the
benefit increases as the page size increases. In some workloads, a 2 MB page
size can be better overall than 1 GB page sizes. Also the choice of page size
affects the granularity of guest RAM size. ie a 1.5 GB guest would not be able
to use 1 GB pages since RAM is not a multiple of the page size.

Although it is theoretically possible to reserve large pages on the fly, after
a host has been booted for a period of time, physical memory will have become
very fragmented. This means that even if the host has lots of free memory, it
may be unable to find contiguous chunks required to provide large pages. This
is a particular problem for 1 GB sized pages. To deal with this problem, it is
usual practice to reserve all required large pages upfront at host boot time,
by specifying a reservation count on the kernel command line of the host. This
would be a one-time setup task done when deploying new compute node hosts.

Use Cases
---------

Huge pages can be used as a way to provide the concept of dedicated
resource guest, since huge pages must be allocated to exactly one guest
at a time. The advantage over just setting the RAM over commit ratio to
0, is that the memory associated with huge pages cannot be swapped or
used by the OS for other purposes. It is guaranteed to always be assigned
to the guest OS.

From a performance POV huge pages provide improved memory access latency
by improving TLB cache hit rate in processors. This benefit is important
to workloads that require strong guarantees of guest performance, such as
the Network Function Virtualization (NFV) deployments.

Project Priority
----------------

None

Proposed change
===============

The flavor extra specs will be enhanced to support a new parameter

* hw:mem_page_size=large|any|2MB|1GB

In absence of any page size setting in the flavor, the current behaviour of
using the small, default, page size will continue. A setting of 'large' says
to only use larger page sizes for guest RAM, eg either 2MB or 1GB on x86;
'any' means to leave policy upto the compute driver implementation to
decide. When seeing 'any' the libvirt driver might try to find large pages,
but fallback to small pages, but other drivers may choose alternate policies
for 'any'. Finally an explicit page size can be set if the workload has very
precise requirements for a specific large page size. It is expected that the
common case would be to use page_size=large or page_size=any. The
specification of explicit page sizes would be something that NFV workloads
would require.

The property defined for the flavor can also be set against the image, but
the use of large pages would only be honoured if the flavor already had a
policy or 'large' or 'any'. ie if the flavor said a specific
numeric page size, the image would not be permitted to override this to access
other large page sizes. Such invalid override in the image would result in
an exception being raised and the attempt to boot the instance resulting in
an error. While ultimate validation is done in the virt driver, this can also
be caught and reported at the at the API layer.

If the flavor memory size is not a multiple of the specified huge page size
this would be considered an error which would cause the instance to fail to
boot. If the page size is 'large' or 'any', then the compute driver would
obviously attempt to pick a page size which was a multiple of the RAM size
rather than erroring. This is only likely to be a significant problem when
when using 1 GB page sizes, which imply that ram size must be in 1 GB
increments.

The libvirt driver will be enhanced to honour this parameter when configuring
the guest RAM allocation policy. This will effectively introduce the concept
of a "dedicated memory" guest, since large pages must be 1-to-1 associated with
guests - there's not facility to over commit by allowing one large page to be
used with multiple guests or to swap large pages.

The libvirt driver will be enhanced to report on large page availability per
NUMA node, building on previously added NUMA topology reporting.

The scheduler will be enhanced to take account of the page size setting on the
flavor and pick hosts which have sufficient large pages available when
scheduling the instance. Conversely if large pages are not requested, then the
scheduler needs to avoid placing the instance on a host which has pre-reserved
large pages. The enhancements for the scheduler will be done as part of the
new filter that is implemented as part of the NUMA topology blueprint. This
involves altering the logic done in that blueprint, so that instead of just
looking at free memory in each NUMA node, it instead looks at the free page
count for the desired page size.

As illustrated later in this document each host will be reporting on
all page sizes available and this information will be available to the
scheduler. When intepreting 'large' it will consider any page size
except the smallest one. This obviously implies that there is
potential for 'large' and 'small' to have different meanings depending
on the host being considered. For the use cases where this would be a
problem, an explicit page size would be requested instead of using
these symbolic named sizes. It will also have to consider whether the
page size is a multiple of the flavor memory size. If the instance is
using multiple NUMA nodes, it will have to consider whether the RAM in
each guest node is a multiple of the page size, rather than the total
memory size.

Alternatives
------------

Recent Linux hosts have a concept of "transparent huge pages" where the kernel
will opportunistically allocate large pages for guest VMs. The problem with
this is that over time, the kernel's memory allocations get very fragmented
making it increasingly hard to find contiguous blocks of RAM to use for large
pages. This makes transparent large pages impractical for use with 1 GB page
sizes. The opportunistic approach also means that users do not have any hard
guarantee that their instance will be backed by large pages. This makes it an
unusable approach for NFV workloads which require hard guarantees.

Data model impact
-----------------

The previously added data in the host state structure for reporting NUMA
topology would be enhanced to further include information on page size
availability per node. So it would then look like

::

  hw_numa = {
     nodes = [
         {
            id = 0
            cpus = 0, 2, 4, 6
            mem = {
               total = 10737418240
               free = 3221225472
            },
            mempages = [{
                 size_kb = 4,
                 total = 262144,
                 used = 262144,
               }, {
                 size_kb = 2048,
                 total = 1024,
                 used = 1024,
               }, {
                 size_kb = 1048576,
                 total = 7,
                 used = 0,
               }
            ]
            distances = [ 10, 20],
         },
         {
            id = 1
            cpus = 1, 3, 5, 7
            mem = {
               total = 10737418240
               free = 5368709120
            },
	    mempages = [{
                 size_kb = 4,
                 total = 262144,
                 used = 512,
               }, {
                 size_kb = 2048,
                 total = 1024,
                 used = 128,
               }, {
                 size_kb = 1048576,
                 total = 7,
                 used = 4,
               }
            ]
            distances = [ 20, 10],
         }
     ],
  }

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

There are no changes that directly impact the end user, other than the fact
that their guest should have more predictable memory access latency.

Performance Impact
------------------

The scheduler will have more logic added to take into account large page
availability per NUMA node when placing guests. Most of this impact will have
already been incurred when initial NUMA support was added to the scheduler.
This change is merely altering the NUMA support such that it considers the
free large pages instead of overall RAM size.

Other deployer impact
---------------------

The cloud administrator will gain the ability to set large page policy on the
flavors they configured. The administrator will also have to configure their
compute hosts to reserve large pages at boot time, and place those hosts into a
group using aggregates.

It is possible that there might be a need to expose information on the page
counts to host administrators via the Nova API. Such a need can be considered
for followup work once the work refernced in this basic spec is completed

Developer impact
----------------

If other hypervisors allow the control over large page usage, they could be
enhanced to support the same flavor extra specs settings. If the hypervisor
has self-determined control over large page usage, then it is valid to simply
ignore this new flavor setting. ie do nothing.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid

Other contributors:
  ndipanov
  berrange

Work Items
----------

* Enhance libvirt driver to report available large pages per NUMA node in the
  host state data
* Enhance libvirt driver to configure guests based on the flavor parameter
  for page sizes
* Add support to scheduler to place instances on hosts according to the
  availability of required large pages

Dependencies
============

* Virt driver guest NUMA node placement & topology. This blueprint is going
  to be an extension of the work done in the compute driver and scheduler
  for NUMA placement, since large pages must be allocated from matching
  guest & host NUMA node to avoid cross-node memory access

   https://blueprints.launchpad.net/nova/+spec/virt-driver-numa-placement

* Libvirt / KVM need to be enhanced to allow Nova to indicate that large
  pages should be allocated from specific NUMA nodes on the host. This is not
  a blocker to supporting large pages in Nova, since it can use the more
  general large page support in libvirt, however, the performance benefits
  won't be fully realized until per-NUMA node large page allocation can be
  done.

Testing
=======

Testing this in the gate would be difficult since the hosts which run the
gate tests would have to be pre-configured with large pages allocated at
initial OS boot time. This in turn would preclude running gate tests with
guests that do not want to use large pages.

Documentation Impact
====================

The new flavor parameter available to the cloud administrator needs to be
documented along with recommendations about effective usage. The docs will
also need to mention the compute host deployment pre-requisites such as the
need to pre-allocate large pages at boot time and setup aggregates.

References
==========

Current "big picture" research and design for the topic of CPU and memory
resource utilization and placement. vCPU topology is a subset of this
work

* https://wiki.openstack.org/wiki/VirtDriverGuestCPUMemoryPlacement

Previously approved for Juno but implementation not completed

* https://review.openstack.org/93653
