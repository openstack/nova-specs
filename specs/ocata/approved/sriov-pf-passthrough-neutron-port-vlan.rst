..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
Expose SR-IOV physical function's VLAN tag to guests
====================================================

https://blueprints.launchpad.net/nova/+spec/sriov-pf-passthrough-neutron-port-vlan

The sriov-pf-passthrough-neutron-port spec [1]_, that introduced network
awareness for the passed-through Physical Functions, has been implemented in
the Newton Cycle. However, current implementation ignores VLAN tags set on the
associated neutron port.


Problem description
===================

The aim of the sriov-pf-passthrough-neutron-port spec [1]_ was to add network
awareness to the assigned Physical Functions (PFs) for the users to use the
feature in the same manner as they would use it with the Virtual Functions
(VFs) However, with the current implementation VLAN tags setting is being
ignored.

Assignment of the SR-IOV Physical Function (PF) to a guest instance will
unbind the PF device from its driver. Any MAC or VLAN tag that is set
in the PF device driver will be lost once the device is unbound.
Currently, nova updates neutron with an actual MAC address of a selected PF,
however, no solution is available for passing the VLAN tag [3]_.

Use Cases
----------

Workloads requiring full access to a physical function will also need to have
the ability to manipulate the network settings, in the same manner and
flexibility that is currently available for VFs. This includes the ability to
set VLAN tags.

Proposed change
===============

The aim of this proposal is to expose VLAN tags, of the associated physical
functions, to the guest instance through the device tagging mechanism.
Several VLAN tags can be associated with a network device.
Neutron provides the VLAN tag as part of the port binding details::

    binding:vif_details: {'vlan': 1000}

The format of the network devices metadata has been introduced in a
virt-device-role-tagging spec [2]_. As part of this proposal this format will
be extended with a VLANs list field.

For example:

.. code-block:: json

  {
    "devices": [
      {
          "type": "nic",
          "bus": "pci",
          "address": "0000:00:02.0",
          "mac": "01:22:22:42:22:21",
          "tags": ["nfvfunc1"]
          "vlans": [300, 1000]
      }]
  }

This metadata is being provided via a config drive and a metadata service.
Guest OS will be able to consume this information about the devices and
configure the provided VLAN tags.
However, how the guest OS will do it is outside the scope of this spec.

Alternatives
------------
The alternative is not to allow an assignment of a PF to a guest if Neutron has
a VLAN set for the network and raise an error if this is attempted.
However, following this suggestion will leave lots of cases unaddressed.
This feature is mainly intended for specific NFV use cases, which require
flexibility and a high throughput, which this feature might provide.

Data model impact
-----------------
A new field "vlans" will be introduced to the VirtualInterface object and its
associated table


REST API impact
---------------
None


Security impact
---------------

The Neutron project currently doesn't provide a mechanism to restrict the
traffic a guest can be exposed to, if it's connected to a VLAN tagged network.
Allowing PFs to be connected with vlan tagged or multiple-vlan tagged trunk
ports might be considered as a security issue.

If putting the passed through PF in a VLAN is used as a way to restrict the
traffic that is available to the guest, we cannot expect the guest to honour
the VLAN information provided in the metadata. Therefore, an external mechanism
must be in place to restrict the traffic available to the PF based on its VLAN.
There is no such mechanism in either Nova or Neutron, nor can there be, as the
physical interface and the wire connecting it to the switch is outside of our
control. It is the deployer’s responsibility to ensure that traffic reaching
the PF is limited to what is intended for that VLAN.

The operator may physically make the necessary network separation to secure the
setup, configuring the top of the rack switches to map specific PCI devices to
physical networks.
Some operators have a private external mechanism that maps PCI addresses to
switch port maps, and talk openflow to the switches.

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
Secure the setup by making sure that physical network mapped to the whitelisted
PCI device only has access to traffic intended for a specific user/tenant.

Some operators currently do this with extra mechanism drivers that have PCI
addresses to switch port maps: the PCI address of the PF device is associated
with the switch port that the PF is connected to. Using these maps, the
mechanism driver can configure the correct VLAN on the switch port using
Openflow.

Such a mechanism can be used as an example for operators to understand that
merely setting VLAN tags on a PF in Nova isn't sufficient in and of itself,
they also have the responsibility the configure their top of rack switches.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

* Vladik Romanovsky <vromanso@redhat.com>
* Artom Lifshitz <alifshit@redhat.com>


Work Items
----------

* Define new 'vlans' attribute for VirtualInterface object and it's db table.
* Modify ``_update_ports_for_instance`` to include vlans in the created
  VirtualInterface objects
* Modify the InstanceMetadata object to include vlans attribute


Dependencies
============

None

Testing
=======

New unit and functional tests will be written to cover the changes.

Documentation Impact
====================

* `Networking guide`_ should describe the operator's responsibility as stated
  in `Other deployer impact`_ section and the `security guide`_ should describe
  the security aspect of this feature, as stated in the `Security impact`_
  section.
* Provide and example to the guest users of how to extract the device metadata
  information

.. _Networking guide: http://docs.openstack.org/newton/networking-guide/config-sriov.html
.. _security guide: http://docs.openstack.org/security-guide/networking/services.html#l2-isolation-using-vlans-and-tunneling

References
==========
.. [1] https://review.openstack.org/#/c/239875/
.. [2] https://specs.openstack.org/openstack/nova-specs/specs/mitaka/approved/virt-device-role-tagging.html
.. [3] https://bugs.launchpad.net/nova/+bug/1614092

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced

