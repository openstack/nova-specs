..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Generic os-vif datapath offloads
================================

https://blueprints.launchpad.net/nova/+spec/generic-os-vif-offloads

The existing method in os-vif is to pass datapath offload metadata via a
``VIFPortProfileOVSRepresentor`` port profile object. This is currently used by
the ``ovs`` reference plugin and the external ``agilio_ovs`` plugin. This spec
proposes a refactor of the interface to support more VIF types and offload
modes.

Problem description
===================

Background on Offloads
----------------------

While composing this spec, it became clear that the "offloads" term had
historical meaning that caused confusion about the scope of this spec. This
subsection was added in order to clarify the distinctions between different
classes of offloads.

Protocol Offloads
~~~~~~~~~~~~~~~~~

Network-specific computation being handled by dedicated peripherals is well
established on many platforms. For Linux, the `ethtool man page`_ details a
number of settings for the ``--offload`` option that are available on many
NICs, for specific protocols.

``ethtool`` type offloads typically:

#. are available to guests (and hosts),
#. have a strong relationship with a network endpoint,
#. have a role with generating and consuming packets,
#. can be modeled as capabilities of the virtual NIC on the instance.

Currently, Nova has little modelling for these types of offload capabilities.
Ensuring that instances can live migrate to a compute node capable of
providing the required features is not something Nova can currently determine
ahead of time.

This spec only touches lightly on this class of offloads.

Datapath Offloads
~~~~~~~~~~~~~~~~~

Relatively recently, SmartNICs emerged that allow complex packet processing on
the NIC. This allows the implementation of constructs like bridges and routers
under control of the host. In contrast with procotol offloads, these offloads
apply to the dataplane.

In Open vSwitch, the dataplane can be implemented by, for example, the kernel
datapath (the ``openvswitch.ko`` module), the userspace datapath, or the
``tc-flower`` classifier. In turn, portions of the ``tc-flower`` classifier can
be delegated to a SmartNIC as described in this `TC Flower Offload paper`_.

.. note:: Open vSwitch refers to specific implementations of its packet
          processing pipeline as datapaths, not dataplanes. This spec follows
          the datapath terminology.

Datapath offloads typically have the following characteristics:

#. The interfaces controlling and managing these offloads are under host
   control.
#. Network-level operations such as routing, tunneling, NAT and firewalling can
   be described.
#. A special plugging mode could be required, since the packets might bypass
   the host hypervisor entirely.

The simplest case of this is an SR-IOV NIC in Virtual Ethernet Bridge (VEB)
mode, as used by the ``sriovnicswitch`` Neutron driver. A special plugging mode
is necessary, (namely IOMMU PCI passthrough), and the hypervisor configures the
VEB with the required MAC ACL filters.

This spec focuses on this class of offloads.

Hybrid Offloads
~~~~~~~~~~~~~~~

In future, it might be possible to push out datapath offloads as a service to
guest instances. In particular, trusted NFV instances might gain access to
sections of the packet processing pipeline, with various levels of isolation
and composition. This spec is does not target this use case.

Core Problem Statement
----------------------

In order to support hardware acceleration for datapath offloads, Nova
core and os-vif need to model the datapath offload plugging metadata. The
existing method in os-vif is to pass this via a
``VIFPortProfileOVSRepresentor`` port profile object. This is used by the
``ovs`` reference plugin and the external ``agilio_ovs`` plugin.

With ``vrouter`` being a potential third user of such metadata (proposed in the
`blueprint for vrouter hardware offloads`_), it's worthwhile to abstract the
interface before the pattern solidifies further.

This spec is limited to refactoring the interface, with future expansion in
mind, while allowing existing plugins to remain functional.

SmartNICs are able to route packets directly to individual SR-IOV Virtual
Functions. These can be connected to instances using IOMMU (vfio-pci
passthrough) or a low-latency vhost-user `virtio-forwarder`_ running on the
compute node.

