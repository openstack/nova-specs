..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
libvirt: Supporting multiple vGPU types for a single pGPU
=========================================================

https://blueprints.launchpad.net/nova/+spec/vgpu-rocky

`Virtual GPUs in Nova`_ was implemented in Queens but only with one supported
GPU type per compute node. Now that `Nested Resource Providers`_ is a thing,
this spec is discussing about how to have one supported vGPU type *per physical
GPU* (given a GPU card can have multiple physical GPUs).

.. note::
   As Xen provides a specific feature where physical GPUs supporting same vGPU
   type are within a single pGPU group, that virt driver doesn't need to know
   which exact pGPUs need to support a specific type, hence this spec only
   targets the libvirt driver.

.. _`Virtual GPUs in Nova`: https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/add-support-for-vgpu.html
.. _`Nested Resource Providers`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html

Problem description
===================

Hardware vendors tell us that a physical GPU device can support multiple types.
That said, Intel (to be confirmed) and NVidia vendor drivers only accept one
type for all the virtual devices *per graphical processing unit*.

For example, NVidia GRID physical cards can accept a list of different GPU
types, but the driver can only support `one type per physical GPU`_.

.. figure:: http://docs.nvidia.com/grid/5.0/grid-vgpu-user-guide/graphics/sample-vgpu-configurations-grid-2gpus-on-card.png

.. _`one type per physical GPU`: http://docs.nvidia.com/grid/5.0/grid-vgpu-user-guide/index.html#homogeneous-grid-vgpus

Consequently, we require a way to instruct the libvirt driver which vGPU types
an NVIDIA or Intel physical GPU is configured to accept.

Use Cases
---------

An operator needs a way to inform the libvirt driver which vGPU types an
NVIDIA or Intel physical GPU is configured to accept.

Proposed change
===============

We already have ``[devices]/enabled_vgpu_types`` that define which types the
Nova compute node can use:

.. code::

  [devices]
  enabled_vgpu_types = [str_vgpu_type_1, str_vgpu_type_2, ...]

Now we propose that libvirt will accept configuration sections that are related
to the [devices]/enabled_vgpu_types and specifies which exact pGPUs are related
to the enabled vGPU types and will have a ``device_addresses`` option defined
like this:

.. code::

  cfg.ListOpt('device_addresses',
              default=[],
              help="""
  List of physical PCI addresses to associate with a specific GPU type.

  The particular physical GPU device address needs to be mapped to the vendor
  vGPU type which that physical GPU is configured to accept. In order to
  provide this mapping, there will be a CONF section with a name corresponding
  to the following template: "vgpu_type_%(vgpu_type_name)s

  The vGPU type to associate with the PCI devices has to be the section name
  prefixed by ``vgpu_``. For example, for 'nvidia-11', you would declare
  ``[vgpu_nvidia-11]/device_addresses``.

  Each vGPU type also has to be declared in ``[devices]/enabled_vgpu_types``.

  Related options:

  * ``[devices]/enabled_vgpu_types``
  """),

For example, it would be set in nova.conf:

.. code::

  [devices]
  enabled_vgpu_types = nvidia-35,nvidia-36
  [vgpu_nvidia-35]
  device_addresses = 0000:84:00.0,0000:85:00.0
  [vgpu_nvidia-36]
  device_addresses = 0000:86:00.0


In that case, the ``nvidia-35`` vGPU type would be supported by the physical
GPUs that are in the PCI addresses ``0000:84:00.0`` and ``0000:85:00.0``, while
``nvidia-36`` vGPU would only be supported by ``0000:86:00.0``.

If some operator messes up and provides two types for the same pGPU, an
InvalidLibvirtGPUConfig exception will be raised. If the operator forgets to
provide a type for a specific pGPU, then the first type given in
``enabled_vgpu_types`` will be supported, like the existing situation.
If the operator fat-fingers the PCI IDs, then when creating the inventory, it
will return an exception.


As one single compute could now support multiple vGPU types, asking operators
to provide host aggregates for grouping computes having the same vGPU type
becomes irrelevant. Instead, we need to ask operators to amend their flavors
for specific GPU capabilities if they care of such things, or Placement will
just randomly pick one of the available vGPU types.
For this, we propose to standardize GPU capabilities that are unfortunately
very vendor specific (eg. a CUDA library version support) by having a
nova.virt.vgpu_capabilities module that would translate a vendor-specific vGPU
type into a set of os-traits traits.
If operators want vendor-specific traits, it's their responsibility to provide
custom traits on the resource providers or ask the community to find a standard
trait that would fit their needs.


Alternatives
------------

Instead of creating only one inventory per pGPU, we could try to have children
resource providers for a pGPU being GPU types. But then, once an instance
would create a vGPU, all the other inventories but the one related to the used
type would be having a total=0.


Data model impact
-----------------

None

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Operators need to either look at the sysfs (for libvirt) for knowing the
existing pGPUs and which types are supported.


Developer impact
----------------

None.

Upgrade impact
--------------

None, as not setting that config option will keep the existing behaviour where
we only support the first enabled type across all pGPUs.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  bauzas

Other contributors:
  None

Work Items
----------

* Create the config option
* Modify the libvirt virt driver code to make use of that option for creating
  the nested Resource Provider inventories.

Dependencies
============

None.

Testing
=======

Classic unittests and functional tests.


Documentation Impact
====================

A release note will be added with a 'feature' section, and the
`Virtual GPU`_ documentation will be modified to explain the new feature.

.. _`Virtual GPU`: https://docs.openstack.org/nova/latest/admin/virtual-gpu.html

References
==========

None.
