..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Boot a VM with an unaddressed port
==================================

https://blueprints.launchpad.net/nova/+spec/boot-vm-with-unaddressed-port

This blueprint aims to allow a VM to boot with an attached port without any IP
assigned.


Problem description
===================

Currently Neutron permits users to create a port assigned to a network with
corresponding subnets and IP pools, without an IP address assigned. However
Nova only allows users to create a VM with a port without an IP only if this
address assignment is deferred; that means that the port is expected to have
an IP address but Neutron deferred the IP allocation until the host to which
the port will be bound is populated.

However, there are some network applications (e.g.: service function
forwarding, service function classifier, CMTS) that often forward traffic that
is not intended for them. Those applications have an interface without a
primary L3 address which may be receiving traffic for so many disparate
addresses that configuring all of them in Neutron is a burden.

Use Cases
---------

A typical use case is when a user wishes to deploy a VM which accepts traffic
that is neither IPv4 nor IPv6 in nature. For example, a CMTS (Cable Modem
Termination System).

Another use case could be a VM that accepts traffic for a very wide address
range (for either forwarding or termination) and where the port has no primary
address. In such cases, the VM is not a conventional application VM.


Proposed change
===============

This spec proposes to allow to spawn a VM with a manually created port without
IP address assignation.

When a port in Neutron is created with the option "--no-fixed-ip", the port
parameter ``ip_allocation`` [1]_ will be populated with "none" [2]_. This way
Neutron marks a port not to have an IP address. Nova, during the instance
creation, validates the build options; in particular the ports provided to be
bound to this new VM. To be able to use an unaddressed port, Nova needs to
modify the logic where IP assignation is tested [3]_.

Alternatives
------------

As commented in the use cases, some applications will accept traffic that is
neither IPv4 nor IPv6. Having an IP address is irrelevant on those ports but
doesn't affect the application.

In other cases, like in a routing application, there is no alternative. It's
not possible to define in Neutron all the possible IP addresses.

Data model impact
-----------------

None

The Neutron port contains the information needed in the ``ip_allocation``
parameter and the ``connectivity`` parameter inside the
``binding:vif_details``.


REST API impact
---------------

None


Security impact
---------------

Those ports without an assigned IP don't work with the Neutron in-tree
firewalls (iptables and OVS Open Flows based). Both firewalls will filter the
egress and the ingress traffic depending on several parameters, including the
IP address. To let the traffic come into the virtual interface, the firewall
should be disabled in the compute node hosting the VM. This mandatory
configuration will be documented.

Once the Nova feature is implemented and tested, a new feature will be
requested to Neutron, in order to allow those ports without an IP address to
work correctly with the in-tree firewalls.

Notifications impact
--------------------

None

Other end user impact
---------------------

To be able to remotely access to the created VM, the user needs to add an
addressed port to the VM. This "management" port must have an IP address.

Performance Impact
------------------

None

Other deployer impact
---------------------

Some L2 driver, like "l2-pop", may have problems when dealing with this kind of
port because they use proxy ARP to answer ARP requests from known IP address.

The ["novnc"] service won't work with a port without an IP address. This is why
it's recommended to create a VM with at least one management port, with an
assigned IP address.

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

Primary assignee:
  stephenfinucane

Other contributors:
  Rodolfo Alonso <rodolfo-alonso-hernandez> (ralonsoh@redhat.com)

Feature Liaison
---------------

Feature liaison:
  stephenfinucane


Work Items
----------

Work items:

- Change the logic of how the IP assignation is tested [3]_.
- Implement the tempest test described.
- Create a new Neutron feature request to change the in-tree firewalls to work
  correctly with those ports without IP address assigned.


Dependencies
============

None. The necessary work in neutron has already been accomplished via two
specs. The main neutron change was allowing for the creation of an unaddressed
port and mark it, by populating the ``ip_allocation`` parameter with ``none``.
This was covered by the "Allow vm to boot without l3 address(subnet)" [5]_
spec. The changes introduced as part of the "Port binding event extended
information for Nova" [4]_ spec means neutron will now provide the type of
back-end to which the port is bound, with the parameter ``connectivity``,
included now in ``binding:vif_details``. Nova can determine whether a given
driver back-end has "l2" connectivity and, if so, know that a port without an
IP address can be assigned to a virtual machine.


Testing
=======

Apart from the needed functional and unit testing, a tempest test could cover
this feature. This tempest test will spawn three VMs, each one with a
management port, to be able to SSH to the machine. Then two traffic networks
will be created, net1 and net2.

The first machine will have a port, with an IP assigned, connected to net1.
The third machine will have a port, with an IP assigned, connected to net2.
And finally, the second machine, in the middle of the first and the third one,
with be connected to net1 and net2 with two ports without an IP address.
The second machine will have the needed iptables rules to NAT the traffic
between the first VM and the third VM port.

Both the first and the third machine will need a manual entry in the ARP table
to force the traffic going out trough the traffic port.


Documentation Impact
====================

- Make a reference of this feature in the user document "Launch instances"
  [6]_.


References
==========

.. [1] https://github.com/openstack/neutron/blob/stable/rocky/releasenotes/notes/add-port-ip-allocation-attr-294a580641998240.yaml
.. [2] https://github.com/openstack/neutron/blob/stable/rocky/neutron/db/db_base_plugin_v2.py#L1323
.. [3] https://github.com/openstack/nova/blob/stable/rocky/nova/network/neutronv2/api.py#L2078-L2086
.. [4] https://review.opendev.org/#/c/645173/
.. [5] https://blueprints.launchpad.net/neutron/+spec/vm-without-l3-address
.. [6] https://github.com/openstack/nova/blob/stable/rocky/doc/source/user/launch-instances.rst


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Xena
     - Reproposed
