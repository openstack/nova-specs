..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
vRouter Hardware Offload Enablement
===================================

https://blueprints.launchpad.net/nova/+spec/vrouter-hw-offloads

SmartNICs allow complex packet processing on the NIC. In order to support
hardware acceleration for them, Nova core and os-vif needs modifications to
support the combination of VIF and vRouter plugging they support. This spec
proposes a hybrid SR-IOV and vRouter model to enable acceleration.

.. note:: In this spec, `Juniper Contrail`_, `OpenContrail`_ and
          `Tungsten Fabric`_ will be used interchangeably.

Problem description
===================

SmartNICs are able to route packets directly to individual SR-IOV Virtual
Functions. These can be connected to instances using IOMMU (vfio-pci
passthrough) or a low-latency vhost-user `virtio-forwarder`_ running on the
compute node. The `vRouter packet processing pipeline`_ is managed by a
`Contrail Agent`_. If `Offload hooks in kernel vRouter`_ are present, then
datapath match/action rules can be fully offloaded to the SmartNIC instead of
executed on the hypervisor.

For a deeper discussion on datapath offloads, it is highly recommended
to read the `Generic os-vif datapath offloads spec`_.

The ``vrouter`` VIF type has not been converted to the os-vif plugin model.
This spec proposes completing the conversion to an os-vif plugin as the first
stage.

Currently, Nova supports multiple types of Contrail plugging: TAP plugs,
vhost-user socket plugs or VEB SR-IOV plugs. Neutron and the Contrail
controller decides what VIF type to pass to Nova based on the Neutron port
semantics and the configuration of the compute node. This VIF type is then
passed to Nova:

* The ``vrouter`` VIF type plugs a TAP device into the kernel vrouter.ko
  datapath.
* The ``vhostuser`` VIF type with the ``vhostuser_vrouter_plug`` mode plugs
  into the DPDK-based vRouter datapath.
* The ``hw_veb`` VIF type plugs a VM into the VEB datapath of a NIC using
  vfio-pci passthrough.

In order to enable full datapath offloads for SmartNICs, Nova needs to support
additional VNIC types when plugging a VM with the ``vrouter`` VIF type, while
consuming a PCIe Virtual Function resource.

`Open vSwitch offloads`_ recognises the following VNIC types:

* The ``normal`` (or default) VNIC type indicates that the Instance is plugged
  into the software bridge. The ``vrouter`` VIF type currently supports only
  this VNIC type.
* The ``direct`` VNIC type indicates that a VF is passed through to the
  Instance.

In addition, the Agilio OVS VIF type implements the following offload mode:

* The ``virtio-forwarder`` VNIC type indicates that a VF is attached via a
  `virtio-forwarder`_.

Use Cases
---------

* Currently, an end user is able to attach a port to an Instance, running on a
  hypervisor with support for plugging vRouter VIFs, by using one of the
  following methods:

  * Normal: Standard kernel based plugging, or vhost-user based plugging
    depending on the datapath running on the hypervisor.
  * Direct: PCI passthrough plugging into the VEB of an SR-IOV NIC.

* In addition, an end user should be able to attach a port to an Instance
  running on a properly configured hypervisor, equipped with a SmartNIC, using
  one of the following methods:

  * Passthrough: Accelerated IOMMU passthrough to an offloaded vRouter
    datapath, ideal for NFV-like applications.
  * Virtio Forwarder: Accelerated vhost-user passthrough, maximum
    software compatibility with standard virtio drivers and with support for
    live migration.

* This enables Juniper, Tungsten Fabric (and partners like Netronome) to
  achieve functional parity with the existing OVS VF Representor datapath
  offloads for vRouter.

Proposed change
===============

* Stage 1: vRouter migration to os-vif.

  * The `vRouter os-vif plugin`_ has been updated with the required code on the
    master branch. Changes in Nova for this stage are gated on a release being
    issued on that project in order to reflect the specific version required
    in the release notes.

    Progress on this task is tracked on the `vRouter os-vif conversion
    blueprint`_.

  * In ``nova/virt/libvirt/vif.py``:

    Remove the Legacy vRouter config generation code,
    ``LibvirtGenericVIFDriver.get_config_vrouter()``, and migrate the plugging
    code, ``LibvirtGenericVIFDriver.{plug,unplug}_vrouter()``, to an external
    os-vif plugin.

    For kernel-based plugging, VIFGeneric will be used.

  * In ``privsep/libvirt.py``

    Remove privsep code, ``{plug,unplug}_contrail_vif()``:

    The call to ``vrouter-port-control`` will be migrated to the external
    os-vif plugin, and further changes will be beyond the scope of Nova.

