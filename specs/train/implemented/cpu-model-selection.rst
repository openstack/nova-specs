..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Select CPU model from a list of CPU models
==========================================

https://blueprints.launchpad.net/nova/+spec/cpu-model-selection

Problem description
===================

In the libvirt driver, currently we use ``cpu_model`` in ``nova.conf``
(when ``cpu_mode`` is set to ``custom``) to specify the CPU model the
instance should use on this host. This could have implications on
availability of compute nodes for live migration.

* If the instance lands on a compute node which uses an "advanced" CPU model,
  then it may only live-migrate to a few of the cluster's compute nodes or fail
  to live-migrate.

* The admin can configure all compute nodes use the same CPU model. But some
  users may request "advanced" CPU flags for some special application (such
  as video edit and scientific compute).

Use Cases
---------

As an admin, I would like to live-migrate instances among all compute nodes
even if there are different CPU models in the the cluster.

As a user, I would like to boot an instance on a host supporting
specific CPU features and for the instance to be live-migratable to as
many other hosts as possible that also support the instance.

Proposed change
===============

Rename the ``cpu_model`` config attribute with ``cpu_models``, which is
an ordered list of CPU models the host supports. It is expected that the
list is ordered so that the more common and less advanced CPU models are
listed earlier. The reported CPU feature traits will be the union of features
of all the CPU models. Mark ``cpu_model`` is deprecated, so existing confs
will continue to work, but will log a warning.

Note that this is not add a new config attribute, this is rename exist config
attribute and extend it from singular to plural variants. Mark ``cpumodel`` as
deprecated is to maintain capatibility with the old confs. Otherwise,
supporting both the singular and plural variants at the *same* time (or even
after we deprecate ``cpu_model``) could lead to confusion and avoidable typos.
Avoid them.

End users specify CPU features they require through traits [1]_. If the
``cpu_mode`` is set to ``custom``, the libvirt driver will select the first
CPU model in the ``cpu_models`` (combined with
``cpu_model_extra_flags`` if it is specified) that can provide the
required feature traits. This would make it more likely that the
instance could be live-migrated later on. If no CPU feature traits are
specified then the instance will be configured with the first CPU model
in the list.

For example, if the end user specifies CPU features ``avx`` and ``avx2``
as follows::

    openstack flavor set 1 --property trait:HW_CPU_X86_AVX=required --property trait:HW_CPU_X86_AVX2=required


and ``cpu_models`` is configured like this::

    [libvirt]
    cpu_mode = custom
    cpu_models = SandyBridge,IvyBridge,Haswell,Broadwell

then ``Haswell``, the first CPU model supporting both ``avx`` and
``avx2``, will be chosen by libvirt.

If ``cpu_model_extra_flags`` or ``cpu_models`` specified, it should be checked
against each configured items to make sure they are compatible with host CPU.
Any incompatibility should prevent the compute service from starting and force
the user to correct the configuration.

A few related points:

- If both ``cpu_models`` and ``cpu_model`` are set, ``cpu_model``
  will be ignored.

- Typically, data centers only have a handful of CPU generations deployed, so
  the ``cpu_models`` is expected to contain not as many CPUs as shown in
  the contrived example earlier.

- The value in the option ``cpu_models`` will be made case-insensitive.

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
in hardware. If they specify models with CPU features that are emulated by QEMU
it could result in performance degradation.

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

TBD

Work Items
----------

* Conf: Rename ``[libvirt]cpu_model`` to ``[libvirt]cpu_models``.

* Virt driver changes.

* Add/modify unit tests.

Dependencies
============

None

Testing
=======

Add unit tests.


Documentation Impact
====================

Update release note for introducing ``[libvirt]cpu_models``.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/report-cpu-features-as-traits.html

[2] Stein iteration of this spec:
    https://specs.openstack.org/openstack/nova-specs/specs/stein/approved/cpu-model-selection.html

[3] The work in progresss spec to add more "hypervisor-literate" CPU
    APIs to Nova -- https://review.openstack.org/#/c/645814/ ("CPU
    selection with hypervisor consideration")

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
