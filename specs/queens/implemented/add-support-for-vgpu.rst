..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Support virtual GPU resources
=============================

https://blueprints.launchpad.net/nova/+spec/add-support-for-vgpu

Add support for virtual GPU (vGPU) resources.

Problem description
===================

With some graphics virtualization solutions e.g. `Intel's GVT-g`_ and
`NVIDIA GRID vGPU`_, a single physical Graphics Processing Unit (pGPU)
can be virtualized as multiple virtual Graphics Processing Units (vGPU).
Some hypervisors support to boot VMs with vGPU to accelerate graphics
processing. But presently Nova can't support vGPU.

The compute node may have one or multiple pGPUs and each pGPU could support
multiple vGPUs. Some pGPUs (e.g. NVIDIA GRID K1) support several different
vGPU types and each vGPU type has a fixed amount of frame buffer, number of
supported display heads and maximum resolutions and are targeted at different
classes of workload. Due to their different resource requirements, the maximum
number of vGPUs that can be created simultaneously on a pGPU varies
according to the vGPU type.

The following are examples for different vGPU types:

.. rubric:: Example 1: vGPUs on NVIDIA GRID K1

::

 +----------------+---------------------------------------+
 | Card Type      | NVIDIA GRID K1                        |
 +----------------+---------------------------------------+
 | No. of pGPUs   | 4                                     |
 +----------------+---------------------------------------+
 | FB size (MB)   | 4096  | 2048  | 1024  | 512   | 256   |
 +----------------+-------+-------+-------+-------+-------+
 | Max heads      |   4   |  4    |  2    |  2    |  2    |
 +----------------+-------+-------+-------+-------+-------+
 | vGPU model     | K180Q | K160Q | K140Q | K120Q | K100  |
 +----------------+-----------------------+---------------+
 | Max Resolution |    2560x1600          |   1920x1200   |
 +----------------+-----------------------+---------------+
 | vGPUs per GPU  |  1    |  2    | 4     | 8     | 8     |
 +----------------+-------+-------+-------+-------+-------+

.. rubric:: Example 2: Intel GVT-g vGPUs on Intel(R) Xeon(R) CPU E3-1285 v4

::

 +----------------+------------------------------------+
 | pGPU model     | Iris Pro Graphics P6300            |
 +----------------+------------------------------------+
 | vGPU model     | Intel GVT-g                        |
 +----------------+------------------------------------+
 |Framebuffer size| 128 MB                             |
 +----------------+------------------------------------+
 | Max heads      | 1                                  |
 +----------------+------------------------------------+
 | Max Resolution | 1920x1080                          |
 +----------------+------------------------------------+
 | No. of vGPUs   |                                    |
 |    per GPU     | 7                                  |
 +----------------+------------------------------------+

In this spec, we will define a model to track vGPU resources.

Use Cases
----------

* As a cloud administrator, I should be able to define flavors which request
  an amount of vGPU resources.

* As a cloud administrator, I should be able to specify the supported display
  heads number and resolutions for vGPUs defined in the flavors; end users can
  choose a proper flavor with the expected performance.

* As a cloud administrator, I should be able to define flavors which request
  vGPUs that support some special features e.g. `OpenGL`_ to achieve
  hardware-accelerated rendering.

* As an end user, I should be allowed to boot VMs which have vGPUs by using
  the pre-defined flavor.

Proposed change
===============

* Define resource tracking model for vGPU: There are both **quantitative**
  and **qualitative** aspects need to be tracked for vGPU resources.

  * Tracking **quantitative** aspects of the vGPU resource:

    * Define a new standard resource class `resource-classes`_ to track the
      amount of vGPUs (``ResourceClass.VGPU``) in the resource providers.

    * Generate the resource provider(RP) tree to track the amount of vGPUs
      available. The resource tracking model is as the following::

       resource provider:                  compute_node
                                       /        |          \
       resource provider:            RP_1      RP_2   ...  RP_n
                                    /           |             \
       inventory:          vGPU_inv_1       vGPU_inv_2  ...  vGPU_inv_n

      In virt driver (in the function of ``get_inventory()``), it would ask
      the hypervisor to get the existing pGPUs, their capacity for vGPUs.
      With the inventory data, virt driver makes resource providers for each
      pGPU or each pGPU group (depend on how the pGPUs are managed by
      hypervisors). These resource providers will be associated as the
      compute_node's children[`nested-resource-providers`_].

      * *RP for GPU*: For example, libvirt will report the available vGPU
        number for each pGPU. In this way, if there are multiple pGPUs (same
        model), it can create one type of vGPUs on a pGPU and create other
        types of vGPUs on the remaining pGPUs.

      * *RP for pGPU group*: XenServer uses pGPU groups to manage pGPUs. A
        pGPU group is a collection of pGPUs which belong to the same model.
        On creating vGPU, it will search the target group for a GPU which can
        supply the requested vGPU. In another word, **it is not possible to
        specify which pGPU the vGPU to be created on**. So XenAPI (the virt
        of XenServer) should make RP for each pGPU group. And the amount of
        in the inventory should be total number of vGPUs which can be supplied
        by pGPUs belong the group.

      As described above, some pGPUs (e.g. NVIDIA GRID K1) support different
      sized vGPU types. The capacity for different vGPU types varies. In order
      to make resource tracking easier, we need to make sure the number of the
      vGPU is predictable. So we will add a new whitelist in nova.conf to
      specify the enabled vGPU types to ensure each resource provider of vGPUs
      only has one type of vGPUs. The whitelist is defined as the following::

       enabled_vgpu_types = [ str_vgpu_type_1, str_vgpu_type_2, ... ]

      Note: the str_vgpu_type_x is a string representing a vGPU type. Different
      hypervisors may expose the vGPU types with different strings. The virt
      driver should handle that properly and map the whitelist to the correct
      vGPUs types.

      For example, NVIDIA's vGPU type M60-0B is exposed with the type id:
      "nvidia-11" in libvirt; but that's exposed in XenServer with the type name:
      "GRID M60-0B". If we want to enable this vGPU type,

      * the whitelist when libvirt is the hypervisor should be:

        .. code::

           enabled_vgpu_types = [ "nvidia-11" ]

      * the whitelist when XenServer is the hypervisor should be:

        .. code::

           enabled_vgpu_types = [ "GRID M60-0B" ]

      The vGPU resource number should be 8 (4 GPU per card * 2 vGPU per GPU).
      The inventory data for the resource provider for vGPUs should be as:

      .. code::

         {
             obj_fields.ResourceClass.vGPU: {
                 "total": 8,
                 "reserved": 0,
                 "min_unit": 1,
                 "max_unit": 1,
                 "step_size": 1,
                 "allocation_ratio": 1.0
             },
         }

  * Tracking **qualitative** aspects of the vGPU resources:

    * The feature of traits is targeted to support representing *qualitative*
      aspects for resources to differentiate their characteristics[`os-traits`_].

    * GPUs also have different characteristics. We define traits for GPUs
      in os-traits[`gpu-traits`_]: include `maximum display heads`,
      `resolutions`, `features`. In virt driver, it should query for the
      `qualitative` aspects of the vGPU resources; map them to the defined
      traits and associate these traits to the resource providers.

