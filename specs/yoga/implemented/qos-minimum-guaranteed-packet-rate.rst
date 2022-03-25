..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
QoS minimum guaranteed packet rate
==================================

https://blueprints.launchpad.net/nova/+spec/qos-minimum-guaranteed-packet-rate

Similarly to how bandwidth can be a limiting factor of a network interface,
packet processing capacity tend to be a limiting factor of the soft switching
solutions like OVS. In the same time certain applications are dependent on not
just guaranteed bandwidth but also on guaranteed packet rate to function
properly. OpenStack already supports bandwidth guarantees via the
`minimum bandwidth QoS policy rules`_. This specification is aiming for adding
support for a similar minimum packet rate QoS policy rule.

.. _`minimum bandwidth QoS policy rules`: https://docs.openstack.org/api-ref/network/v2/?expanded=#qos-minimum-bandwidth-rules

To add support for the new QoS rule type both Neutron and Nova needs to be
extended. This specification covers the high level description of these
impacts, the interaction between Neutron, Placement and Nova. And have
the details of the Nova specific changes necessary. For the detailed
description of the Neutron impact please see the `Neutron specification`_.

Problem description
===================

OpenStack needs to provide support for minimum packet rate guarantees on
Neutron ports via a new QoS policy rule type.

Use Cases
---------

I as an administrator want to define the maximum packet rate, in kilo packet
per second (kpps), my OVS soft switch capable of handle per compute node, so
that I can avoid overload on OVS.

I as an end user want to define the minimum packet rate, in kilo packet per
second (kpps) a Neutron port needs to provide to my Nova server, so that my
application using the port can work as expected.

I as an administrator want to get a Nova server with such ports placed on a
compute node that can still provide the requested minimum packet rate for the
Neutron port so that the application will get what it requested.

I as an administrator want that the nova server lifecycle operations are
rejected in case the requested minimum packet rate guarantee of the Neutron
ports of the server cannot be fulfilled on any otherwise eligible compute
nodes, so that the OVS overload is avoided and application guarantees are kept.

Proposed change
===============
The whole solution is very similar and the proposed implementation heavily
rely on the already implemented `qos guaranteed minimum bandwidth feature`_.

.. _`qos guaranteed minimum bandwidth feature`: https://specs.openstack.org/openstack/nova-specs/specs/stein/implemented/bandwidth-resource-provider.html

New resources
-------------

The solution needs to differentiate between two deployment scenarios.

1) The packet processing functionality is implemented on a shared hardware
   (e.g. on the same compute host CPUs) and therefore both ingress and egress
   queues are handled by the same hardware resources. This is the case in the
   non-hardware-offloaded OVS deployments. In this scenario OVS represents a
   single packet processing resource pool. Which can be represented with a
   single new resource class, ``NET_PACKET_RATE_KILOPACKET_PER_SEC``.

2) The packet processing functionality is implemented in a specialized hardware
   where the ingress and egress queues are processed by independent
   hardware resources. This is the case for hardware-offloaded OVS. In this
   scenario a single OVS has two independent resource pools one for the
   incoming packets and one for the outgoing packets. Therefore these needs to
   be represented with two new resource classes
   ``NET_PACKET_RATE_EGR_KILOPACKET_PER_SEC`` and
   ``NET_PACKET_RATE_IGR_KILOPACKET_PER_SEC``.

.. note::
    1 kilo packet means 1000 packets in the context of packet rate resource.

These new resource classes needs to be added to Placement's os-resource-classes
library.

Packet processing resource inventory
------------------------------------

The bandwidth resources are modelled on the OVS physnet bridges as each bridge
is connected to a specific physical NIC that provides the bandwidth resource.
As the packet processing resource is provided by the OVS service itself
therefore the packet processing resource needs to be modeled on an entity that
is global for the whole OVS service. Today we have such entity, the Neutron OVS
agent itself. This assumes that one Neutron OVS agent only handles one OVS
which is true today. We think this assumption is strong one. If later on two
vswitches are needed on the same compute host then we think it is easier to
duplicate the agents handling them separately than enhancing the current agent
to handle two switches.

Resource inventory reporting
----------------------------
For details of these Neutron changes please see the `Neutron specification`_.

* Neutron OVS agent needs to provide configuration options for the
  administrator to define the maximum packet processing capacity of the OVS
  per compute node. Depending on the deployment scenario this might mean a
  single directionless inventory value, or two direction aware values.

* Neutron agent needs to communicate the configured capacity to the Neutron
  server via the agent hearth beat.

* Neutron server needs to report ``NET_PACKET_RATE_KILOPACKET_PER_SEC`` or
  ``NET_PACKET_RATE_[E|I]GR_KILOPACKET_PER_SEC`` resource inventory on the
  ``Open vSwitch agent`` resource provider to Placement.


