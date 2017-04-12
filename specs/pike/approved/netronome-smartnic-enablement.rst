..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Netronome SmartNIC Enablement
=============================

https://blueprints.launchpad.net/nova/+spec/netronome-smartnic-enablement

Netronome SmartNICs allow complex packet processing on the NIC. In order to
support hardware acceleration for them, Nova core needs modifications to
support the combination of VIF and OVS plugging they support. This spec
proposes a hybrid SR-IOV and OVS model to enable acceleration.

Problem description
===================

Netronome SmartNICs are able to route packets directly to individual SR-IOV
Virtual Functions. These can be connected to VMs using IOMMU (vfio-pci
passthrough) or a low-latency vhost-user virtio-forwarder running on the
compute node. The packet processing pipeline is managed by running a custom
version of OVS, which has support for enabling hardware acceleration of the
datapath match/action rules.

Currently, Nova supports multiple types of OVS plugging: TAP-like plugs,
hybrid (veth pair + linux-bridge) plugs or vhost-user socket plugs. The type
is decided by the bridge type: DPDK-based bridges use vhost-user, and "normal"
bridges use vhost-net/TAP or hybrid, based on the firewall plugin used.

In order to enable acceleration on Netronome SmartNICs, Nova needs two
additional methods to plug a VM into an OVS bridge, while consuming a PCIe
Virtual Function resource. Additionally, it would be beneficial if the
plugging method could be determined on a per-port basis.

Use Cases
---------

* An end user should be able to attach a port to a VM running on
  a hypervisor equipped with a Netronome SmartNIC with OVS in one of three
  modes:

  * Normal: Standard kernel-based OVS plugging. (hybrid or TAP)
  * Passthrough: Accelerated IOMMU passthrough, ideal for NFV-like
    applications. (vfio-pci)
  * Virtio Forwarder: Accelerated vhost-user passthrough, maximum
    software compatibility with standard virtio drivers and with support for
    live migration. (XVIO)

Proposed change
===============

* Add extra SR-IOV VNIC type:

  * Nova's network model has the following VNIC types as options for a port:

    * normal
    * direct
    * macvtap
    * direct-physical
    * baremetal

  * It is proposed that this list be extended with:

    * virtio-forwarder

* Add logic to implement PCI reservation in the neutron API section:

  * In `nova/network/neutronv2/api.py` a secondary check needs to be added to
    `create_pci_requests_for_sriov_ports` in order to allocate PCI requests
    for OVS networks when the VNIC type is set to `direct` or
    `virtio-forwarder`. It is undesirable to send the VF type selection
    parameters to Nova as PCI vendor/product ID, further work should be done
    to develop a capability or driver list that would abstract this detail
    away from users. Refer to IRC chat log for more details:
    http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2017-04-14.log.html#t2017-04-14T14:44:06

* Because Agilio OVS is a forked version of upstream OVS, an external OS-VIF
  plugin is required, based on the OVS OS-VIF plugin.

  * New port profiles should be added for the two plugging types:

    * VIFPortProfilePassthrough: for Passthrough plugging
    * VIFPortProfileForwarder: for Virtio Forwarder plugging

  * Add logic in `nova/network/os_vif_util.py:_nova_to_osvif_vif_ovs` to pick
    between them based on VNIC type.

* Additional notes:

  * From the point of view of most portions of Neutron, this solution looks
    like unmodified OVS:

    * Flow rules are programmed like normal.
    * Ports are annotated on the bridge with the same metadata as the standard
      OVS solutions.
    * Standard Neutron plugins or ML2 drivers can be used.

  * The OS-VIF plugin needs to run commands on the hypervisor to configure the
    Virtual Function and handles. This is likely to be vendor specific, this
    could call out to a user-replaceable script or be implemented in the
    OS-VIF custom plugin.

  * A deployer/administrator still has to register the PCI devices on the
    hypervisor with `pci_passthrough_whitelist` and `pci_alias` in
    `nova.conf`.

  * SmartNIC enabled nodes and classic nodes can run side-by-side. Standard
    scheduling filters allocate and place VMs according to port types and
    driver capabilities.

  * A proof-of-concept implementation has been submitted: this is tracked on
    the blueprint. For convenience, the constants and new additions have been
    named with the keyword "Agilio". This will be replaced with vendor-neutral
    SmartNIC terms.

  * An RFE needs to be logged on Neutron API to be amended to recognise
    `virtio-forwarder` as a valid option for `binding:vnic_type`.

Alternatives
------------

* Add a new OVS bridge type:

  * This would force all VMs plugged into that bridge to use one
    acceleration type. The impact on code would be much wider.

* Add glance or flavor annotations:

  * This would force a VM to have one type of acceleration. Code
    would possibly move out to more VIF types and Virtual Function reservation
    would still need to be updated.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The OS-VIF plugin needs elevated privileges, similar to other OS-VIF
plugins.

Notifications impact
--------------------

None

Other end user impact
---------------------

python-neutronclient should accept the `virtio-forwarder` VNIC type, in
addition to the current list of VNIC types.

Performance Impact
------------------

This code is likely to be called at VIF plugging and unplugging. Performance
is not expected to regress.

On accelerated ports, dataplane performance between VMs is expected to
increase.

Other deployer impact
---------------------

A deployer would still need to configure the SmartNIC version of OVS and
configure the PCI whitelist in Nova at deployment. This would not require
core OpenStack changes.

Developer impact
----------------

Core Nova semantics have been slightly changed. `ovs` networks would now
support more VNIC types.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jan Gutter <jan.gutter@netronome.com>

Other contributors:
  Imran Khakoo <imran.khakoo@netronome.com>
  Monique van den Berg <mvandenberg@netronome.com>


Work Items
----------

* Rework proof-of-concept implementation to be more vendor neutral, including
  support for the OVS-TC topic: https://review.openstack.org/#/q/topic:ovs_acc
* Generate external OS-VIF plugin, replicating required functionality from the
  OVS plugin.
* Develop acceptable method of VF selection based on capabilities or driver
  types.
* Update unit tests.
* Generate user-facing documentation.

Dependencies
============

* Netronome SmartNIC drivers are available.

Testing
=======

Unit testing will be added for the new semantics, functional testing will be
conducted at Netronome using a third-party CI system.

Documentation Impact
====================

A user-facing guide to configuring SmartNIC acceleration similar to the one
available for SR-IOV Passthrough would be generated:

https://docs.openstack.org/ocata/networking-guide/config-sriov.html

References
==========

Agilio OVS:
https://www.netronome.com/products/agilio-software/agilio-ovs-software/

Agilio OVS Firewall:
https://www.netronome.com/products/agilio-software/agilio-ovs-firewall-software/

XVIO:
https://www.netronome.com/solutions/xvio/overview/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