In Nova, a VIF should fully describe how an instance is plugged into the
datapath. This includes information for the hypervisor to perform the required
plugging, and also info for the datapath control software. For the ``ovs`` VIF,
the hypervisor is generally able to also perform the datapath control, but this
is not the case for every VIF type (hence the existence of os-vif).

The VNIC type is a property of a VIF. It has taken on the semantics of
describing a specific "plugging mode" for the VIF. In the Nova network API,
there is a `list of VNIC types that will trigger a PCI request`_, if Neutron
has passed a VIF to Nova with one of those VNIC types set. `Open vSwitch
offloads`_ uses the following VNIC types to distinguish between offloaded
modes:

* The ``normal`` (or default) VNIC type indicates that the Instance is plugged
  into the software bridge.
* The ``direct`` VNIC type indicates that a VF is passed through to the
  Instance.

In addition, the Agilio OVS VIF type implements the following offload mode:

* The ``virtio-forwarder`` VNIC type indicates that a VF is attached via a
  `virtio-forwarder`_.

Currently, os-vif and Nova implement `switchdev SR-IOV offloads`_ for Open
vSwitch with ``tc-flower`` offloads. In this model, a representor netdev on the
host is associated with each Virtual Function. This representor functions like
a handle for the corresponding virtual port on the NIC's packet processing
pipeline.

Nova passes the PCI address it received from the PCI request to the os-vif
plugin. Optionally, a netdev name can also be passed to allow for friendly
renaming of the representor by the os-vif plugin.

The ``ovs`` and ``agilio_ovs`` os-vif plugins then look up the associated
representor for the VF and perform the datapath plugging. From Nova's
perspective the hypervisor then either passes through a VF using the data from
the ``VIFHostDevice`` os-vif object (with the ``direct`` VNIC type), or plugs
the Instance into a vhost-user handle with data from a ``VIFVHostUser`` os-vif
object (with the ``virtio-forwarder`` VNIC type).

In both cases, the os-vif object has a port profile of
``VIFPortProfileOVSRepresentor`` that carries the offload metadata as well as
Open vSwitch metadata.

Use Cases
---------

Currently, switchdev VF offloads are modelled for one port profile only. Should
a developer, using a different datapath, wish to pass offload metadata to an
os-vif plugin, they would have to extend the object model, or pass the metadata
using a confusingly named object. This spec aims to establish a recommended
mechanism to extend the object model.

Proposed change
===============

Use composition instead of inheritance
--------------------------------------

Instead of using an inheritance based pattern to model the offload
capabilities and metadata, use a composition pattern:

* Implement a ``DatapathOffloadBase`` class.

* Subclass this to ``DatapathOffloadRepresentor`` with the following members:

    * ``representor_name: StringField()``
    * ``representor_address: StringField()``

* Add a ``datapath_offload`` member to ``VIFPortProfileBase``:

    * ``datapath_offload: ObjectField('DatapathOffloadBase', nullable=True,
      default=None)``

* Update the os-vif OVS reference plugin to accept and use the new versions and
  fields.

Future os-vif plugins combining an existing form of datapath offload (i.e.
switchdev offload) with a new VIF type will not require modifications to
os-vif. Future datapath offload methods will require subclassing
``DatapathOffloadBase``.

Instead of implementing potentially brittle backlevelling code, this option
proposes to keep two parallel interfaces alive in Nova for at least one
overlapping release cycle, before the Open vSwitch plugin is updated in os-vif.

Instead of bumping object versions and creating composition version maps, this
option proposes that versioning be deliberately ignored until the next major
release of os-vif. Currently, version negotiation and backlevelling in os-vif
is not used in Nova or os-vif plugins.

Kuryr Kubernetes is also a user of os-vif and is using object versioning in a
manner not yet supported publicly in os-vif. There is an `ongoing discussion
attempting to find a solution for Kuryr's use case`_.