* Stage 2: Extend os-vif with better abstraction for representors.

    os-vif's object model needs to be updated with a better abstraction model
    to allow representors to be applicable to the ``vrouter`` datapath.

    This stage will be covered by implementing the `Generic os-vif datapath
    offloads spec`_.

* Stage 3: Extend the ``vrouter`` VIF type in Nova.

  Modify ``_nova_to_osvif_vif_vrouter`` to support two additional VNIC types:

  * ``VNIC_TYPE_DIRECT``: os-vif ``VIFHostDevice`` will be used.

  * ``VNIC_TYPE_VIRTIO_FORWARDER``: os-vif ``VIFVHostUser`` will be used.

  Code impact to Nova will be to pass through the representor information to
  the os-vif plugin using the extensions developed in Stage 2.

Summary of plugging methods
---------------------------

* Existing methods supported by Contrail:

  * VIF type: ``hw_veb`` (legacy)

    * VNIC type: ``direct``

  * VIF type: ``vhostuser`` (os-vif plugin: ``contrail_vrouter``)

    * VNIC type: ``normal``
    * ``details: vhostuser_vrouter_plug: True``
    * os-vif object ``VIFVHostUser``

  * VIF type: ``vrouter`` (legacy)

    * VNIC type: ``normal``

* After migration to os-vif (Stage 1):

  * VIF type: ``hw_veb`` (legacy)

    * VNIC type: ``direct``

  * VIF type: ``vhostuser`` (os-vif plugin: ``contrail_vrouter``)

    * VNIC type: ``normal``
    * ``details: vhostuser_vrouter_plug: True``
    * os-vif object: ``VIFVHostUser``

  * VIF type: ``vrouter`` (os-vif plugin: ``vrouter``)

    * VNIC type: ``normal``
    * os-vif object: ``VIFGeneric``

* Additional accelerated plugging modes (Stage 3):

  * VIF type: ``vrouter`` (os-vif plugin: ``vrouter``)

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile.datapath_offload: DatapathOffloadRepresentor``

  * VIF type: ``vrouter`` (os-vif plugin: ``vrouter``)

    * VNIC type: ``virtio-forwarder``
    * os-vif object: ``VIFVHostUser``
    * ``port_profile.datapath_offload: DatapathOffloadRepresentor``

Additional notes
----------------

* Stage 1 and Stage 2 can be completed and verified in parallel. The
  abstraction layer will be tested on the Open vSwitch offloads.

* Selecting between the VEB passthrough mode and the offloaded vRouter
  datapath passthrough mode happens at the `Contrail Controller`_. This is
  keyed on the provider network associated with the Neutron port.

* The `vRouter os-vif plugin`_ has been updated to adopt ``vrouter`` as the new
  os-vif plugin name. ``contrail_vrouter``, is kept as a backwards compatible
  alias. This prevents namespace fragmentation. `Tungsten Fabric`_,
  `OpenContrail`_ and `Juniper Contrail`_ can use a single os-vif plugin
  for the vRouter datapath.

* No corresponding changes in Neutron are expected. The Contrail Neutron
  plugin and agent require minimal changes in order to allow the semantics
  to propagate correctly.

* This change is agnostic to the SmartNIC datapath: should Contrail switch
  to TC based offloads, eBPF or a third-party method, the Nova plugging
  logic will remain the same for full offloads.

* A deployer/administrator still has to register the PCI devices on the
  hypervisor with ``pci_passthrough_whitelist`` in ``nova.conf``.

* SmartNIC-enabled nodes and standard compute nodes can run side-by-side.
  Standard scheduling filters allocate and place Instances according to port
  types and driver capabilities.

Alternatives
------------

Alternatives proposed require much more invasive patches to Nova:

* Create a new VIF type:

  * This would add three VIF types for Contrail to maintain. This is not
    ideal.

* Add glance or flavor annotations:

  * This would force an Instance to have one type of acceleration. Code would
    possibly move out to more VIF types and Virtual Function reservation would
    still need to be updated.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

os-vif plugins run with elevated privileges.

Notifications impact
--------------------

None

Other end user impact
---------------------

End users will be able to plug VIFs into Instances with either ``normal``,
``direct`` or ``virtio-forwarder`` VNIC types on hardware enabled Nova nodes
running Contrail.

Performance Impact
------------------

This code is likely to be called at VIF plugging and unplugging. Performance
is not expected to regress.

On accelerated ports, dataplane performance between Instances is expected to
increase.

Other deployer impact
---------------------

A deployer would still need to configure the SmartNIC components of Contrail
and configure the PCI whitelist in Nova at deployment. This would not require
core OpenStack changes.

Developer impact
----------------

Core Nova semantics will be slightly changed. ``vrouter`` VIFs will support
more VNIC types.

