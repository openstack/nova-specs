..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Tenant networking support for Ironic driver
===========================================

https://blueprints.launchpad.net/nova/+spec/ironic-networks-support

Currently, Ironic only works on a flat network shared between control plane and
tenants. There's an ongoing effort to allow for arbitrary networks to be
connected to Ironic nodes in various configurations.[0][1] Some changes in Nova
are required to support this effort.

Problem description
===================

Ironic currently supports a single flat network shared between the control
plane and tenants. This causes Ironic to be unusable in multitenant
environments, or by users that wish to have an isolated network.

* Multitenant deployments

* Deployments that wish to secure the control plane from tenants

* Deployments that wish to use "advanced" network configurations such as LAG,
  MLAG, bonding, VLAN/VXLAN

Use Cases
----------

* Deployers that wish to deploy a multitenant environment.

* Deployers that wish to isolate the control plane from tenants.

* Deployers that wish to deploy baremetal hosts using "advanced" network
  configurations such as LAG, MLAG, bonding, VLAN/VXLAN.

* Users that wish to use isolated networks with Ironic instances.

Proposed change
===============

* The port-create calls to Neutron, during instance spawn in the Neutron
  network driver, need to be made with a null binding:host_id. This signals to
  Neutron that it shouldn't bind the port yet. To keep the provisioning process
  away from the tenant network, we need to wait for the deployment to complete
  before binding the port, which only Ironic can control. As part of the
  deployment process, Ironic will make a port-update call with: 1) a
  binding:host_id value of "baremetal:$node_uuid", and 2) physical switchport
  information necessary to connect the port. This will happen while the virt
  driver is waiting for the Ironic node to get a state of "active".

  To accomplish this, we'll need to allow the virt driver to define the
  `binding:host_id` field. So we'll need to add a method to the base virt
  driver class, defaulting to the current value (instance.host), and override
  that in the ironic driver if the node is using the new networking model (this
  will be available in the network_provider attribute for the Ironic node).

  The `plug_vifs` and `unplug_vifs` methods will also need to be similarly
  modified to pass the VIF UUID to port groups and ungrouped port objects,
  rather than all ports.

* Ironic now has a concept of "port groups"[1], which is a single logical
  connection comprised of multiple physical NICs; used in LAG and MLAG
  configurations.  These are a first-class citizen in the API. The
  `macs_for_instance` method in the ironic driver needs to be changed to report
  MACs for both port groups and ungrouped ports. For example::

    # the old method
    [port.address for port in get_ports_for_node()]

    # the new method
    ([port.address for port in get_ungrouped_ports_for_node()] +
     [portgroup.address for portgroup in get_portgroups_for_node()])

* A BAREMETAL vnic type will be added to the network model to support the
  BAREMETAL vnic type that was previously added in Neutron.[3]

This will support the basic tenant networking support we are building out in
Ironic. In the future, we'll want to support multiple networks via VLAN or
VXLAN over a pair of bonded NICs (currently Nova enforces a 1:1 mapping of NICs
to networks, as in the virtual world NICs can be created on the fly), but these
items are outside the scope of this spec.

Alternatives
------------

One alternative is to subclass the NeutronAPI to have it do what we want. This
may help make the future work noted above easier. However, as this is used at
the API and conductor layers, doing this may break multi-hypervisor
deployments.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

This enables users and deployers to improve the network security for the
control plane and Ironic instances.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users will be able to use arbitrary networks with Ironic instances. In the
future, we should investigate how to allow the user to specify which physical
connection gets connected to which network; however, that is outside the scope
of this spec.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None. The flag to use this or not is an attribute on Ironic's node object.
There's no extra configuration to do on the Nova side to use this feature.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Other contributors:
  Sukhdev
  lazy_prince

Work Items
----------

* Cause port-create calls to send a null binding:host_id.

* Add the BAREMETAL vnic type.

* Make changes to the Ironic driver to handle Ironic "port groups" in addition
  to Ironic "ports".


Dependencies
============

This depends heavily on work being done in Ironic.[0][1]

Note that while this work is not complete at the time of this writing, it has
made good progress and is expected to land well before the end of the Mitaka
cycle.

Testing
=======

CI jobs that exercise this code are being created as part of the Ironic work;
we should also have those jobs run against Nova.

Documentation Impact
====================

There is substantial documentation work to be done on the Ironic side, however
there isn't any work to do on the Nova side.

References
==========

[0] https://blueprints.launchpad.net/ironic/+spec/network-provider

[1] https://blueprints.launchpad.net/ironic/+spec/ironic-ml2-integration

[2] https://blueprints.launchpad.net/neutron/+spec/neutron-ironic-integration

[3] https://review.openstack.org/#/c/197774/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
