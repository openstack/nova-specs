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

* As a deployer of an existing OpenStack environment I want to default a new
  machine type while not breaking the ABI of existing instances.

* As a user I want to ensure the ABI of my instance remains the same throughout
  the lifetime of the instance, regardless of default configurable changes made
  by deployers or developers.

Proposed change
===============

* Copy the hardcoded machine type defaults from the libvirt driver into the
  ``[libvirt]/hw_machine_type`` configurable.

* Store the used machine type in the instance extras table during the initial
  spawn of the instance *or* init_host of the compute service for all running
  instances that don't have a ``machine_type`` listed at present.

* Allow operators to set the machine_type of ``SHELVE_OFFLOADED`` instances via
  a ``nova-manage`` command.

* Ensure the stored machine type is used during a hard reboot, move or any
  other action that results in the domain being redefined aside from a full
  rebuild of the instance.

* Allow the stored machine_type of a ``SHUTOFF`` instance to be updated by
  an admin/operator via a ``nova-manage`` command. Allowing operators to
  migrate instances between versioned machine types if an alias is not used.

Alternatives
------------

N/A

Data model impact
-----------------

The ``Instance`` object will be extended to include a nullable
``hw_machine_type`` attribute that maps to a simple ``StringField`` stored in
the instance extras table.

A ``StringField`` is used here as we cannot enumerate all of the possible
values of machine_type as different distributions provide different
versioned machine_types. For example Fedora provides machine types versioned by
the underlying QEMU version, while RHEL provides machine types versioned by the
underlying RHEL version::

    $ cat /etc/fedora-release
    Fedora release 33 (Thirty Three)
    $ qemu-system-x86_64 -machine help | grep q35
    q35                  Standard PC (Q35 + ICH9, 2009) (alias of pc-q35-5.1)
    pc-q35-5.1           Standard PC (Q35 + ICH9, 2009)
    pc-q35-5.0           Standard PC (Q35 + ICH9, 2009)
    pc-q35-4.2           Standard PC (Q35 + ICH9, 2009)
    pc-q35-4.1           Standard PC (Q35 + ICH9, 2009)
    pc-q35-4.0.1         Standard PC (Q35 + ICH9, 2009)
    pc-q35-4.0           Standard PC (Q35 + ICH9, 2009)
    pc-q35-3.1           Standard PC (Q35 + ICH9, 2009)
    pc-q35-3.0           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.9           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.8           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.7           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.6           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.5           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.4           Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.12          Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.11          Standard PC (Q35 + ICH9, 2009)
    pc-q35-2.10          Standard PC (Q35 + ICH9, 2009)

    $ cat /etc/redhat-release
    Red Hat Enterprise Linux release 8.2 (Ootpa)
    $ /usr/libexec/qemu-kvm -machine help | grep q35
    q35                  RHEL-8.2.0 PC (Q35 + ICH9, 2009) (alias of pc-q35-rhel8.2.0)
    pc-q35-rhel8.2.0     RHEL-8.2.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel8.1.0     RHEL-8.1.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel8.0.0     RHEL-8.0.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel7.6.0     RHEL-7.6.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel7.5.0     RHEL-7.5.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel7.4.0     RHEL-7.4.0 PC (Q35 + ICH9, 2009)
    pc-q35-rhel7.3.0     RHEL-7.3.0 PC (Q35 + ICH9, 2009)


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
instance residing on the host. This includes ``SHUTOFF``, ``PAUSED`` and
``SHELVED`` instances.  Where possible this will come from a direct query of
the underlying guest domain but if one is not found it will instead come from
the instance image metadata property ``hw_machine_type``,
``[libvirt]/hw_machine_type`` configurable or legacy hardcoded defaults.

For non-deleted instances that are marked as ``SHELVED_OFFLOADED`` and thus
don't reside on a compute host a ``nova-manage`` command will be introduced
that will allow operators/admins to record a machine type. As above this will
rely first on any stored image properties but if non is found will require a
specific machine type to be provided by the caller.

A ``nova-status`` command will be introduced to allow operators/admins to
determine when all non-deleted instances have had a machine type recorded
across an environment.

While the aliased machine types (``q35`` for example) will be documented as the
recommended choice admins and operators will be allowed to configure a
versioned machine either per image or per architecture on a given compute host.

As a result another ``nova-manage`` command will be introduced to update the
machine type of a given ``SHUTOFF`` instance in the DB, allowing operators and
admins to migrate instances between these versioned machine types overtime
without a full rebuild of the instance. It should be noted that this
command will not allow the machine_type to be changed between actual types of
machine_type, for example ``pc`` to ``q35``. This will continue to require a
full rebuild of the instance using a new image with associated
``hw_machine_type`` image property set.

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

* Copy the hardcoded machine type defaults into the
  ``[libvirt]/hw_machine_type`` configurable.

* Store the used machine type in the instance extras table during the initial
  spawn of the instance *or* init_host of the compute service for all running
  instances.

* Ensure the stored machine type is used during a hard reboot, move or any
  other action that results in the domain being redefined aside from a full
  rebuild of the instance.

* Introduce a ``nova-manage`` command to allow operators and admin to set
  the recorded machine_type for non-deleted ``SHELVE_OFFLOADED``
  instances.

* Introduce a ``nova-status`` upgrade check to ensure the machine_type has
  been updated for all instances residing on a given host in the env or across
  all hosts.

* Introduce a ``nova-manage`` command to allow operators and admin to update
  the recorded machine_type for a given instance, allowing upgrades between
  versioned machine types over time.

* Write extensive operator/admin documentation for the above.

Dependencies
============

N/A

Testing
=======

The ``grenade`` job will be extended to ensure the machine_type field is
being populated during compute service startup when using the libvirt driver.

Functional tests should also be written to assert the above and failure
behaviour when attempting to change the default before a machine_type has
been registered for all instances on a given compute.

Documentation Impact
====================

Operator/admin documentation covering the upgrade impact and use of the
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