Should protocol offloads also need to be modeled in os-vif, ``VIFBase`` or
``VIFPortProfileBase`` could gain a ``protocol_offloads`` list of capabilities.

Summary of plugging methods affected
------------------------------------

* Before changes:

  * VIF type: ``ovs`` (os-vif plugin: ``ovs``)

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile: VIFPortProfileOVSRepresentor``

  * VIF type: ``agilio_ovs`` (os-vif plugin: ``agilio_ovs``)

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile: VIFPortProfileOVSRepresentor``

  * VIF type: ``agilio_ovs`` (os-vif plugin: ``agilio_ovs``)

    * VNIC type: ``virtio-forwarder``
    * os-vif object: ``VIFVHostUser``
    * ``port_profile: VIFPortProfileOVSRepresentor``

* After this model has been adopted in Nova:

  * VIF type: ``ovs`` (os-vif plugin: ``ovs``)

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile: VIFPortProfileOpenVSwitch``
    * ``port_profile.datapath_offload: DatapathOffloadRepresentor``

  * VIF type: ``agilio_ovs`` (os-vif plugin: ``agilio_ovs``)

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile: VIFPortProfileOpenVSwitch``
    * ``port_profile.datapath_offload: DatapathOffloadRepresentor``

  * VIF type: ``agilio_ovs`` (os-vif plugin: ``agilio_ovs``)

    * VNIC type: ``virtio-forwarder``
    * os-vif object: ``VIFVHostUser``
    * ``port_profile: VIFPortProfileOpenVSwitch``
    * ``port_profile.datapath_offload: DatapathOffloadRepresentor``


Additional Impact
-----------------

os-vif needs to issue a release before these profiles will be available to
general CI testing in Nova. Once this is done, Nova can be adapted to use the
new generic interfaces.

* In Stein, os-vif's object model will gain the interfaces described in this
  spec. If needed, a major os-vif release will be issued.
* Then, Nova will depend on the new release and use the new interfaces for new
  plugins.
* During this time, os-vif will have two parallel interfaces supporting this
  metadata. This is expected to last at least from Stein to Train.
* From Train onwards, existing plugins should be transitioned to the new
  model.
* Once all plugins have been transitioned, the parallel interfaces can be
  removed in a major release of os-vif.
* Support will be lent to Kuryr Kubernetes during this period, to transition to
  a better supported model.

Additional notes
----------------

* No corresponding changes in Neutron are expected: currently os-vif is
  consumed by Nova and Kuryr Kubernetes.
* Even though representor addresses are currently modeled as PCI address
  objects, it was felt that stricter type checking would be of limited
  benefit. Future networking systems might require paths, UUIDs or other
  methods of describing representors. Leaving the address member a string was
  deemed an acceptable compromise.
* The main concern raised against composition over inheritance was the increase
  of the serialization size of the objects.

Alternatives
------------

During the development of this spec it was not immediately clear whether the
composition or inheritance model would be the consensus solution. Because the
two models have wildly different effects on future code, it was decided that
both be implemented in order to compare and contrast.

The implementation for the inheritance model is illustrated in
https://review.openstack.org/608693

Use inheritance to create a generic representor profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep using an inheritance based pattern to model the offload capabilities and
metadata:

* Implement ``VIFPortProfileRepresentor`` by subclassing ``VIFPortProfileBase``
  and adding the following members:

    * ``representor_name: StringField(nullable=True)``
    * ``representor_address: StringField()``

Summary of new plugging methods available in an inheritance model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* After os-vif changes:

  * Generic VIF with SR-IOV passthrough:

    * VNIC type: ``direct``
    * os-vif object: ``VIFHostDevice``
    * ``port_profile: VIFPortProfileRepresentor``

  * Generic VIF with virtio-forwarder:

    * VNIC type: ``virtio-forwarder``
    * os-vif object: ``VIFVHostUser``
    * ``port_profile: VIFPortProfileRepresentor``

