..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Support Napatech LinkVirtualization SmartNICs
=============================================

https://blueprints.launchpad.net/nova/+spec/support-napatech-linkvirtualization-smartnic

Napatech LinkVirtualization SmartNICs offload network traffic switching, QoS,
and tunnel encapsulation/decapsulation functions from the OVS running on the
hypervisor to the on-board silicon. This spec proposes to update the Nova and
Neutron source code to include support for a new VIF type corresponding to the
virtual devices exposed by the LinkVirtualization SmartNIC.

Problem description
===================

Napatech SmartNICs can offload several computational resource intensive tasks
from the hypervisor, such as packet switching, QoS enforcement, and V(x)LAN
tunnel encapsulation/decapsulation. Upstream and Out of tree OVS
implementations can leverage these offloads when using dpdk via DPDK port
representors (https://docs.openvswitch.org/en/latest/topics/dpdk/phy/#representors).

Data processing, like encryption and compression, can be extremely intensive
when performed in software and require a tremendous amount of CPU cores.
By offloading these functions to accelerated NIC hardware it is possible
to significantly increase performance and free CPU cores to support more
virtual functions on the same server.

To achive those goals Napatech provides
`SmartNIC Solution Virtual Switch Acceleration`__.

.. __: https://shorturl.at/qAIL9

`Napatech Getting Started Guide`__ will provide details regarding
`Napatech SmartNIC solution for hardware offload`__:
* OS Preparation
* Compiling and Installing DPDK with the Napatech PMD
* Running OVS-DPDK
* OVS-DPDK Configuration Examples

.. __: https://shorturl.at/cizAL
.. __: https://shorturl.at/iS137

Nova and os-vif currently support kernel-based VF representors, but not the
DPDK VF representors which leverage vhost-user socket. This spec seeks to
address this gap.

Use Cases
---------

* An end user of Napatech SmartNIC should be able to support Napatech SmartNICs
  out-of-the-box.
* Other SmartNICs using OvS-DPDK representor ports should also work.


Proposed change
===============

* We propose to extend the OpenvSwitch driver with a new VNIC type
  `VNIC_VIRTIO_FORWARDER` and the related VIF handling function
  `nova_to_osvif_vif()`. A method which handles vhostuser VIF type should
  handle the new VNIC type by setting an appropriate datapath, representor port
  profile, vhostuser vif type, `OVS` plugin, and datapath offload settings.
  OpenvSwitch driver should be able to set the DPDK representor socket path for
  virtio-forwarder vnic type:
  https://docs.openvswitch.org/en/latest/topics/dpdk/phy/#representors.

* We propose to extend vif type `OVS` attribute `OVS_DPDK_PORT_TYPES` with a
  new port type `dpdk`.

* We propose to update the ``OvsPlugin`` class to support plug and unplug of
  OVS DPDK representor ports `os_vif OVSPlugin code`__.

.. __: https://encr.pw/uSQfn

  Appropriate methods `plug()` and `unplug()` should be extended with
  ability to plug VF if vif has `VIFPortProfileOVSRepresentor` port profile for
  ``VIFVHostUser``.

* `_plug_vf()` method should be extended with formula `VF_NUM=ID*8+VF` to
  calculate VF number based on the input PCI slot.

* `update_device_mtu()` method will be extended with `OVS_DPDK_INTERFACE_TYPE`
  interface support to have ability update MTU configuration for port on the
  OVS layer.

* We propose Unit/Functional tests pertinent to the proposed changes.

* The `NT200A02`__ and `NT50B01`__ SmartNics with Link-Virtualization™ software
  will provide support of the hardware-based solution for full
  Open vSwitch (OVS) offload.

.. __: https://www.napatech.com/products/nt200a02-smartnic-capture/
.. __: https://www.napatech.com/products/nt50b01-smartnic-capture/

* Napatech will a provide document with NT NIC hardware offloading
  configuration in the OpenStack. This documentation will consist
  configuration steps, requirements, links on the Napatech portal
  with software and additional specific documentations. This document
  will be created under Neutron project.

Alternatives
------------

None

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

None

Performance Impact
------------------

Users will see a significant network performance increase when running over
the hardware offloaded data-plane compared kernel-ovs and traditional
vhost-user.

Other deployer impact
---------------------

In line with other SmartNIC offerings, the deployer will have to configure
OVS-DPDK following the SmartNIC producer guidelines and update the PCI
device_spec configuration.
https://docs.openstack.org/nova/latest/configuration/config.html#pci.device_spec

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

* Oleksii Butenko (obu-plv)
* Danylo Vodopianov (dvo-plv)
* Justas Poderys (justas_napa on IRC and Gerrit)


Feature Liaison
---------------

* Sean Mooney (sean-k-mooney)

Work Items
----------

* Extend Openvswitch driver with Virtio-Forwarder VIF type support
* Add Virtio-Forwarder VIF type for Qos support
* Add new OVS datapath port type ``dpdk``
* Add ability to set MTU for dpdk representor potr type
* Add ability to plug vf with ``VIFPortProfileOVSRepresentor`` vif profile
  for ``VIFVHostUser``
* Add/Update Unit and Functional tests

Dependencies
============

* This blueprint is a prerequisite to update code in Neutron to support
  LinkVirtualization SmartNICs. This is in-line with support of other
  SmartNICs. Links to changes of all four components are given in the Work
  Items section.


Testing
=======

Code changes will require additional testing coverage:
*  New unit tests will be implented or updated existing.
*  New functional tests will be implemented.
*  Napatech will provide third party ci for testing on the NT hardware.


Documentation Impact
====================

We are not introducing any new VNIC type, so there should be no impact on
documentation.


References
==========

* Napatech LinkVirtualization:
  https://www.napatech.com/products/link-virtualization-software/

* Napatech SmartNIC solution for hardware offload
  https://shorturl.at/iS137

* Napatech Getting Started Guide
  https://shorturl.at/cizAL


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.2 Bobcat
     - Introduced