Requesting minimum packet rate guarantees
-----------------------------------------
For details of these Neutron changes please see the `Neutron specification`_.

Neutron QoS API needs to be extended with the new minimum packet rate QoS rule
type. The rules of this type need to be persisted in the neutron DB similarly
to the other QoS rules.

To support the two different OVS deployment scenario we need two sets of new
minimum guaranteed QoS rule types. One which is directionless to support the
case when the resource is also directionless. And two other that are direction
aware to support the other deployment case where the pps resource are also
direction aware.

Nova servers with the new QoS policies
--------------------------------------
Today Neutron expresses the resource needs of a port via the
``resource_request`` field. The value of this field is intended to communicate
the resource needs in a generic, machine readable way. Nova and
(and indirectly Placement) uses this during the scheduling of the server to
decide which compute host can fulfill the overall resource needs of the server
including the ports of the server. So far the port can only have bandwidth
resource request.

To support the new packet rate resource Neutron API needs to be changed so that
the ``resource_request`` read only field of the port could contain more than
one group of requested resources and required traits. Today the content of the
``resource_request`` is translated to a single, named Placement request group
during scheduling. As a single port can have both bandwidth and packet rate QoS
applied and because bandwidth is allocated from the bridge / physical device
while the packet rate resource is allocated from the whole OVS instance the two
groups of resources need to be requested separately. The technical reason to
this is that a single named resource request group is always allocated from a
single resource provider in Placement. So if bandwidth and packet rate does not
need to come from the same resource provider then they should be requested in
different resource request groups.

The new format of the ``resource_request`` is::

    {
        "request_groups":
        [
            {
                "id": <some unique identifier string of the group>
                "required": [<CUSTOM_VNIC_TYPE traits>],
                "resources":
                {
                    NET_PACKET_RATE_[E|I]GR_KILOPACKET_PER_SEC:
                    <amount requested via the QoS policy>
                }
            },
            {
                "id": <some unique identifier string of the group>
                "required": [<CUSTOM_PHYSNET_ traits>,
                             <CUSTOM_VNIC_TYPE traits>],
                "resources":
                {
                    <NET_BW_[E|I]GR_KILOBIT_PER_SEC resource class name>:
                    <requested bandwidth amount from the QoS policy>
                }
            },
        ],
       "same_subtree":
        [
            <id of the first group from above>,
            <id of the second group from above>
        ]
    }

For the reasoning why we need this format see the `Neutron specification`_

The Neutron port binding API needs to be extended. Today the ``allocation``
key in the ``binding:profile`` of the port is used by Nova to communicate the
UUID of the resource provider from which the ``resource_request`` of the port
is fulfilled from. This is then used by the Neutron's port binding logic to
bind the port to the same physical device the Placement resource is allocated
from. Now that a port can request resources from more than one placement
resource providers a single UUID is not enough to communicate where those
resources are allocated from. Nova needs to provide a mapping instead that
describes which set of resource, a.k.a which request group, is fulfilled from
which resource provider in placement.

For the details of the new structures see the `Neutron specification`_

Adapting Nova to the Neutron changes
------------------------------------

* Nova needs to adapt to the changes in the structure and semantics of the
  ``resource_request`` field of the neutron port. Today Nova translates this
  field to a single named resource request group. After the Neutron changes
  this field will communicate a list of such request groups.

* Nova also assumes today that a port only allocates resource from a single
  resource provider. This assumption needs to be removed and the implementation
  needs to support a list of such resource providers. Nova can still assume
  that a single placement request group is fulfilled by a single resource
  provider as that is an unchanged Placement behavior.

These Nova changes needs to be applied to every code path in Nova that results
in a new scheduling attempt including:

* server create

* migrate, resize, evacuate, live-migrate, unshelve after shelve-offload

* interface attach and detach

What is out of scope
--------------------
Supporting minimum packet rate policy for other than OVS backends are out of
scope but can be handled later with a similar proposal.

This spec only aiming to give scheduling time guarantees for the packet
rate. The data plane enforcement of the new policy is out of scope. When the
`packet rate limit policy rule`_ feature is implemented then a basic data plane
enforcement can be applied by adding both minimum and maximum packet rate QoS
rules to the same QoS policy where maximum limit is set to be equal to the
minimum guarantee.

Alternatives
------------

Packet processing resource inventory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Alternatively* it was suggested to define the packet processing inventory
on the OVS bridge level. The big advantage of having the pps resource
represented on the OVS bridge, on the same place as the bandwidth resource, is
that it would simplify the overall design. It would means that we could still
keep the assumption that the resource request of the port is always fulfilled
from a single resource provider. Therefore the format of the
``resource_request`` and the ``binding:profile.allocation`` does not need to
change. However there are a list of counter arguments against this direction:

* If we define packet processing capacity on the bridges then if there are
  multiple bridges then the overall packet processing capacity of the whole OVS
  would need to be statically split between the bridges, while the actual
  resource usage of OVS are not split in that way in reality.
  Configuration with multiple bridges are possible today, even in the
  frequently used case of having one phynet bridge for VLAN traffic and one
  tunneling bridge for the VXLAN traffic.

* In case of bandwidth the actual resource is behind the physnet bridge, the
  physical interface the bridge is connected to, so the resource is dedicated
  to the bridge. But in case of packet processing the actual resource is not at
  all dedicated to the given bridge but it is dedicated to the whole OVS
  instance. So while we can assign a portion of the overall resource to the
  bridge this assignment would never represent the reality well.

* Traffic between the VMs on the same host does not flow through the physnet or
  tunneling bridges but it does impact the capacity of the OVS on the host.

* While the currently proposed design change is significant it makes the
  solution more future proof. E.g. for the case when the IP pool resource
  handling will be refactored to use the port's resource_request then we anyhow
  need to be able to handle another resource provider that will not be the same
  as any of the existing ones as the IP addresses are shared resource between
  multiple host.

*Another alternative* would be to represent the packet processing capacity on a
new provider that maps to ``br-int`` the OVS integration bridge where the VMs
are plugged. This have the benefit that the resource inventory would be global
on OVS instance level and also it would clean up some of the confusion created
by having a separate OVS Agent RP. Moving further we could even consider
dropping the Agent RP altogether and only representing the bridge hierarchy in
Placement with the resource provider hierarchy. Logically it is not different
from that we rename today's OVS Agent RP to br-int RP. However `we agreed`_
that keep this as a future exercise if and when more OVS instances would be
needed per OVS agent.

.. _we agreed: http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2021-05-21.log.html#t2021-05-21T10:33:22

Requesting minimum packet rate guarantees
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Alternatively* it was suggested that it would be enough to have a single set
of direction aware QoS rule types. Then in case of the normal OVS deployment
scenario, where the resource is directionless, the resource requests from the
direction aware QoS rules could be added together before matched against the
single directionless resource inventory. Neutron would be able to differentiate
between the two deployment situation on the port level based on the
``vnic_type`` of the port. The ``normal`` ``vnic_type`` means that the port is
requested to be backed by a normal OVS with directionless resource accounting.
While the ``direct`` ``vnic_type`` means the port is requested to be backed by
a hardware-offloaded OVS (or non OVS backend, like SRIOV) with a direction
aware resource inventory.

Data model impact
-----------------
No Placement DB schema changes expected.

For the Neutron DB changes see the `Neutron specification`_.

No Nova DB schema changes are expected.

Some Nova o.v.o changes are expected.

The RequestSpec object already stores a list of RequestGroups as it needs to
support multiple ports and cyborgs devices per Instance already.

The RequestGroup object does not assume anything about the format of the
``requester_id`` field. However the parts of nova that drives the PCI claim
based on the already allocated bandwidth assumes that the
``InstancePCIRequest.requester_id`` is the same ``port_id`` as the
``RequestGroup.requester_id``. To facilitate distinction between different
groups requested by the same port this assumption needs to be removed. This
needs a new field ``group_id`` in the RequestGroup object that stores the
group id from the ``requested_resources`` while we keep the ``requester_id``
to be the ``port_id`` as today. The PCI request update logic needs to be
changed to use the group with the bandwidth resource to drive the PCI claim.
This creates an unfortunate dependency between the Nova code and the content
of the ``resource_request``. We can remove this dependency one we start
modeling PCI devices in Placement.

The RequestLevelParams object also needs to be extended to store a list of
``same_subtree`` requests coming from the ``same_subtree`` field of the
``resource_request``.

See the changes in the handling of the ``allocation`` key in the port's
``binding:profile`` how this might change in the `Neutron specification`_

The Neutron related resource provider model in Placement needs to be extended
with a new inventory of ``NET_PACKET_RATE_KILOPACKET_PER_SEC``,
``NET_PACKET_RATE_EGR_KILOPACKET_PER_SEC``, and
``NET_PACKET_RATE_IGR_KILOPACKET_PER_SEC`` resources on the OVS agent resource
providers if such resource inventory is configured in the related agent
configuration by the administrator. Also the ``CUSTOM_VNIC_TYPE_`` that today
applied only to the bridge and device RPs needs to be reported on the OVS Agent
RP to facilitate proper scheduling. Note that ``CUSTOM_PHYSNET_`` traits are
not needed for the packet rate scheduling as this resource is not split
between the available physnets.

REST API impact
---------------

For the Neutron REST API changes see the `Neutron specification`_.

