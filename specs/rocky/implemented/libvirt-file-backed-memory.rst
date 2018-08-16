..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Libvirt file backed memory
==========================================

Spec for blueprint libvirt-file-backed-memory
https://blueprints.launchpad.net/nova/+spec/libvirt-file-backed-memory

With the advent of large capacity memory devices, it's now reasonable to run
virtual machines with file backed memory. This enables a much larger total
memory area per compute node

Problem description
===================

New memory technology and modern NVMe SSDs have progressed to the point where
it is reasonable to utilize these devices as a backing store for VM memory to
expand the memory capacity of a compute host.

Use Cases
---------

As an operator, I want to be able to leverage libvirt's support for
file-backed memory technologies to expand my compute node memory capacity.

Proposed change
===============

The proposed change is to add a new option in ``nova.conf`` under the
``libvirt`` section to configure file backed memory:

* ``file_backed_memory``

``file_backed_memory`` will default to ``0``, indicating file backed memory is
disabled. When set to non-zero, the libvirt driver will include elements
to enable file backed memory within instances.

When ``file_backed_memory`` is set to non-zero, the libvirt driver will
include a ``MemoryBacking`` element for all instances on the compute node,
with a ``source`` subelement with type ``file``, and an ``access`` subelement
with mode ``shared``.

The value configured in ``file_backed_memory`` will be reported by the libvirt
driver as the total memory capacity of the compute node in MiB. As the memory
capacity is dependent on the backing store(s) in use, libvirt must report a
value other than the real system memory capacity. Available capacity will then
be calculated from the value in ``file_backed_memory`` minus the currently
used memory for instances. System memory will be used as a cache for the file
backed memory through the kernel pagecache.

As overcommit is not expected to work with file backed memory, enabling this
option requires the value of ``ram_allocation_ratio`` in ``nova.conf``, to be
set to the value ``1.0``, and will block Nova startup if this is not
configured properly.

.. note:: ``shared`` access mode is required, as ``private`` access will not
          utilize an underlying backing store for pages in-use by the
          instance, but will keep those pages within main system memory.

.. note:: During migration, the destination compute node must be checked for
          the ``file_backed_memory`` option, and add or remove the
          MemoryBacking element and subelements as appropriate, to
          ensure memory is appropriately allocated during the migration
          process. This can be in nova/virt/libvirt/migration.py, within the
          get_updated_guest_xml method, similar to how graphics, serial,
          volume, and perf events are handled today.

.. note:: Migration from compute nodes running versions of Nova without this
          feature will not include the appropriate libvirt XML for
          file backed memory. Nova will block these migrations, to ensure
          all instances migrated to a node with ``file_backed_memory`` enabled
          are actually using file backed memory. Migrations will be blocked
          within ``check_can_live_migrate_destination``

Alternatives
------------

In Nova, the available memory capacity could be detected dynamically. Due to
the variety of memory and SSD technologies and ways the memory backing
directory could be configured within libvirt and on the system, this would
require implementing an external call point to determine the available
capacity, or require vendor-specific code included in Nova. Either option
would significantly increase the scope of this spec.

In Nova, file backed memory could be enabled via a flavor extra-spec, allowing
for control per individual instance. This results in an inconsistent use of RAM
and backing devices, leading to a confusing / conflicting memory capacity
calculation on the compute node.

Not implement this spec at all. In this case, a compute node is limited to
the capacity of the standard DRAM in the compute node.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

As the instance memory will now be contained within a file on a filesystem,
instance memory will be accessible to any process owned by a user with
permissions necessary to access the files. Currently, the root user on a
compute node already has capability to read system memory and VM memory.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

When the ``file_backed_memory`` option is enabled, instance memory performance
will be dependent on the backing store, as configured by the operator.

Other deployer impact
---------------------

New config options would need to be explicitly enabled to take effect.

Prior to enabling new config options, an operator should configure the libvirt
``memory_backing_dir`` configuration setting to point to their selected backing
store, such as a filesystem on an NVMe device.

Enabling ``file_backed_memory`` will reject migrations from compute nodes
running versions of Nova that do not support file backed memory.

Developer impact
----------------

None

Upgrade impact
--------------

Enabling ``file_backed_memory`` will reject migrations from compute nodes
running versions of Nova that do not support file backed memory.

It's recommended to only enable ``file_backed_memory`` after all compute nodes
are upgraded.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zack Cornelius <zcornelius>

Other contributors:
  None

Work Items
----------

* Add new configuration options to nova.conf
* Check for configuration options within libvirt driver and report the
  file-backed capacity value instead of system memory
* Generate additional libvirt domain XML as needed
* Validate / correct libvirt domain XML during migration process

Dependencies
============

- Qemu >= 2.6.0
- Libvirt >= 4.0.0

Testing
=======

Unit tests will be added to validate the instances booted on host have files
in the libvirt ``memory_backing_dir`` on the host.

A test will be needed for the edge cases of migrating between a host with the
new options enabled, and a host without the new options enabled, to ensure the
memory is allocated from the correct source.

We will investigate adding an integration test for this by creating a large
ramdisk, enabling these settings, and validating that an instance is utilizing
memory within files on that ramdisk. We believe this test layout should be
possible, but if not, will fall back to relying on unit tests.

Documentation Impact
====================

The documentation for ``nova.conf`` should be updated with the new
configuration options.

References
==========

* https://libvirt.org/formatdomain.html#elementsMemoryBacking

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
