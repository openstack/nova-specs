=====================================================================
Overhead option to differ hypervisor process on a global set of pCPUs
=====================================================================

https://blueprints.launchpad.net/nova/+spec/overhead-pin-set

The Nova scheduler and the placement API determine CPU resource
utilization and instance CPU placement based on the number of vCPUs in
the flavor. A number of hypervisors have operations that are being
performed on behalf of the guest instance in the host OS. These
operations should be accounted and scheduled separately, as well as
have their own placement policy controls applied.

Problem description
===================

Previously was introduced option ``hw:emulator_threads_policy`` which
adds additional pCPU per guest to run emulator threads.

While it resolves issues related to spike latency caused by emulator
threads running on same pCPUs that vCPUs are pinned on, some operators
have desire to pack all emulator threads on a specific set of pCPUs in
order to allow more pCPUs running vCPUs.

Use Cases
---------

As an operator I want all the emulator threads of all the instances
running in a specific set pCPUs.

Project Priority
----------------

None

Proposed change
===============

To extend flexibility and address use-cases where resources on hosts
are limited a separate "Standardize CPU resource tracking" spec_ that
discusses a change to how we would like to both simplify the
configuration of a compute node with regards to CPU resource inventory
as well as make the quantitative tracking of dedicated CPU resources
consistent with the tracking of shared CPU resources via the placement
API, introduces a CONF option ``cpu_shared_set`` which stores a pinset
string that indicates the physical processors that should be used for
the ``VCPU`` resource requests.

The proposed change is to run the emulator threads work on these
shared host CPUs. The admin who would like to take advantage of such
improvement for its flavors will have to configure the flavor
extra-specs ``hw:emulator_threads_policy=share``.

It is has noted that, the ``hw:emulator_threads_policy=share`` already
exists but its default behavior where ``CONF.cpu_shared_set`` is not
configured on host will remain the same, meaning that the emulator
threads will float on the set of pCPUs dedicated for the guest. As for
``hw:emulator_threads_policy=isolate`` its behavior will remain the
same, meaning that an additional pCPU is reserved to run guest
emulator threads on.

.. _spec: https://review.openstack.org/#/c/555081/


Alternatives
------------

An alternative would be to always pin emulator threads on
``CONF.cpu_shared_set``. It has been noted that, removing the actual
flexibility provided to users to isolate guest emulator threads on an
dedicated pCPU or let the guest emulator threads floating across the
whole set of pCPUs dedicated for guest are still valid option and we
should not remove such flexibility.

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

For end users, using option ``emulator_threads_policy=share`` with
hosts have ``CONF.cpu_shared_set`` configured is going to improve the
latency of guests running sensitive workloads.

Performance Impact
------------------

None

Other deployer impact
---------------------

Operators who want to configure some flavors to run their guest
emulator threads outside of the pCPUs pinned for running vCPUs threads
will be able to achieve that by specifying a range of pCPUs using
``CONF.cpu_shared_set`` and setting ``hw:emulator_threads=share``.

Developer impact
----------------

* Developers of other virtualization drivers may wish to make use of
  the new flavor extra spec property and scheduler accounting. This
  will be of particular interest to the Xen hypervisor, if using the
  stub domain feature.

Upgrade impact
--------------

N/A

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sahid Orentino Ferdjaoui <sahid-ferdjaoui>

Work Items
----------

* Introducing ``CONF.compute.cpu_shared_set`` option for compute nodes
* Configuring guest to pin its emulator threads on the
  ``CONF.compute.cpu_shared_set`` when
  ``emulator_threads_policy=share``

Dependencies
============

* The ``CONF.compute.cpu_shared_set`` is also defined in "Standardize
  CPU resource tracking" spec_. This option could be introduced by
  both of the spec.

Testing
=======

This can be tested in any CI system that is capable of testing the
current NUMA and dedicated CPUs policy. i.e. It requires ability to
use KVM and not merely QEMU. Functional tests for the scheduling and
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

   * - Queen
     - Proposed
   * - Rocky
     - Re-proposed
