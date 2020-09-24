..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Use ``PCPU`` and ``VCPU`` in One Instance
=========================================

https://blueprints.launchpad.net/nova/+spec/use-pcpu-and-vcpu-in-one-instance

The spec `CPU resource tracking`_ splits host CPUs into ``PCPU`` and ``VCPU``
resources, making it possible to run instances of ``dedicated`` CPU allocation
policy and instances of ``shared`` CPU allocation policy in the same host.
This spec aims to create such kind of instance that some of the vCPUs are
dedicated (``PCPU``) CPUs and the remaining vCPUs are shared (``VCPU``) vCPUs
and expose this information via the metadata API.

Problem description
===================

The current CPU allocation policy, ``dedicated`` or ``shared``, is applied to
all vCPUs of an instance. However, with the introduction of
`CPU resource tracking`_, it is possible to propose a more fine-grained CPU
allocation policy, which is based on the control over individual instance vCPU,
and specifying the ``dedicated`` or ``shared`` CPU allocation policy to each
instance vCPU.

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
create a CPU *mixed* instance in such way that some instance vCPUs are
allocated from computing node's ``PCPU`` resource, and the rest of instance
vCPUs are allocated from the ``VCPU`` resources. The CPU allocated from
``PCPU`` resource will be pinned on particular host CPUs which are defined in
``CONF.compute.dedicated_cpu_set``, and the CPU from ``VCPU`` resource will be
floating on the host CPUs which are defined in ``CONF.compute.shared_cpu_set``.
In this proposal, we call these two kinds of vCPUs as *dedicated* vCPU and
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
:ref:`section <mixed-instance-PCPU-VCPU>` and the spec
`CPU resource tracking`_.

Affect over real-time vCPUs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-time vCPU also occupies the host CPU exclusively and does not share CPU
with other instances, all real-time vCPUs are dedicated vCPUs. For a *mixed*
instance with some real-time vCPUs, with this proposal, the vCPUs not in the
instance real-time vCPU list are shared vCPUs.

Affect over emulator thread policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If emulator thread policy is ``ISOLATE``, the *mixed* instance will look for
a *dedicated* host CPU for instance emulator thread, which is very similar
to the case introduced by ``dedicated`` policy instance.

If the emulator thread policy is ``SHARE``, then the instance emulator thread
will float over the host CPUs defined in configuration
``CONF.compute.cpu_shared_set``.

Set dedicated CPU bit-mask in ``hw:cpu_dedicated_mask`` for ``mixed`` instance
------------------------------------------------------------------------------

As an interface to create the ``mixed`` policy instance through legacy flavor
extra specs or image properties, the flavor extra spec
``hw:cpu_dedicated_mask`` is introduced. If the extra spec
``hw:cpu_dedicated_mask`` is found in the instance flavor, then the
information of the *dedicated* CPU could be found through
parsing ``hw:cpu_dedicated_mask``.

Here is the example to create an instance with ``mixed`` policy:

.. code::

    $ openstack flavor set <flavor_id> \
        --property hw:cpu_policy=mixed \
        --property hw:cpu_dedicated_mask=0-3,7

And, following is the proposing command to create a *mixed* instance which
consists of multiple NUMA nodes by setting the *dedicated* vCPUs in
``hw:cpu_dedicated_mask``:

.. code::

    $ openstack flavor set <flavor_id> \
        --property hw:cpu_policy=mixed \
        --property hw:cpu_dedicated_mask=2,7 \
        --property hw:numa_nodes=2 \
        --property hw:numa_cpus.0=0-2 \
        --property hw:numa_cpus.1=3-7 \
        --property hw:numa_mem.0=1024 \
        --property hw:numa_mem.1=2048

.. note::
    Please be aware that there is no equivalent setting in image properties
    for flavor extra spec ``hw:cpu_dedicated_mask``. It will not be supported
    to create *mixed* instance through image properties.

.. note::
    The dedicated vCPU list of a *mixed* instance could be specified through
    the newly introduced dedicated CPU mask or the cpu-time CPU mask, the
    ``hw:cpu_realtime_mask`` or ``hw_cpu_realtime_mask``, you cannot set it
    by setting dedicated CPU mask extra spec and real-time CPU mask at the
    same time.

.. _mixed-instance-PCPU-VCPU:

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
creates the ``dedicated`` or ``shared`` policy instance, that all vCPUs in the
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
specifying the vCPUs that are pinned to the host CPUs chosen from ``PCPU``
resource.

Following extra spec and the image property are defined to keep the
*dedicated* vCPUs of a ``mixed`` policy instance::

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

Add the ``pcpuset`` field in ``InstanceNUMACell`` object to track the dedicated
vCPUs of the instance NUMA cell, and the original ``InstanceNUMACell.cpuset``
is special for shared vCPU then.

This change will introduce some database migration work for the existing
instance in a ``dedicated`` CPU allocation policy, since all vCPUs in such an
instance are dedicated vCPUs which should be kept in ``pcpuset`` field, but
they are stored in ``cpuset`` historically.

REST API impact
---------------

The metadata API will be extended with the *dedicated* vCPU info and a new
OpenStack metadata version will be added to indicate this is a new metadata
API.

The new field will be added to the ``meta_data.json``::

    dedicated_cpus=<cpu set string>

The ``<cpu set string>`` lists the *dedicated* vCPU set of the instance, which
might be the content of ``hw:cpu_dedicated_mask`` or
``hw:cpu_realtime_mask`` or ``hw_cpu_realtime_mask`` or the CPU list
generated with the *round-robin* policy as described in
:ref:`section <mixed-instance-PCPU-VCPU>`.

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

The ``InstanceNUMACell.pcpuset`` is introduced for dedicated vCPUs and the
``InstanceNUMACell.cpuset`` is special for shared vCPUs, all existing
instances in a ``dedicated`` CPU allocation policy should be updated by moving
content in ``InstanceNUMACell.cpuset`` filed to
``InstanceNUMACell.pcpuset`` field. The underlying database keeping the
``InstanceNUACell`` object also need be updated to reflect this change.

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

* Add a new field, the ``pcpuset``, for ``InstanceNUMACell`` for dedicated
  vCPUs.
* Add new instance CPU allocation policy ``mixed`` property and resolve
  conflicts
* Bump nova service version to indicate the new CPU policy in nova-compute
* Add flavor extra spec ``hw:cpu_dedicated_mask`` and create *mixed* instance
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
     - Approved
   * - Victoria
     - Re-proposed
