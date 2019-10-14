..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

=========================================
Use ``PCPU`` and ``VCPU`` in One Instance
=========================================

https://blueprints.launchpad.net/nova/+spec/use-pcpu-and-vcpu-in-one-instance

The spec `CPU resource tracking`_ splits host CPUs into ``PCPU`` and ``VCPU``
resources, making it possible to run instances of ``dedicated`` CPU allocation
policy and instances of ``shared`` CPU allocation policy in the same host.
This spec aims to create such kind of instance that some of the CPUs are
dedicated (``PCPU``) CPUs and the remaining CPUs are shared (``VCPU``) CPUs
and expose this information via the metadata API.

Problem description
===================

The current CPU allocation policy, ``dedicated`` or ``shared``, is applied to
all CPUs of an instance. However, with the introduction of
`CPU resource tracking`_, it is possible to propose a more fine-grained CPU
allocation policy, which is based on the control over individual instance CPU,
and specifying the ``dedicated`` or ``shared`` CPU allocation policy to each
instance CPU.

Use Cases
---------

As an operator, I would like to have an instance with some realtime CPUs for
high performance, and at the same time, in order to increase instance density,
I wish to make the remaining CPUs, which do not demand high performance,
shared with other instances because I only care about the performance of
realtime CPUs. One example is deploying the NFV task that is enhanced with
DPDK framework in the instance, in which the data plane threads could be
processed with the realtime CPUs and the control-plane tasks are scheduled
on CPUs that may be shared with other instances.

As a Kubernetes administrator, I wish to run a multi-tier or auto-scaling
application in Kubernetes, which is running in single OpenStack VM, with
the expectation that using dedicated high-performance CPUs for application
itself and deploying the containers on shared cores.

Proposed change
===============

Introduce a new CPU allocation policy ``mixed``
-----------------------------------------------

``dedicated`` and ``shared`` are the existing instance CPU allocation policies
that determine how instance CPU is scheduled on host CPU. This specification
proposes a new CPU allocation policy, with the name ``mixed``, to
create a CPU *mixed* instance in such way that some instance CPUs are
allocated from computing node's ``PCPU`` resource, and the rest of instance
CPUs are allocated from the ``VCPU`` resources. The CPU allocated from
``PCPU`` resource will be pinned on particular host CPUs which are defined in
``CONF.compute.dedicated_cpu_set``, and the CPU from ``VCPU`` resource will be
floating on the host CPUs which are defined in ``CONF.compute.shared_cpu_set``.
In this proposal, we call these two kinds of CPUs as *dedicated* vCPU and
*shared* vCPU respectively.

Instance CPU policy matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~

Nova operator may set the instance CPU allocation policy through the
``hw:cpu_policy`` and ``hw_cpu_policy`` interfaces, which may raise conflict.
The CPU policy conflict is proposed to be solved with the following policy
matrix:

+---------------------------+-----------+-----------+-----------+-----------+
|                           |               hw:cpu_policy                   |
+ INSTANCE CPU POLICY       +-----------+-----------+-----------+-----------+
|                           | DEDICATED |   MIXED   |   SHARED  | undefined |
+---------------+-----------+-----------+-----------+-----------+-----------+
| hw_cpu_policy | DEDICATED | dedicated | conflict  | conflict  | dedicated |
+               +-----------+-----------+-----------+-----------+-----------+
|               | MIXED     | dedicated | mixed     | conflict  | mixed     |
+               +-----------+-----------+-----------+-----------+-----------+
|               | SHARED    | dedicated | conflict  | shared    | shared    |
+               +-----------+-----------+-----------+-----------+-----------+
|               | undefined | dedicated | mixed     | shared    | undefined |
+---------------+-----------+-----------+-----------+-----------+-----------+

For example, if a ``dedicated`` CPU policy is specified in instance flavor
``hw:cpu_policy``, then the instance CPU policy is ``dedicated``, regardless
of the setting specified in image property ``hw_cpu_policy``. If ``shared``
is explicitly set in ``hw:cpu_policy``, then a ``mixed`` policy specified
in ``hw_cpu_policy`` is conflict, which will throw an exception, the instance
booting request will be rejected.

If there is no explicit instance CPU policy specified in flavor or image
property, the flavor matrix result would be 'undefined', and the final
instance policy is further determined and resolved by ``resources:PCPU``
and ``resources:VCPU`` specified in flavor extra specs. Refer to
:ref:`section<mixed-instance-via-PCPU-VCPU>` and the spec
`CPU resource tracking`_.

