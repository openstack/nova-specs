..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode


====================================================================
Add MacVTap as new virtual interface type for libvirt virtualization
====================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-macvtap-vif

Add macvtap as new virtual interface (vif) type to Nova's libvirt driver.
This is required to attach libvirt managed KVM guests via macvtap to the hosts
network. It will be exploited by a new macvtap ml2 plugin and agent. The
current spec is hosted on github `[1]`_ but the final goal is to have this
under the big tent.


Macvtap guest attachments come with the following values
   * Significantly higher throughput than the reference implementation ovs
   * Significantly lower latency than the reference implementation ovs
   * Significantly lower CPU consumption per throuput in the hypervisor than
     the reference implementation ovs
   * Built into each kernel - no additional packages required
   * Very less configuration required

However, the disadvantage of an macvtap attachment is, that Security Groups
and Rules can technically not be supported for now. More details see section
'Security impact'.

Problem description
===================

The new macvtap neutron driver and agent `[1]`_ requires nova vif driver
integration. The corresponding vif_type should represent a general macvtap
device. It is responsible for
* creating the xml definition accordingly
* the correct plug/unplug operations


Use Cases
----------

* Attaching libvirt/KVM guests via macvtap to the hosts network

No additional impact on actors from the Nova side (configuration is done in
Neutron)


Project Priority
-----------------

None

Proposed change
===============

Adding support for a general macvtap vif_type that is represented by the
following domain.xml: ::

  <interface type='direct'>
    <source dev='<macvtap_src>' mode=’<mode>’/>
    <model type='virtio' />
  </interface>

The following attributes are variables that must be propagated by neutron to
nova using the vif dictionary:

* macvtap_src: This is the source device for the macvtap (the device the
  macvtap sits on).

* mode: The mode, in which the macvtap device should be instantiated.
  e.g. 'bridge' or 'vepa'


Bandwith configurations are supported like with other vif types using a macvtap
based connection (e.g. 'hw_veb').

This proposed change will consider the ongoing os-vif-library discussion
(`[5]`_ or alternative `[3]`_) and

* implement things in this new way, if it gets approved.
* implement things in the old way, if it will be moved out.

The corresponding neutron code will use the vnic_type 'normal'.

Alternatives
------------

**Reusing an exsiting vif_type**

Reusing an already existing type is not possible:

* It depends on `[5]`_ to allow different plug/unplug operations
* It requires a refactoring of existing vif_types xml generation method
* An existing vif_type would have to be renamed which breaks other ml2 plugins


**Creating a new generic vif_type for direct connections**

This will be part of the os-vif-library effort `[5]`_.


**Supported vnic types**

The plan is to support only the vnic_type 'normal'.

However two other vnic_types do exist: 'direct' and 'macvtap'.
These other vnic_types both trigger PCI Requests in nova, so they cannot be
reused. The new macvtap support should be hardware independet. But I see the
confusion with the existing 'macvtap' type by just looking at the name.An idea
would be to rename the type 'macvtap' to somehting like 'sriov-macvtap'. But
this requires another blueprint and probbly an nova api change.


Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Macvtap does not provide a hook to apply iptables or ebtables on the guest's
traffic, and therefore does not support Neutron Security Groups and
anti-spoofing-rules. Technically, the linux macvtap driver could implement
such a hook in the future. But even without such a hook, macvtap prevents
MAC spoofing already today.

As a consequence, configuration of the NoopFirewallDriver is desired, like it
is with other integrated direct attachment types.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None from a Openstack code point of view.

But the network performance of the guest should increase compared to the ovs
reference implementation.

Other deployer impact
---------------------

None for Nova

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  scheuran (andreas.scheuring@de.ibm.com)

Other contributors:
  None

Work Items
----------


Dependencies
============

New vif-plug approach:

* `[5]`_ or alternatively
* `[3]`_



Testing
=======

* Unittest

* No tempest tests. They will be added with the corresponding neutron code and
  run by a neutron Thirdparty CI.


Documentation Impact
====================

None for Nova


References
==========

* Spec of Macvtap driver/agent:
  https://github.com/scheuran/networking-macvtap/blob/bp/initial-macvtap
  -support/specs/liberty/macvtap-ml2.rst

.. _[1]: https://github.com/scheuran/networking-macvtap/blob/bp/initial-macvtap
   -support/specs/liberty/macvtap-ml2.rst

* Core-Vendor decomposition:
  https://github.com/openstack/neutron-specs/blob/master/specs/kilo/
  core-vendor-decomposition.rst

.. _[2]: https://github.com/openstack/neutron-specs/blob/master/specs/kilo/
   core-vendor-decomposition.rst

* VIF-plug-script proposal:
  https://review.openstack.org/#/c/162468/

.. _[3]: https://review.openstack.org/#/c/162468/

* Request for networking-macvtap stackforge project:
  https://review.openstack.org/#/c/189644/

.. _[4]: https://review.openstack.org/#/c/189644/

* os-vif-library:
  https://review.openstack.org/#/c/193668/

.. _[5]: https://review.openstack.org/#/c/193668/

* Launcpad project of macvtap-agent:
  https://launchpad.net/networking-macvtap


History
=======


.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