Other alternatives considered
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Other alternatives proposed require much more invasive patches to Nova and
os-vif:

* Create a new VIF type for every future datapath/offload combination.

* The inheritance based pattern could be made more generic by renaming the
  ``VIFPortProfileOVSRepresentor`` class to ``VIFPortProfileRepresentor`` as
  illustrated in https://review.openstack.org/608448

* The versioned objects could be backleveled by using a suitable negotiation
  mechanism to provide overlap.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

os-vif plugins run with elevated privileges, but no new functionality will be
implemented.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Extending the model in this fashion adds more bytes to the VIF objects passed
to the os-vif plugin. At the moment, this effect is negligible, but when the
objects are serialized and passed over the wire, this will increase the size of
the API messages.

However, it's very likely that the object model would undergo a major
version change with a redesign, before this becomes a problem.

Other deployer impact
---------------------

Deployers might notice a deprecation warning in logs if Nova, os-vif or the
os-vif plugin is out of sync.

Developer impact
----------------

Core os-vif semantics will be slightly changed. The details for extending
os-vif objects would be slightly more established.

Upgrade impact
--------------

The minimum required version of os-vif in Nova wil be bumped in both
``requirements.txt`` and ``lower-constraints.txt``. Deployers should be
following at least those minimums.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Jan Gutter <jan.gutter@netronome.com>

Work Items
----------

* Implementation of the composition model in os-vif:
  https://review.openstack.org/572081

* Adopt the new os-vif interfaces in Nova. This would likely happen after a
  major version release of os-vif.

Dependencies
============

* After both options have been reviewed, and the chosen version has been
  merged, an os-vif release needs to be made.

* When updating Nova to use the newer release of os-vif, the corresponding
  changes should be made to move away from the deprecated classes. This change
  is expected to be minimal.

Testing
=======

* Unit tests for the os-vif changes will test the object model impact.

* Third-party CI is already testing the accelerated plugging modes, no new
  new functionality needs to be tested.

Documentation Impact
====================

The os-vif development documentation will be updated with the new classes.

References
==========

* `ethtool man page`_
* `TC Flower Offload paper`_
* `virtio-forwarder`_
* `Open vSwitch offloads`_
* `switchdev SR-IOV offloads`_
* `blueprint for vrouter hardware offloads`_
* `list of VNIC types that will trigger a PCI request`_
* `section in the API where the PCI request is triggered`_
* `ongoing discussion attempting to find a solution for Kuryr's use case`_

.. _`ethtool man page`: http://man7.org/linux/man-pages/man8/ethtool.8.html
.. _`TC Flower Offload paper`: https://www.netdevconf.org/2.2/papers/horman-tcflower-talk.pdf
.. _`virtio-forwarder`: http://virtio-forwarder.readthedocs.io/en/latest/
.. _`Open vSwitch offloads`: https://docs.openstack.org/neutron/queens/admin/config-ovs-offload.html
.. _`switchdev SR-IOV offloads`: https://netdevconf.org/1.2/slides/oct6/04_gerlitz_efraim_introduction_to_switchdev_sriov_offloads.pdf
.. _`blueprint for vrouter hardware offloads`: https://blueprints.launchpad.net/nova/+spec/vrouter-hw-offloads
.. _`list of VNIC types that will trigger a PCI request`: https://github.com/openstack/nova/blob/e3eb5f916580a9bab8f67b0fd685c6b3b23a97b7/nova/network/model.py#L111
.. _`section in the API where the PCI request is triggered`: https://github.com/openstack/nova/blob/e3eb5f916580a9bab8f67b0fd685c6b3b23a97b7/nova/network/neutronv2/api.py#L1921
.. _`ongoing discussion attempting to find a solution for Kuryr's use case`: http://lists.openstack.org/pipermail/openstack-discuss/2018-December/000569.html
