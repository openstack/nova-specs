..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
support live migration with virtual persistent memory
=====================================================

https://blueprints.launchpad.net/nova/+spec/support-live-migration-with-virtual-persistent-memory

Live migration with virtual persistent memory (``vpmem`` for short) is
supported by QEMU and Libvirt. This spec seeks to enable this support in
OpenStack Nova.

Problem description
===================

Basic functions for virtual persistent memory are supported in OpenStack Nova
from Train release, including resource tracking and creating/resizing instance
with virtual persistent memory, etc. See `virtual persistent memory spec`_.
Pre-copy live migration with virtual persistent memory is supported by QEMU
and Libvirt, post-copy with vpmem is not supported, so this spec seeks to
enable pre-copy live migration with vpmem.

Currently vpmems are stored in instance.resources as ResourceMetadata object,
or stored in migration_context when migrating. As far as Nova concerned,
several problems need to be addressed:

* Disable post-copy live migration with vpmem even if post-copy is enabled
  by nova configration
* Claim resources from placement when migrating
* Assign specific resources to instance according to the allcations from
  placement and track them
* Prepare dest xml on the source host, which is used to launch live migration,
  that means we need to bring the resources info claimed on dest host to
  source host
* vpmem resources need cleanup correctly after live migration successes/fails

Use Cases
---------
Administrator needs the virtual persistent memory data migrated correctly
during live migration.

Proposed change
===============
* Nova Conductor:
  if we specify parameter 'host' and 'force' for live migration, current
  code will firstly assign specific resources to instance on dest host and
  then claim resources from placement, we need reverse the order since we rely
  on allocations getting from placement to assign specific resources, which is
  also our proposed change in following Nova compute.
  Before live migration starts, we need check and reject vpmem live migration
  if the source host or dest host doesn't support live migration with vpmem.

* Nova Compute:
  use resource tracker to assign and track specific resources on
  the dest host according to the allocations from placement, and stored in
  instance.migration_context (reuse the code introduced by vpmem resize
  implementation)

* Libvirt Driver change for vpmem post-copy disable:
  if the instance has vpmems, disable the post-copy live migration even if
  post-copy is enabled by Nova configration

* Libvirt Driver change for vpmem xml:
  prepare dest xml on source host for live migration, update the dest virtual
  persistent memory info into dest xml

* Libvirt Driver change for vpmem cleanup:
  If live migration fails, rollback_live_migration_at_destination will cleanup
  vpmems from instance.resources, but instance.resources is still pointing at
  the resources on source host. There are other similar cleanup issues.
  We can pass one more parameter to driver.cleanup to tell this cleanup is on
  source/dest host. Alternatively, we can use the mutated_migration_context
  to switch instance.resources to new resources on dest host temporarily. It's
  implementation detail which should be determined when coding.
  In a word, we should be careful about vpmem cleanup, especially during
  migration.

Alternatives
------------
None

Data model impact
-----------------
We are using the existing instance.migration_context bring the dest vpmems info
to source host.

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
In virtualization layer, QEMU will copy vpmem over the network like volatile
memory. But due to the typical large capacity of vpmem, it may takes longer
time for live migration. If the instance workloads was actively writing to
the vpmem, the live migration might never complete which goes for standard
memory as well.

Other deployer impact
---------------------
None

Developer impact
----------------
None

Upgrade impact
--------------
Both source and dest host needs upgrade, then live migration with vpmem will
be supported, otherwise it will be rejected.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  luyaozhong

Other contributors:
  xuhj
  rui-zang

Feature Liaison
---------------
luyaozhong

Work Items
----------
* implement virtual persistent memory live migration management in Nova
* get 3rd party CI tests ready

Dependencies
============
* Kernel version >= 4.2
* QEMU version >= 3.1.0
* Libvirt version >= 5.0.0
* ndctl version >= 62
* daxio version >= 1.4.1

Testing
=======
* unittests
* Third party CI is required for testing on real hardware. For existing virtual
  persistent memory feature in Nova, there are 2 tempest tests, creating and
  same host resizing running in the 3rd party CI. Besides, multinode cold
  migration, live migration, and shelve/unshelve tests are required.

Documentation Impact
====================
Update virtual persistent memory document in Nova "advanced configuration" to
notify administrator that live migration with virtual persistent memory is
supported in Nova.

References
==========

.. _`virtual persistent memory spec`: https://specs.openstack.org/openstack/nova-specs/specs/train/approved/virtual-persistent-memory.html


History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