This feature does not change the Nova API, only adapts Nova to be able to
consume the new Neutron API extension. A Nova microversion alone could not
signal the availability of the feature to the end user as with Xena Neutron
and Yoga Nova, even with latest Nova microversion, this feature will not be
available. Therefore no microversion bump will be added. What we suggest
instead is that the end users decide on feature availability based on what QoS
policies the admin created for them. If QoS policies with the new minimum
guaranteed QoS policy rule is available to the end users then they can be sure
that the feature is available. See the `IRC log`_ for further discussion.

.. _IRC log: http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2021-05-21.log.html#t2021-05-21T10:51:46

If, due to scoping, support for some of the lifecycle operations is not
implemented in the current release cycle then those operations will be rejected
with HTTP 400.


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
There will be extra calls to the Neutron ``GET /extensions`` API during the
server lifecycle operations to detect which format of the ``resource_request``
is used by Neutron and what format the ``binding:profile.allocation`` is
expected by Neutron. This is temporary to support an upgrade scenario where
Nova is already upgraded to Yoga but Neutron isn't. In Z release we can
remove the extra call and assume that Neutron always returns the new format.


Other deployer impact
---------------------
No new configuration option is proposed to Nova but to use this feature Neutron
needs to be properly configured. See `Neutron specification`_ for details.

Developer impact
----------------

None

Upgrade impact
--------------
OpenStack needs to support deployments where the major version of Neutron and
Nova are different. This means that changes for this feature needs to be
written to support both cases:

* Xena Neutron - Yoga Nova
* Yoga Neutron - Xena Nova

Neutron will introduce a new API extension that will change the structure and
the semantic of the ``resource_request`` field of the port. Nova needs to
check the existence of the new API extension and parse the field accordingly.

As Nova in Xena merged the changes, except the nova-manage changes, to support
the new Neutron API extension, such extension can be enabled by default in
Neutron in Yoga. The Yoga Neutron will work with Xena Nova properly.

In the other hand Yoga Nova needs to understand both the old Neutron API if
Neutron is still on Xena level, and the new API if Neutron is also upgraded
to Yoga.

As the changes impacting the nova-compute service a new service version
will be introduced. Nova will reject any lifecycle operation
(server created, delete, migration, resize, evacuate, live-migrate, unshelve
after shelve-offload, interface attach and detach) with HTTP 400 if the new
Neutron API extension is enabled but there are compute services in the
deployment with old service version not supporting the new extension.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  balazs-gibizer

Work Items
----------

* Reject all lifecycle operations with HTTP 400 if the Neutron API extension
  changing the structure of the ``resource_request`` field is enabled.
  As we add support for each operation the rejection is removed from the given
  operation. This way whenever we hit feature freeze we will have a consistent
  system that rejects what is not supported.

* Propose the new resource classes to Placement's os-resource-classes library

* Enhance the ``resource_request`` parsing logic to support the new format

* Use the new parsing logic if the new Neutron API extension is enabled

* For each lifecycle operation:

  * Remove assumption from the code that a single port only request a single
    request group. If this requires a nova-compute change then bump the service
    version and add a check to the API side to reject the operation if there
    are old computes in the cluster

  * Enable the operation by removing the automatic rejection and keeping only
    the service version check.

* Adapt the implementation of the nova-manage placement heal_allocation CLI to
  the new ``resource_request`` format.

Dependencies
============

* The new Neutron API extension for the port's ``resource_request`` as defined
  in the `Neutron specification`_.

Testing
=======

Integration testing can be done in the upstream CI system with the standard
OVS backend through tempest. The hardware-offloaded OVS case cannot be tested
in upstream CI.

Top of the automatically assumed unit test coverage an extensive set of
functional test will be added to cover the relevant lifecycle operations with
ports having either just minimum packet rate QoS policy rules or both minimum
bandwidth and minimum packet rate QoS rules.

Documentation Impact
====================

* `API guide`_
* `Admin guide`_
* Document Nova's expectation on the format of the ``resource_request`` field
  of the Neutron port in the developer documentation.

.. _API guide: https://docs.openstack.org/api-guide/compute/port_with_resource_request.html
.. _Admin guide: https://docs.openstack.org/nova/latest/admin/ports-with-resource-requests.html

References
==========

* `Neutron specification`_ complementing this spec about the neutron details
* Neutron RFE for `packet rate limit policy rule`_.

.. _`packet rate limit policy rule`: https://bugs.launchpad.net/neutron/+bug/1912460
.. _`Neutron specification`: https://review.opendev.org/c/openstack/neutron-specs/+/785236


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced and merged support for the new Neutron API extension except
       in the nova-manage placement heal_allocations CLI
   * - Yoga
     - Re-proposed to finish up the nova-manage part
