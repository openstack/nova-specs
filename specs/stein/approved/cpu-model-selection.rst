..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Select cpu model from a list of cpu models
==========================================

https://blueprints.launchpad.net/nova/+spec/cpu-model-selection

Problem description
===================

In the libvirt virt driver, currently we use cpu_model in nova.conf (when
cpu_mode is set to ``custom``) to specify the CPU model the instance should
use on this host. This could have implications on availability of compute
nodes for live migration if you ended up with an ``advanced`` CPU model when
all you really cared about was an older feature flag.

Use Cases
---------

As a user, I would like to boot an instance on a host supporting specific CPU
features and for the instance to be live-migratable to as many other hosts as
possible that also support the instance.

Proposed change
===============

Replace ``cpu_model`` with ``cpu_models`` which is an ordered list of CPU
models the host supports. It is expected that the list is ordered so that the
more common and less advanced CPU models are listed earlier. The reported cpu
feature traits will be the union of features of all the cpu models.

End users specify CPU features they required through traits [1]_. If the
``cpu_mode`` is set to *custom*, libvirt driver will select the first CPU model
in the ``cpu_models`` list (combined with ``cpu_model_extra_flags`` if it is
specified) that can provide the required feature traits. This would make it
more likely that the instance could be live-migrated later on. If no CPU
feature traits are specified then the instance will be configured with the
first CPU model in the list.

For example, if the end user specifies CPU features avx and avx2 as following::

    openstack flavor set 1 --property trait:HW_CPU_X86_AVX=required --property trait:HW_CPU_X86_AVX2=required


and ``cpu_models`` is configured like this::

    [libvirt]
    cpu_mode = custom
    cpu_models = Conroe,Penryn,Nehalem,Westmere,SandyBridge,IvyBridge,Haswell,Broadwell,Skylake-Client,Skylake-Server

then ``Haswell``, the first cpu model supporting both avx and avx2 will be
chosen by libvirt.

If ``cpu_model_extra_flags`` is specified, it should be checked against each
cpu model in the ``cpu_models`` list using host.compare_cpu() to make sure it
is compatible with *all* models in the ``cpu_models`` list. Any incompatibility
should prevent compute host from starting and user needs to correct the
configuration.

If both ``cpu_models`` and ``cpu_model`` are set, ``cpu_model`` will be
ignored.

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

Negligible.


Other deployer impact
---------------------

Add some information in the config option help text indicating that the
operator should be careful to only specify models which can be fully supported
in hardware. If they specify models with CPU features that are emulated by qemu
it could result in performance degredation.

Developer impact
----------------

None

Upgrade impact
--------------

The operator needs to set the config option appropriately after an upgrade.
If cpu_models is not set it should default to the value of cpu_model.

Implementation
==============

Assignee(s)
-----------

TBD

Work Items
----------

* Conf: define ``[libvirt]cpu_models``. ``[libvirt]cpu_model`` is deprecated.

* Virt driver changes.

* Add/modify unit tests.

Dependencies
============

None

Testing
=======

Will add unit tests.


Documentation Impact
====================

Update release note for introducing [libvirt]cpu_models.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/report-cpu-features-as-traits.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
