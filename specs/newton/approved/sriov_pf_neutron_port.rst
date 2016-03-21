..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================
Enable SR-IOV physical functions assignment with Neutron port
=============================================================

https://blueprints.launchpad.net/nova/+spec/sriov-pf-passthrough-neutron-port

Relying on the sriov-physical-function-passthrough spec [1], which describes
an implementation of a SR-IOV physical functions passthough support in Nova;
This spec will address the need for SR-IOV physical functions to be
associated with Neutron ports.


Problem description
===================

Current implementation of the Physical Function (PF) passthrough lacks
any network awareness. It is exposing the physical hardware to the instances
without an integration with Neutron, unlike the way it is implemented for the
SR-IOV Virtual Functions (VFs).

Physical Function can only be exposed as a libvirt's <hostdev>
definition in the domain XML and not as a "<interface type='hostdev'..."
element that can receive a MAC address and a virtual port definition.

In general, it is not possible to configure a MAC address for a PF, nor to
assign a VLAN tag via it's driver on the host. Therefore, additional steps
will be needed to update Neutron with an actual MAC address of a seleced PF.


Use Cases
----------

Workloads requiring to have full access to a physical function will
also need to have the ability to manipulate the network settings, in the
same manner and flexibility that is currently available for VFs.


Project Priority
-----------------

None

Proposed change
===============

Allow the users to specify a new vnic_type, with the neutron port creation,
which would be used by Nova to select a Physical Function on a host and
properly passthrough it to a guest, using a new VIF type.
Nova will update the neutron port with a MAC address of the selected PF
on the host.

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
None

Other deployer impact
---------------------
None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Vladik Romanovsky <vromanso@redhat.com>

Other contributors:
  Nikola Đipanov <ndipanov@redhat.com>

Work Items
----------

* Introduce a new vnic_type to request PF selection - VNIC_DIRECT_PHYSICAL
* Introduce a new vif type to configure the PF attachment with as a hostdev.
* Update the Neutron port with a MAC of a selected PF.


Dependencies
============

* Depending on a neutron support of a new VNIC type.
  https://review.openstack.org/#/c/246923
  https://bugs.launchpad.net/neutron/+bug/1500993
* There is also a dependency on the actual implementation of the
  sriov-physical-function-passthrough spec [1]

Testing
=======
New unit and functional tests will be written to cover the changes.

Documentation Impact
====================

Documentation of a new vnic_type should be documented.

References
==========
[1] https://review.openstack.org/#/c/212472

History
=======

Optional section for Mitaka intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Newton
     - Re-proposed
