..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================================
libvirt - Store and allow the default machine type to be changed
================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-default-machine-type

Problem description
===================

QEMU's "machine type" concept can be thought of a virtual chipset that
provides certain default devices (e.g. PCIe graphics card, Ethernet
controller, SATA controllae, etc).  QEMU supports two main variants of
"machine type" for x86 hosts: (a) ``pc``, which corresponds to Intel's
I440FX chipset, which is twenty-two years old as of this writing; and
(b) ``q35``, which corresponds to Intel's 82Q35 chipset (released in
2007; a relatively modern chipset).  For AArch64 hosts, the machine type
is called: ``virt``.

The ``pc`` machine type is considered "legacy", and does not support some of
the modern features.  Although at this time of writing, upstream QEMU has not
reached an agreement to remove new versioned variants of the ``pc`` machine
type, some long-term stable Linux distributions (CentOS, RHEL, possibly others)
are moving to support ``q35`` only.

The libvirt virt driver has long supported the configuration of a per compute
host `default machine type`_ via the ``[libvirt]/hw_machine_type`` configurable
for use by QEMU and KVM based instances. This configurable provides a default
machine type per host architecture to be used when no corresponding
``hw_machine_type`` image property is provided for the instance.

When the configurable is not defined the libvirt driver relies on the following
`hardcoded dictionary`_ of default machine types per architecture:

.. code-block:: python

    default_mtypes = {
        obj_fields.Architecture.ARMV7: "virt",
        obj_fields.Architecture.AARCH64: "virt",
        obj_fields.Architecture.S390: "s390-ccw-virtio",
        obj_fields.Architecture.S390X: "s390-ccw-virtio",
        obj_fields.Architecture.I686: "pc",
        obj_fields.Architecture.X86_64: "pc",
    }

However the resulting machine type used by the instance is not recorded by
Nova. As such the configurable (if set) and hardcoded defaults within the
libvirt driver must remain consistent between hosts in an environment *and* can
never be changed without changing the emulated hardware exposed to the guest,
breaking the application binary interface (ABI) of the instances after hard
reboot, move or re-creation operations.

This spec aims to outline how we can avoid this by always storing the machine
type for the lifetime of the instance. This will allow both operators and
developers to make changes to the default machine type over time while not
breaking existing instances.

Use Cases
---------

* As a developer working on the libvirt driver I would like to update the
  default machine type for a given host architecture to make use of newer
  models of emulated hardware and features of QEMU.

* As an operator of an existing OpenStack environment I want to default to a
  new machine type while not breaking the ABI of existing instances.

* As a user I want to ensure the ABI of my instance remains the same throughout
  the lifetime of the instance, regardless of default configurable changes made
  by an operator or virt driver developers.

Proposed change
===============

* Store the used machine type in the instance system metadata table during the
  initial spawn of the instance *or* init_host of the compute service for all
  running instances that don't have a ``hw_machine_type`` already stored.

* Ensure the stored machine type is used during a hard reboot, move or any
  other action that results in the domain being redefined aside from a full
  rebuild of the instance.

* Unset the stored machine type during a rebuild allowing a new image defined
  machine type or host configured default to be used.

* Allow operators to get the machine type of instances via a new
  ``get_machine_type`` ``nova-manage`` command.

* Allow operators to set or update the machine type of instances with a
  vm_state of ``STOPPED``, ``SHELVED`` or ``SHELVED_OFFLOADED`` via a new
  ``update_machine_type`` ``nova-manage`` command.

Alternatives
------------

N/A

Data model impact
-----------------

The machine type will be stored within the ``Instance`` object under the
``system_metadata`` field that is a ``DictOfNullableStringsField`` using the
key ``hw_machine_type``.


REST API impact
---------------

N/A

Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

N/A

Performance Impact
------------------

N/A

Other deployer impact
---------------------

Deployers will now be able to change the default machine type for a given
architecture without changing the underlying ABI presented to existing
instances.

Developer impact
----------------

Libvirt driver developers will now be able to change the default machine type
without changing the underlying ABI presented to existing instances.

Upgrade impact
--------------

When upgrading to Wallaby from Victoria (or earlier) on startup the libvirt
driver will attempt to record the current machine type of each non-deleted
instance residing on the host. This includes ``STOPPED``, ``PAUSED`` and
``SHELVED`` instances.  Where possible this will come from a direct query of
the underlying guest domain but if one is not found it will instead come from
the instance image metadata property ``hw_machine_type``,
``[libvirt]/hw_machine_type`` configurable or legacy hardcoded defaults.

For non-deleted instances that are marked as ``SHELVED_OFFLOADED`` and thus
don't reside on a compute host a ``update_machine_type`` ``nova-manage``
command will be introduced that will allow operators to set a machine
type. As above this will rely first on any stored image properties but if none
is found will require a specific machine type to be provided by the caller.

A ``nova-status`` command will be introduced to allow operators to
determine when all non-deleted instances have had a machine type recorded
across an environment.

While the aliased machine types (``q35`` for example) will be documented as the
recommended choice admins and operators will be allowed to configure a
versioned machine either per image or per architecture on a given compute host.

As a result the same ``update_machine_type`` ``nova-manage`` command used to
set the machine type of ``SHELVED_OFFLOADED`` instances will also be able to
update the machine type of instances with a vm_state of ``STOPPED``,
``SHELVED`` or ``SHELVED_OFFLOADED``.

This will allow operators to migrate instances between these versioned machine
types overtime without a full rebuild of the instance.

It should be noted that by default this command will not allow the machine_type
to be changed between actual types of machine_type, for example ``pc`` to
``q35`` or between a newer and older version of a machine type.

By default both will continue to require a full rebuild of the instance using a
new image with associated ``hw_machine_type`` image property set or once the
``[libvirt]/hw_machine_type`` defaults have been updated on the launching
compute host.

A ``--force`` flag will be inlcuded to allow operators to force through
changes in both cases with a warning that the operation will likely break the
ABI within the instance once restarted.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    lyarwood

Other contributors:

Feature Liaison
---------------

Feature liaison:
    lyarwood

Work Items
----------

* Store the used machine type in the instance extras table during the initial
  spawn of the instance *or* init_host of the compute service for all running
  instances.

* Ensure the stored machine type is used during a hard reboot, move or any
  other action that results in the domain being redefined aside from a full
  rebuild of the instance.

* Unset the stored machine type during a rebuild allowing a new image defined
  machine type or host configured default to be used.

* Introduce a ``get_machine_type`` ``nova-manage`` command to allow operators
  to get the recorded machine_type of an instance.

* Introduce a ``update_machine_type`` ``nova-manage`` command to allow
  operators to set or update the recorded machine_type for a given instance
  with a vm_state of ``STOPPED``, ``SHELVED`` or ``SHELVED_OFFLOADED`` allowing
  upgrades between versioned machine types over time.

* Introduce a ``nova-status`` upgrade check to ensure the machine_type has
  been updated for all instances residing on a given host in the env or across
  all hosts.

* Write extensive operator documentation for the above.

Dependencies
============

N/A

Testing
=======

The ``grenade`` job will be extended to ensure the machine_type field is
being populated during compute service startup when using the libvirt driver.

Documentation Impact
====================

Extensive operator documentation covering the upgrade impact and use of the
configurable will be written.

References
==========

.. _`default machine type`: https://review.opendev.org/#/c/100664/
.. _`hardcoded dictionary`: https://github.com/openstack/nova/blob/dc93e3b510f53d5b2198c8edd22528f0c899617e/nova/virt/libvirt/utils.py#L631-L638
.. _`original spec`: https://review.opendev.org/#/c/631154/7/specs/victoria/approved/q35_qemu_machine_type_as_the_default.rst

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