* Define flavor: allow the cloud administrator to create different flavors
  to specify the required amount of vGPU and/or a set of required traits to
  meet different users' demands.

* Scheduler: Basing on the amount of vGPU and the required traits, the resource
  providers which can meet the conditions will be filtered out.

* At spawning an instance, the virt drivers should retrieve the vGPU
  resource specs from the instance request specs and map them to the proper
  information (e.g. the GPU group in XenAPI) which is needed to create a vGPU;
  then create and/or associating vGPU to the instance.

Alternatives
------------

* It has been attempted to support vGPU by creating fake SRIOV-VF PCIs for
  vGPUs and then passthrough PCI devices `vGPU-passthrough-PCI`_. But there is
  problem to populate the fake PCI's address. And it can't reflect the real
  situation that some vGPUs are not really PCI devices.

Data model impact
-----------------

No particular data model changes needed, but it depends on the data model
defined in `custom-resource-classes`_ and `nested-resource-providers`_.

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

In order to enable the vGPU feature:

* the operators should change the nova configure settings to enable the vGPU
  type for each pGPU model which will provide vGPU capabilites.

* the operators should create new or update existing flavors to specify the
  amount of vGPU to be requested, and other expected traits (e.g. the dispaly
  resolutions, display heads, features), so that users can use different flavor
  to request vGPUs basing on their graphics processing demands.

* for rolling upgrads, the operators should create or update flavors requesting
  vGPU after they rolled out all of their nodes into release where this spec
  got implemented.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jianghuaw

Other contributors:

Work Items
----------

* Define standard traits into os-traits for GPUs;

* In virt driver, add code to:

  * add whitelist for enabled vGPU types in the config file

  * query needed data for enabled vGPU types

  * generate the nested resource providers

  * generate the inventory data in resource providers

  * mapping GPU characteristics to the traits defined in os-traits

  * associate these traits to the resource providers

  * mapping traits in the boot request spec to the required metadata

  * create or/and attach vGPU to the instance basing on the metadata

Dependencies
============
This spec depends on the following specs to be implemented:

* custom-resource-classes-pike: https://blueprints.launchpad.net/nova/+spec/custom-resource-classes-pike

* nested-resource-providers: https://specs.openstack.org/openstack/nova-specs/specs/ocata/approved/nested-resource-providers.html

* resource-provider-traits: https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/resource-provider-traits.html

Testing
=======

* Unit tests.

Documentation Impact
====================

Need document the configuration for vGPU.

References
==========

.. _Intel's GVT-g: https://01.org/igvt-g

.. _NVIDIA GRID vGPU: http://images.nvidia.com/content/grid/pdf/GRID-vGPU-User-Guide.pdf

.. _resource-classes: http://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/resource-classes.html

.. _custom-resource-classes: https://blueprints.launchpad.net/nova/+spec/custom-resource-classes

.. _resource-provider: https://specs.openstack.org/openstack/nova-specs/specs/mitaka/approved/resource-providers.html

.. _resource-provider-traits: https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/resource-provider-traits.html


.. _Resource-providers-scheduler: https://blueprints.launchpad.net/nova/+spec/resource-providers-scheduler-db-filters

.. _nested-resource-providers: https://specs.openstack.org/openstack/nova-specs/specs/ocata/approved/nested-resource-providers.html

.. _OpenGL: https://en.wikipedia.org/wiki/OpenGL

.. _vGPU-passthrough-PCI: https://review.openstack.org/#/c/280099/17

.. _os-traits: http://docs.openstack.org/developer/os-traits

.. _gpu-traits: https://github.com/openstack/os-traits/tree/master/os_traits/hw/gpu

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced

