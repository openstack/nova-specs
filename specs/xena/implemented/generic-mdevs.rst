..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Support for generic mediated devices
====================================

https://blueprints.launchpad.net/nova/+spec/generic-mdevs


As Nova already supports to manage existing mediated devices via the libvirt
driver for virtual GPUs, we would want to help the operator to use this for
generic PCI devices that use the VFIO-mdev framework but aren't GPUs.

Problem description
===================

As the Linux kernel supports a framework that's called `VFIO-mdev`_ , hardware
vendors can use it for their devices, like `nVidia does for their GPUs`_. For
example, you can create virtual GPUs by asking the kernel to create a new
mediated device to the parent. As this API is abstract, any hardware could use
this framework for supporting the fact to create a virtual device off the
physical device.

In the Queens release, the libvirt driver gains support for looking up
existing mediated devices for enable `managing virtual GPUs`_ and can also
directly call the kernel API to `creating a new mediated device if needed`_.
Unfortunately, while this kernel API is abstract in terms of usability between
different physical devices supporting mediated devices, we created in Nova a
fake and unnecessary reciprocity between a virtual GPU and a mediated
device : a virtual GPU is indeed a mediated device, but a mediated device can
be something other than a virtual GPU.

In this spec, we propose to remove this unrelated reciprocity by considering a
mediated device to be a distinct Placement resource class and not a virtual
GPU, if specified.


.. note:: As currently, we only support stateless physical devices, as Nova
          just reuses existing mediated devices between instances.

Use Cases
---------

As an operator, I want to provide new flavors for my customers that would
ask for generic mediated devices that aren't virtual GPUs, as I already have
hardware that use VFIO-mdev fremework in the Linux kernel for abstracting
virtual resources.

Proposed change
===============

We will minimize to the very least number of changes, that won't be breaking
existing users of the virtual GPUs in Nova :

* we'll just extend the configuration options for managing mediated devices in
  Nova by proposing an extra option that will tell whether it's for GPUs or
  else.
* we'll propose to use custom resource classes for scheduling decisions.

Existing flavors won't need to change.


The configuration changes
-------------------------

Today, you can allow the Nova libvirt driver to use mediated devices for
virtual GPU management by defining in `nova.conf` :

.. code::

  [devices]
  enabled_vgpu_types = <type1>,<type2>
  [vgpu_<type1>]
  device_addresses = <pci_address_1>,<pci_address_2>
  [vgpu_<type2>]
  device_addresses = <pci_address_3>


We propose to rename the `enabled_vgpu_types` option name with
`enabled_mdev_types` and just use the old name as a legacy alias.
Accordingly, groups could be named `mdev_<type>` or being kept as `vgpu_<type>`
for a couple of releases.
An extra option could be specified under a `mdev_<type>` group, named
`mdev_class` and which could be defined as below :

.. code::

  cfg.StrOpt('mdev_class',
             default='vgpu',
             regex=[a-zA-Z0-9_],
             max_limit=248,
             help='Class of mediated device to manage.')

An example would be as follows :

.. code::

  [devices]
  enabled_mdev_types = nvidia-35,mlx5_core-local
  [mdev_nvidia-35]
  device_addresses = 0000:84:00.0,0000:85:00.0
  [mdev_mlx5_core-local]
  device_addresses = 0000:86:00.0
  mdev_class=mlx5



.. note:: We already have `configuration checks`_ for this but we could try to
          look at the inventories to detect unwanted changes if allocations
          were create and prevent the compute service to start.


The custom resource classes
---------------------------

Nothing really fancy here. The Nova libvirt driver will lookup at existing
PCI devices that support mediated devices and create inventories as of now.
The only difference is that if a PCI device is set as something other than the
default `vgpu` class, then the inventory of the number of virtual devices it
can create for the specific type will use a custom resource class named
`CUSTOM_<type>`.
For example, in the example above, inventories of physical devices using the
`mlx5` mdev class will have resources of a class named `CUSTOM_MLX5` (we
will convert the characters to uppercase in order to be accepted by the
Placement API).


Accordingly, if a flavor specifies an extraspec with resource groups like
`resources:CUSTOM_MLX5=1`, then Placement will create allocations on a Resource
Provider with this resource class. When, later in the boot sequence, the
libvirt driver will get allocations for the instance in the `spawn()` method
(or for other move operations), it will not only lookup at the `VGPU` related
allocations but also the `CUSTOM_MLX5` ones and will consequently either bind
an existing mdev or ask sysfs to create a new one. In order to do it, the
driver will first look at all the custom resource classes that are accepted
by the configuration options above.


Alternatives
------------

We could describe the capacity with the new inventory YAML files but this would
disrupt a bit more existing users of the framework.
Another alternative could be to stop using the VGPU resource class and just
use the new MDEV resource class but this is a more breaking change for users
which would potentially require to modify existing allocations. Besides, other
virt drivers could continue to use the VGPU resource class, which would mean
a discrepancy between virt drivers.

Cyborg can also be an obvious alternative as they start implementing virtual
GPUs too. There are no problems with having both projects supporting generic
devices as we let the operator choose what they prefer in terms of maintenance
and usage while the code itself is mostly shared (as eventually the mdev
allocation from Cyborg reuses the same methods).

Data model impact
-----------------

None.

REST API impact
---------------

None.
Currently, all operations but live migration are supported and we don't see the
need to propose a microversion for users opting into generic devices. As
flavors are managed by operators, there wouldn't be visible changes for the
end users.

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

See the configuration options described above.

Developer impact
----------------

Potentially other virt drivers could use the opportunity to propose generic
devices too, mainly the Xen driver which already supports virtual gpus.

Upgrade impact
--------------

None as existing flavors and inventories won't change. We will specify to only
use the new generic class for new hardware in order to prevent unneeded and
unnecessary Placement inventories modifications, but this isn't really changing
the situation where some operator decides to reshuffle their GPUs with
different types.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Other contributors:
  None

Feature Liaison
---------------

None.

Work Items
----------

* Amend the libvirt driver to populate inventories of custom resource classes.
* Amend the libvirt methods to look at allocations of known custom resource
  classes.
* Expose the configuration changes.

Dependencies
============

None.

Testing
=======

Good news are, we could use the `mtty fake driver`_ for testing generic mdevs
(and by extend virtual GPU management in Nova) with Tempest without relying on
some proprietary and expensive driver which is impossible with our upstream
gate jobs.


Documentation Impact
====================

Mostly https://docs.openstack.org/nova/latest/admin/virtual-gpu.html.


References
==========

.. _`VFIO-mdev` : https://www.kernel.org/doc/html/latest/driver-api/vfio-mediated-device.html
.. _`nVidia does for their GPUs` : https://docs.nvidia.com/grid/latest/grid-vgpu-user-guide/index.html#creating-vgpu-device-red-hat-el-kvm
.. _`managing virtual GPUs` : https://github.com/openstack/nova/blob/771ea5bf1ea667d6ffe456ee6ef081b83a77f53c/nova/virt/libvirt/driver.py#L7463
.. _`creating a new mediated device if needed` : https://github.com/openstack/nova/blob/771ea5bf1ea667d6ffe456ee6ef081b83a77f53c/nova/virt/libvirt/driver.py#L7818
.. _`configuration checks` : https://github.com/openstack/nova/blob/7953c0197d1a4466cb5b78070d47626c92f9db6e/nova/virt/libvirt/driver.py#L7357
.. _`mtty fake driver`: https://www.kernel.org/doc/html/latest/driver-api/vfio-mediated-device.html#using-the-sample-code


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