Upgrade impact
--------------

New VNIC type semantics will be available on compute nodes with this patch.

A deployer would be mandated to install the os-vif plugin to retain existing
functionality in Nova. This is expected to be handled by minimum required
versions in Contrail.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jan Gutter <jan.gutter@netronome.com>

Work Items
----------

* contrail-controller review implementing the semantics has been merged and is
  awaiting a release tag:
  https://review.opencontrail.org/42850

* The OpenContrail os-vif reference plugin has been updated and is awaiting a
  release tag:
  https://review.opencontrail.org/43399

* Stage 1: os-vif porting for vRouter VIF has been submitted:
  https://review.openstack.org/571325

* Stage 2: `Generic os-vif datapath offloads spec`_ needs to be implemented.

* Stage 3: The OpenContrail os-vif reference plugin needs to be amended with
  the interfaces added to os-vif in Stage 2.

* Stage 3: The ``vrouter`` VNIC support needs to be added in Nova:
  https://review.openstack.org/572082

Dependencies
============

The following dependencies on Tungsten Fabric have been merged on the master
branch and are awaiting a release tag:

* The Contrail/Tungsten Fabric controller required minor updates to enable the
  proposed semantics. This was merged in:
  https://review.opencontrail.org/42850

* The os-vif reference plugin has been updated in:
  https://review.opencontrail.org/43399

The following items can occur in parallel:

* os-vif extensions for accelerated datapath plugin modes need to be released.
  Consult the `Generic os-vif datapath offloads spec`_ for more details. The
  os-vif library update is planned for the Stein release.

* Pending release tags on the Contrail os-vif plugin, the `vRouter os-vif
  conversion blueprint`_ can be completed. This is currently planned for the
  Tungsten Fabric 5.1 release.

Once both of the preceding tasks have been implemented, the following items
can occur in parallel:

* Nova can implement the VNIC support for the ``contrail`` os-vif plugin.

* The ``contrail`` os-vif plugin can be updated to use the new os-vif
  interfaces.

Testing
=======

* Unit tests have been refreshed and now cover the VIF operations more
  completely.

* Third-party CI testing will be necessary to validate the Contrail and
  Tungsten Fabric compatibility.


Documentation Impact
====================

Since this spec affects a non-reference Neutron plugin, a release note in Nova
should suffice. Specific versions of Contrail / Tungsten Fabric need to be
mentioned when a new plugin is required to provide existing functionality. The
external documentation to configure and use the new plugging modes should be
driven from the Contrail / Tungsten Fabric side.

References
==========

* `Juniper Contrail`_
* `OpenContrail`_
* `Tungsten Fabric`_
* `virtio-forwarder`_
* `vRouter packet processing pipeline`_
* `Offload hooks in kernel vRouter`_
* `Open vSwitch offloads`_
* `Generic os-vif datapath offloads spec`_
* `Contrail Agent`_
* `Contrail Controller`_
* `vRouter os-vif plugin`_
* `vRouter os-vif conversion blueprint`_
* `Contrail Controller to Neutron translation unit`_
* `Nova review implementing offloads for legacy plugging <https://review.openstack.org/567147>`_
  (this review serves as an example and has been obsoleted)

.. _`Juniper Contrail`: https://www.juniper.net/us/en/products-services/sdn/contrail/
.. _`OpenContrail`: http://www.opencontrail.org/
.. _`Tungsten Fabric`: https://tungsten.io/
.. _`virtio-forwarder`: http://virtio-forwarder.readthedocs.io/en/latest/
.. _`vRouter packet processing pipeline`: https://github.com/Juniper/contrail-vrouter
.. _`Offload hooks in kernel vRouter`: https://github.com/Juniper/contrail-vrouter/blob/R4.1/include/vr_offloads.h
.. _`Open vSwitch offloads`: https://docs.openstack.org/neutron/queens/admin/config-ovs-offload.html
.. _`Contrail Agent`: https://github.com/Juniper/contrail-controller/tree/R4.1/src/vnsw/agent
.. _`Contrail Controller`: https://github.com/Juniper/contrail-controller
.. _`vRouter os-vif plugin`: https://github.com/Juniper/contrail-nova-vif-driver/blob/master/vif_plug_vrouter/
.. _`Generic os-vif datapath offloads spec`: https://specs.openstack.org/openstack/nova-specs/specs/stein/approved/generic-os-vif-offloads.html
.. _`vRouter os-vif conversion blueprint`: https://blueprints.launchpad.net/nova/+spec/vrouter-os-vif-conversion
.. _`Contrail Controller to Neutron translation unit`: https://github.com/Juniper/contrail-controller/blob/R4.1/src/config/api-server/vnc_cfg_types.py