Affect over real-time vCPUs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's also possible to set some *mixed* instance vCPUs as real-time vCPU,
*realtime* CPUs must be chosen from the instance *dedicated* CPU set.

Affect over emulator thread policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If emulator thread policy is ``ISOLATE``, the *mixed* instance will look for
a *dedicated* host CPU for instance emulator thread, which is very similar
to the case introduced by ``dedicated`` policy instance.

If the emulator thread policy is ``SHARE``, then the instance emulator thread
will float over the host CPUs defined in configuration
``CONF.compute.cpu_shared_set``.

Set dedicated CPU bit-mask in ``hw:pinned_cpus`` for ``mixed`` instance
-----------------------------------------------------------------------

As an interface to create the ``mixed`` policy instance through legacy flavor
extra specs or image properties, the flavor extra spec ``hw:pinned_cpus`` is
introduced. If the extra spec ``hw:pinned_cpus`` is found in the instance
flavor, then the information of the *dedicated* CPU could be found through
parsing ``hw:pinned_cpus``.
Here is the example to create an instance with ``mixed`` policy:

.. code::

    $ openstack flavor set <flavor_id> \
        --property hw:cpu_policy=mixed \
        --property hw:pinned_cpus=0-3,7

And, following is the proposing command to create a *mixed* instance which
consists of multiple NUMA nodes by setting the *dedicated* CPUs in
``hw:pinned_cpus``:

.. code::

    $ openstack flavor set <flavor_id> \
        --property hw:cpu_policy=mixed \
        --property hw:pinned_cpus=2,7 \
        --property hw:numa_nodes=2 \
        --property hw:numa_cpus.0=0-2 \
        --property hw:numa_cpus.1=3-7 \
        --property hw:numa_mem.0=1024 \
        --property hw:numa_mem.1=2048

.. note::
    Please be aware that there is no equivalent setting in image properties
    for flavor extra spec ``hw:pinned_cpus``. It will not be supported to
    create *mixed* instance through image properties.

.. _mixed-instance-via-PCPU-VCPU:

Create *mixed* instance via ``resources:PCPU`` and ``resources:VCPU``
---------------------------------------------------------------------

`CPU resource tracking`_ introduced a way to create an instance with
``dedicated`` or ``shared`` CPU allocation policy through ``resources:PCPU``
and ``resources:VCPU`` interfaces, but did not allow requesting both ``PCPU``
resource and ``VCPU`` resource for one instance.

This specification proposes to let an instance request ``PCPU`` resource along
with ``VCPU``, and effectively applying for the ``mixed`` CPU allocation
policy if the ``cpu_policy`` is not explicitly specified in the flavor list.
So an instance with such flavors potentially creates a ``mixed`` policy
instance:

.. code::

    $ openstack flavor set \
        --property "resources:PCPU"="<dedicated CPU number>" \
        --property "resources:VCPU"="<shared CPU number>" \
        <flavor_id>

For *mixed* instance created in such way, both <shared CPU number> and
<dedicated CPU number> must be greater than zero. Otherwise, it effectively
creates the ``dedicated`` or ``shared`` policy instance, that all CPUs in the
instance is in a same allocation policy.

The ``resources:PCPU`` and ``resources::VCPU`` interfaces only put the request
toward ``Placement`` service for how many ``PCPU`` and ``VCPU`` resources are
required to fulfill the instance vCPU thread and emulator thread requirement.
The ``PCPU`` and ``VCPU`` distribution on the instance, especially on the
instance with multiple NUMA nodes, will be spread across the NUMA nodes in the
round-robin way, and ``VCPU`` will be put ahead of ``PCPU``. Here is one
example and the instance is created with flavor below::

    flavor:
      vcpus:8
      memory_mb=512
      extra_specs:
        hw:numa_nodes:2
        resources:VCPU=3
        resources:PCPU=5

Instance emulator thread policy is not specified in the flavor, so it does not
occupy any dedicated ``PCPU`` resource for it, all ``PCPU`` and ``VCPU``
resources will be used by vCPU threads, and the expected distribution on NUMA
nodes is::

    NUMA node 0: VCPU VCPU PCPU PCPU
    NUMA node 1: VCPU PCPU PCPU PCPU

.. note::
    The demanding instance CPU number is the number of vCPU, specified by
    ``flavor.vcpus``, plus the number of CPU that is special for emulator
    thread, and if the emulator thread policy is ``ISOLATE``, the instance
    requests ``flavor.vcpus`` + 1 vCPUs, if the policy is not ``ISOLATE``,
    the instance just requests ``flavor.vcpus`` vCPU.

Alternatives
------------

