..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add maxphysaddr support for Libvirt
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-maxphysaddr-support

This blueprint propose new flavor extra_specs to control the physical
address bits of vCPUs in Libvirt guests.

Problem description
===================

When booting a guest with 1TB+ RAM, the default physical address bits are
too small and the boot fails [1]_. So a knob is needed to specify the
appropriate physical address bits.

Use Cases
---------

Booting a guest with large RAM.

Proposed change
===============

In Libvirt v8.7.0+ and QEMU v2.7.0+, physical address bits can be specified
with following XML elements [2]_ [3]_. The former means to adopt any physical
address bits, the latter means to adopt the physical address bits of the
host CPU.

- ``<maxphysaddr mode='emulate' bits='42'/>``
- ``<maxphysaddr mode='passthrough'/>``

Flavor extra_specs
-----------------------------------------------

Here I suggest the following two flavor extra_specs.
Of course, if these are omitted, the behavior is the same as before.

- ``hw:maxphysaddr_mode`` can be either ``emulate`` or ``passthrough``.
- ``hw:maxphysaddr_bits`` takes a positive integer value.
  Only meaningful and must be specified if ``hw:maxphysaddr_mode=emulate``.

Nova scheduler changes
----------------------

Nova scheduler also needs to be modified to take these two properties
into account.

There can be a mix of supported and unsupported hosts depending
on Libvirt and QEMU versions. So add new traits
``COMPUTE_ADDRESS_SPACE_PASSTHROUGH`` and ``COMPUTE_ADDRESS_SPACE_EMULATED``
to check the scheduled host supports this feature.
``trait:COMPUTE_ADDRESS_SPACE_PASSTHROUGH=required`` is automatically added
if ``hw:maxphysaddr_mode=passthrough`` is specified in flavor extra_specs.
And same for ``hw:maxphysaddr_mode=emulate``.

Passthrough and emulate modes have different properties. So let's consider
the two separately.

The case of ``hw:maxphysaddr_mode=passthrough``. In this case,
``cpu_mode=host-passthrough`` is a requirement, which is already taken
into account in nova scheduling, and no additional modifications are
required in this proposal. It is not guaranteed whether the instance
can be migrated by nova. So the admin needs to make sure that targets
of cold and live migration have similar hardware and software.
This restriction is similar for ``cpu_mode=host-passthrough``.

The case of ``hw:maxphysaddr_mode=emulate``. In nova scheduling,
it is necessary to check that the hypervisor supports at least
``hw:maxphysaddr_bits``. The maximum number of bits supported by
hypervisor can be obtained by using libvirt capabilities [4]_. Therefore,
``ComputeCapabilitiesFilter`` can be used to compare the number of bits in
scheduling.  For example, this can be accomplished by adding
``capabilities:cpu_info:maxphysaddr:bits>=42`` automatically.
Cold migration and live migration can also be realized with this filter
and ``COMPUTE_ADDRESS_SPACE_EMULATED`` trait.
So the overall flavor extra_specs look like the following::

  openstack flavor set <flavor> \
    --property hw:maxphysaddr_mode=emulate \
    --property hw:maxphysaddr_bits=42

.. note:: Since ComputeCapabilitiesFilter only supports flavor extra_specs
          and not image properties [5]_, this proposal is out of scope for
          image properties.

Alternatives
------------

Before the ``maxphysaddr`` option was introduced into Libvirt, it was specified
as a workaround with the QEMU comanndline parameter. But this alternative is
not allowed in nova.

Also, some Linux distributions may have machine types with
``host-phys-bits=true`` [6]_. For example, ``pc-i440fx-bionic-hpb`` and
``pc-q35-bionic-hpb``. However, this alternative has following two issues and
cannot be adopted for general-purpose use cases.

- Ubuntu package maintainers are applying a patch to QEMU [7]_. It means this
  is not included in vanilla QEMU and is not available in other distributions.
- This is only the case for ``hw:maxphysaddr_mode=passthrough`` and does not
  include ``hw:maxphysaddr_mode=emulate``. Since
  ``hw:maxphysaddr_mode=passthrough`` requires ``cpu_mode=host-passthrough``
  to be used [8]_, this alternative cannot be used with ``cpu_mode=custom``
  or ``cpu_mode=host-model``. So, this alternative is not sufficient for
  a cloud with many different CPU models.

As for scheduling, placement does not currently support numeric traits,
so the maximum number of bits supported by hypervisor cannot be checked
by this mechanism.

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

None

Other deployer impact
---------------------

Operators should specify appropriate flavor extra_specs as needed.

Developer impact
----------------

None

Upgrade impact
--------------

As described earlier, the new traits ``COMPUTE_ADDRESS_SPACE_PASSTHROUGH`` and
``COMPUTE_ADDRESS_SPACE_EMULATED`` signal if the upgraded compute nodes support
this feature.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  nmiki

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  Liaison Needed

Work Items
----------

* Add new guest configs
* Add new fileds in nova/api/validation/extra_specs/hw.py
* Add new fields in LibvirtConfigCPU in nova/virt/livbirt/config.py
* Add new traits to check Libvirt and QEMU versions
* Add new field ``maxphysaddr`` to ``cpu_info`` in nova/virt/libvirt/driver.py
* Add docs and release notes for new flavor extra_specs

Dependencies
============

Libivrt v8.7.0+.
QEMU v2.7.0+.

Testing
=======

Add the following unit tests:

- check that proposed flavor extra_specs are properly validated
- check that intended XML elements are output
- check that traits are properly added and used
- check that new field in ``ComputeCapabilitiesFilter`` is property
  added and used

Documentation Impact
====================

For operators, the documentation describes what proposed flavor extra_specs
mean and how they should be set.

References
==========

.. [1] https://bugs.launchpad.net/ubuntu/+source/libvirt/+bug/1769053
.. [2] https://libvirt.org/news.html#v8-7-0-2022-09-01
.. [3] https://github.com/libvirt/libvirt/commit/1c1a7cdd4096c59fb0c374529e1e5aea8d43ee9c
.. [4] https://libvirt.org/formatcaps.html#examples
.. [5] https://docs.openstack.org/nova/latest/admin/scheduling.html#computecapabilitiesfilter
.. [6] https://cpaelzer.github.io/blogs/005-guests-bigger-than-1tb/
.. [7] https://git.launchpad.net/~paelzer/ubuntu/+source/qemu/commit/?id=6ba8b5c843d405e1b067dc8b98ecb8545af78a2b
.. [8] https://github.com/libvirt/libvirt/blob/v8.7.0/src/qemu/qemu_validate.c#L346-L351

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
