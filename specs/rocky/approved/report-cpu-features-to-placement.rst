..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Report CPU features to the placement service
============================================

https://blueprints.launchpad.net/nova/+spec/report-cpu-features-as-traits

Traits are already supported by the placement service. All the compute
node's capabilities should be reported to placement using the traits API.
This spec proposes reporting the cpu features of compute node to placement
using traits API.

Problem description
===================

Currently Nova supports scheduling an instance based on the compute node's
CPU features. But it isn't perfect for now.

* There is no consistent naming for the CPU features in all the virt drivers.
  This leads to an inconsistent setup for operators.
* The CPU features of each compute node are stored in a JSON-BLOB of the
  ``compute_nodes`` DB table. It is therefore not possible to efficiently
  query for compute nodes having certain CPU features.
* The flavor extra spec `capabilities` mix the cpu features and other things
  together, and it depends on the virt driver.

Use Cases
---------

* The end user expects a standard and consistent naming for the CPU features
  regardless of the virt driver used by the cloud.
* The end user expects a consistent way to request capabilities for the
  CPU features.

Proposed change
===============

Proposes the compute nodes should report CPU features to placement using the
traits API. The CPU features should map to the CPU traits which are
defined in the os-traits library.

Then the administrator can define the required traits for each flavor in the
extra spec `traits`::

    openstack flavor set 1 --property trait:HW_CPU_X86_AVX=required --property trait:HW_CPU_X86_AVX2=required

The above commands set two CPU features as required for a flavor. It means that
any server booting up with that flavor will be scheduled to the compute node
which has the CPU features `avx` and `avx2`.

Alternatives
------------

If just keep the old way for the scheduling instance based on the cpu features,
there is nothing improvement on the cloud interoperability.

Data model impact
-----------------

None

REST API impact
---------------

No API change, and the original cpu feature reporting to the DB table
`compute_nodes` will be kept for the `/os-hypervisors` API backward compatible.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The ends user should use the extra spec `traits` in the flavor instead of the
extra spec `capabilities:cpu_info:features` to define required CPU features.

Performance Impact
------------------

None

Other deployer impact
---------------------

It will be possible to deprecate and remove the `ComputeCapabilitiesFilter`
once all virt drivers are reporting CPU features consistently using traits.

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Each virt-driver should attach CPU traits to the compute node's resource
provider in the method `update_provider_tree()`.

Libvirt
-------

The configure option `CONF.libvirt.cpu_mode` and `CONF.libvirt.cpu_model` can
change the CPU features exposed to the guest. The libvirt virt-driver should
only return the CPU features which are available to the guest.

The reported CPU features are based on the guest CPU model. The CPU model will
be determined by the table as below::

  +-----------------------+------------------------+------------------+
  | CONF.libvirt.cpu_mode | CONF.libvirt.cpu_model | Guest CPU model  |
  +-----------------------+------------------------+------------------+
  | none                  | N/A                    | qemu64           |
  | host-model            | N/A                    | host cpu model   |
  | host-passthrough      | N/A                    | host cpu model   |
  | custom                | custom cpu model       | custom cpu model |
  +-----------------------+------------------------+------------------+

For the libvirt virt driver, the ``virConnectBaselineCPU`` libvirt API call
to query for CPU model and translate the model into CPU features. Other virt
drivers can use similar calls in their virt APIs to determine CPU features.

There is no same configuration for other virt drivers. For other virt drivers,
they will report CPU traits same as the current way.

Assignee(s)
-----------

Primary assignee:
  Alex Xu <hejie.xu@intel.com>

Other contributors:
  Lei Zhang <lei.a.zhang@intel.com>

Work Items
----------

* Implement an interface which returns a list of traits for the CPU features
  in each virt driver.
* Implement report CPU traits to the compute node resource provider in the
  `update_provider_tree()` method.

Dependencies
============

N/A

Testing
=======

The related unit-tests and functional tests are required.

Documentation Impact
====================

In the administrator guideline to explain how to use traits to define the
required CPU features.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