Creating CPU mixed instance by extending the ``dedicated`` policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of adding a special instance CPU allocation policy, the CPU mixed
instance is supported by extending the existing ``dedicated`` policy and
specifying the CPUs that are pinned to the host CPUs chosen from ``PCPU``
resource.

Following extra spec and the image property are defined to keep the
*dedicated* CPUs of a ``mixed`` policy instance::

    hw:cpu_dedicated_mask=<cpu set string>
    hw_cpu_dedicated_mask=<cpu set string>

The ``<cpu set string>`` shares the same definition defined above.

This was rejected at it overloads the ``dedicated`` policy to mean two things,
depending on the value of another configuration option.

Creating ``mixed`` instance with ``hw:cpu_policy`` and ``resources:(P|V)CPU``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Following commands was proposed as an example to create a *mixed* instance by
an explicit request of ``PCPU`` resources, and infer the ``VCPU`` count by
``flavor::vcpus`` and ``PCPU`` count:

.. code::

    $ openstack flavor create mixed_vmf --vcpus 4 --ram 512 --disk 1
    $ openstack flavor set mixed_vmf \
        --property hw:cpu_policy=mixed \
        --property resources:PCPU=2

This was rejected due to the mixing use of ``hw:cpu_policy`` and
``resources:PCPU``. It is not recommended to mix placement style syntax with
traditional extra specs.

Data model impact
-----------------

No change to data objects.

..note::
    The ``InstanceNUMACell.cpu_pinning`` field keeps the CPU pinning
    information with the instance CPU ID and the host CPU ID that the
    instance CPU is pinning on. This field is used and filled after the CPU
    pair information is determined for the instance taking the ``dedicated``
    policy.
    This field will also be used for ``mixed`` policy instance with the same
    purpose, but will be initialized with a dictionary keyed by the instance
    CPU IDs that wants to be pinned on host CPUs at the instance object
    creating stage. The value of this field will be initialized with *-1*,
    which means host CPU ID is not valid because the host accommodating the
    instance is not determined in instance creating stage. The value is
    replaced with appropriate host CPU ID by nova-scheduler.

REST API impact
---------------

The metadata API will be extended with the *dedicated* vCPU info and a new
OpenStack metadata version will be added to indicate this is a new metadata
API.

The new field will be added to the ``meta_data.json``::

    dedicated_cpus=<cpu set string>

The ``<cpu set string>`` indicated the vCPU IDs which are running on dedicated
host CPUs.

The new cpu policy ``mixed`` is added to extra spec ``hw:cpu_policy``.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

If the end user wants to create an instance with a ``mixed`` CPU allocation
policy, the user is required to set corresponding flavor extra specs or image
properties.

Performance Impact
------------------

This proposal affects the selection of instance CPU allocation policy, but the
performance impact is trivial.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

The ``mixed`` cpu policy is only available when the whole cluster upgrade
finished. A service version will be bumped for detecting the upgrade.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Wang, Huaqiang <huaqiang.wang@intel.com>

Feature Liaison
---------------

Feature liaison:
  Stephen Finucane <stephenfin@redhat.com>

Work Items
----------

* Add new instance CPU allocation policy ``mixed`` property and resolve
  conflicts
* Bump nova service version.
* Add flavor extra spec ``hw:pinned_cpus`` and create *mixed* instance
* Translate *dedicated* and *shared* CPU request to placement ``PCPU`` and
  ``VCPU`` resources request.
* Change libvirt driver to create ``PCPU`` mapping and ``VCPU`` mapping
* Add nova metadata service by offering final pCPU layout in
  ``dedicated_cpus`` field
* Validate real-time CPU mask for ``mixed`` instance.

Dependencies
============

None

Testing
=======

Functional and unit tests are required to cover:

* Ensure to solve the conflicts between the CPU policy matrix
* Ensure only *dedicated* vCPUs are possible to be real-time vCPUs
* Ensure creating ``mixed`` policy instance properly either by flavor
  settings or by ``resources::PCPU=xx`` and ``resources::VCPU=xx`` settings.
* Ensure *shared* vCPUs is placed before the ``dedicated`` vCPUs
* Ensure the emulator CPU is properly scheduled according to its policy.

Documentation Impact
====================

The documents should be changed to introduce the usage of new ``mixed`` CPU
allocation policy and the new flavor extra specs.

Metadata service will be updated accordingly.

References
==========

* `CPU resource tracking`_

.. _CPU resource tracking: http://specs.openstack.org/openstack/nova-specs/specs/train/approved/cpu-resources.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced, abandoned
   * - Ussuri
     - Re-proposed
