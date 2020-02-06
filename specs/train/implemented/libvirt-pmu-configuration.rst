..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Libvirt: tenant control of qemu performance monitoring unit (vPMU)
==================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-pmu-configuration

qemu/kvm supports emulation of a vPMU to enable standard performance
monitoring tools such as `Perf <https://perf.wiki.kernel.org/index.php/Main_Page>`_
to be used within a virtualisation environment. The vPMU which is available
on x86 cpus emulates the hardware PMU found on Intel processors and was
introduced in kvm in kernel 3.3.1.

libvirt introduced support for vPMU control in 1.2.12
see https://libvirt.org/formatdomain.html#elementsFeatures
so this feature is available in nova minimum supported libvirt of 1.3.1.

This spec aims to allow tenants to control when the vPMU is enabled.


Problem description
===================

While kvm/qemu support for a vPMU is generally a useful feature the requirement
to collect and maintain virtual performance counter introduces additional
latency of ~10us which is about 1% of the total budget for 5G end to end
traffic processing latency. While this might seem small it is an appreciable
portion of the total latency introduced by virtulisation and is therefore
an important factor in achieving the end to end system latency target.

As the provision of a vPMU is not currently controllable by an operator
or tenant directly this creates a problem for those that want to enable
or disable the vPMU to either avoid the latency overhead or rely on it
to monitor the performance of their workload.

Use Cases
---------

As a telecoms operator building a 5G network I wish to be able to deploy
a virtualised Radio access network (vRAN) applicance with minimal latency
impact from my virtualisation stack.

As a tenant I wish to be able to monitor the performace of my application
using standard tools like perf in a virtualized environment to enable
development, tuning, and profiling of my application.

Proposed change
===============

This spec proposes adding a boolean image metadata key
hw_pmu=True|False and a corresponding flavor extra spec
hw:pmu=True|False to enable/disable the pmu explicitly.

The default value will be unset meaning the property is not present in
either the image or flavor. This will preserve the current behavior.

If the pmu property is set to true then the pmu feature element in the
libvirt xml will be set to on. Similarly if it the pmu property is set
to false the pmu feature element will be set to off.
If the pmu property is not specified no pmu element will be emitted in the
xml allowing qemu to determine if the pmu should be enabled or not.

.. note::

  Currently when not set the pmu is enabled/disabled based on the
  cpu mode and model. If cpu_mode=host-passthough then it will be enabled;
  if a custom cpu model is set it will be disabled.

In addition to the above minimum changes the libvirt driver could be modifed
to report support for a vPMU to improve scheduling. As the vPMU feature
is supported by Nova's minimum required qemu/libvirt this would only be
useful in a heterogeneous cloud. As such the desicion to expose this
feature as a trait is left to the implementation and will be enabled as part
of https://blueprints.launchpad.net/nova/+spec/image-metadata-prefiltering
if desired.


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

The image metadata versioned notification will be extended
to contain the newly added field.

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

If the operator wants to consume this feature they will need to update
their flavors and/or images accordingly.

Developer impact
----------------

None

Upgrade impact
--------------

None

The default behavior when the flavor extra_spec and image metadata
value is unset was chosen to keep backwards compatiblity on upgrade.


Implementation
==============

Assignee(s)
-----------


Primary assignee:
    sean-k-mooney

Work Items
----------

- Extend libvirt driver config module to support the pmu element
- Extend libvirt dirver to enable/disable the feature based on flavor/image
- optionally enable vPMU trait.


Dependencies
============

If we chose to enable the reporting of vPMU emulation as a trait then
the consumption of that trait would depend on the completion of
https://blueprints.launchpad.net/nova/+spec/image-metadata-prefiltering

The general feature has no dependencies

Testing
=======

This will primarily be tested via unit tests of the xml generation
and flavor/image handling code. If the traits support is added
functional test using the libvirt fake driver can also be implemented.

Documentation Impact
====================

The flavor and image docs will need to be extended to document the
new extra_spec.
The Glance metadefs will also be updated to document their use and
supported values.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
