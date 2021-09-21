..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================================
Store and allow libvirt instance device buses and models to be updated
======================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-device-bus-model-update

QEMU support for device buses and models can come and go dependent on the
underlying instance machine type *and* QEMU version used within an environment.
The defaults provided by libosinfo and currently hardcoded in to the libvirt
driver are not persisted by each instance at present.

This spec aims to outline a basic set of nova-manage commands to allow
operators to move instances between specific device bus and model types without
requiring a rebuild.

Problem description
===================

At present device bus and model types defined as image properties associated
with an instance are always used when launching instances with the libvirt
driver. When these types are not defined as image properties their values
either come from libosinfo or those directly hardcoded into the libvirt driver.

Support for each device bus and model is dependent on the machine type used
*and* version of QEMU available on the underlying compute host.

As such any changes to the machine type of an instance or version of QEMU on a
host might suddenly invalidate the stashed device bus or model image
properties with no way of updating outside of a complete instance rebuild
against a new image defining new image properties.

Additionally any changes to the defaults provided by libosinfo or the libvirt
driver could result in unforeseen changes to existing instances. This has been
encountered in the past as libosinfo assumes that libvirt domain definitions
are static when OpenStack Nova specifically rewrites and redefines these
domains during a hard reboot or migration allowing changes to possibly occur.

Use Cases
---------

* As a user I want the device buses and models used by my instance to remain
  stable for as long as possible and not be changed by new defaults in
  libosinfo or the OpenStack Nova libvirt driver.

* As an operator I want to change the device bus or model of an instance
  *without* forcing users to fully rebuild the instance in order to accommodate
  changing machine types or QEMU deprecations for certain types.

Proposed change
===============

Register existing device buses and models within ``system_metadata``
--------------------------------------------------------------------

As with ``hw_machine_type`` we first want to ensure the current device bus and
model types associated with an instance are stashed ensuring they remain
stable during the lifetime of the instance. This already happens when these
buses or models are defined by image properties so we only need to capture
their value when these are not defined at either service startup or instance
creation time.

The following list of image properties outline the list of device buses and
models this spec will aim to cover:

* ``hw_cdrom_bus``
* ``hw_disk_bus``
* ``hw_floppy_bus``
* ``hw_input_bus``
* ``hw_pointer_model``
* ``hw_video_model``
* ``hw_vif_model``

.. note::

    ``hw_rng_model``, ``hw_scsi_model`` and ``hw_rescue_bus`` are not included
    here as they have no default values. They must be defined to be used
    negating the need for us to capture them here.

Provide nova-manage commands to update existing device buses and models
-----------------------------------------------------------------------

With the bus and model types stored we can now provide commands to operators to
inspect and update only the list of allowed image properties above:

.. code-block:: shell

    $ nova-manage image-property list $instance

.. code-block:: shell

    $ nova-manage image-property show $instance $property

Will list or show the stashed image properties of an instance.

.. code-block:: shell

    $ nova-manage image-property set \
        --property hw_disk_bus=scsi \
        --property hw_scsi_model=virtio-scsi $instance

Will update image properties of an instance, only accepting the previously
defined list of image properties for the time being.

Prerequisites
~~~~~~~~~~~~~

The following prerequisites apply when attempting to update the image
properties of an instance:

- The instance must be in a STOPPED, SHELVED or SHELVED_OFFLOADED vm_sate.

- The provided type will be validated against the corresponding versioned
  object fields for the bus or model.

Once updated the user or admin can power on or unshelve the instance, causing
the underlying libvirt domain to be redefined using the new bus or model type.

Alternatives
------------

None, other than providing a generic API to allow stashed image properties to
be updated by users over time without requiring a rebuild but that's out of
scope for this basic nova-manage command spec.

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

Users should now find that the device bus and models used by their instances
remain stable throughout their lifetime unless a move is forced upon them
by the operator, QEMU support deprecations etc.

Performance Impact
------------------

Stashing these values will incur a slight overhead at compute service start
time when using the libvirt driver and additionally when spawning new
instances.

Other deployer impact
---------------------

Operators should have more control over when and how they move users to
different machine types and versions of QEMU.

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

Primary assignee:
  lyarwood

Other contributors:


Feature Liaison
---------------

Feature liaison:
  lyarwood

Work Items
----------

* Register existing device buses and models within ``system_metadata``

* Provide nova-manage commands to update existing device buses and models

Dependencies
============

None

Testing
=======

Extensive unit and functional tests will be written to validate this.

Documentation Impact
====================

Operator/admin facing documentation will be written outlining the usecase for
these commands as well as the normal documentation for the commands themselves.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Reproposed
   * - Xena
     - Introduced
