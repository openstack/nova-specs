..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
New VIF type to allow routing VM data instead of bridging it
============================================================

https://blueprints.launchpad.net/nova/+spec/vif-type-tap

We propose to add a new VIF type, VIF_TYPE_TAP, whose meaning is that
the host side of a VNIC to a VM is - at least initially - a simple TAP
interface that is not plugged into a bridge or vSwitch.  A Neutron
agent can continue the process of deciding how to handle data from
that interface, and how to deliver data to it - but this is beyond the
scope of the initial TAP interface setup that Nova needs to provide.


Problem description
===================

For Project Calico (http://www.projectcalico.org/), we'd like the host
side of the pipe into a VM to be a simple, unbridged TAP interface,
and currently there is no VIF_TYPE that I can use to get this.

VIF_TYPE_MIDONET, VIF_TYPE_IOVISOR and VIF_TYPE_IVS (without firewall
or hybrid plug) all create an unbridged TAP interface, but then do
additional things to it (within the Nova code) to connect that TAP
interface into the host's networking system.  Other VIF_TYPEs involve
bridges or vSwitches, or 'direct' attachments to physical host
interfaces.

Use Cases
---------

One application is that VIF_TYPE_TAP makes it possible for data
to/from VMs, and also between VMs on the same host, to be routed by
their immediate compute host instead of being bridged.  This is of
interest in deployments where VMs only require services at layer 3
(IP) and above, and it is still possible to implement, through
iptables and route distribution filters, all of the detailed
connectivity and security policies that are implied by any given set
of OpenStack's networking, security group and router configurations.
For more on how that can work please see Project Calico
(http://www.projectcalico.org/) and
https://blueprints.launchpad.net/neutron/+spec/calico-mechanism-driver.

The applicability of VIF_TYPE_TAP should however be wider than just
that one project.  It enables a class of experimental future
networking implementations to be explored in Neutron (with plugin,
mechanism driver and agent code) without needing to change or patch
any Nova code.

Project Priority
----------------

Not applicable.  (As advised by John Garbutt.)

(However we would argue that VIF_TYPE_TAP supports the
"Nova-network/Neutron migration" priority listed at
https://github.com/openstack/nova-specs/blob/master/priorities/kilo-priorities.rst,
in that it allows some forms of network connectivity to be explored
and developed without needing further changes to the Nova code.)


Proposed change
===============

Add VIF_TYPE_TAP in nova/network/model.py.

Add get_config_tap, plug_tap and unplug_tap methods in
nova/virt/libvirt/vif.py, with implementations that simply configure,
create and delete a TAP device.

The libvirt config for VIF_TYPE_TAP would be an <interface
type="ethernet"> element with a null script, just as for the existing
VIF_TYPE_MIDONET and VIF_TYPE_IOVISOR cases, prepared by calling
self.get_base_config and
designer.set_vif_host_backend_ethernet_config.

When a VM is to be launched using VIF_TYPE_TAP:

- Nova creates the TAP interface, in plug_tap(), by calling
  linux_net.create_tap_dev

- libvirt launches the VM, with the config described just above, to
  match the created TAP interface.

Alternatives
------------

None.  All existing VIF_TYPEs whose plugging is implemented in
nova/virt/libvirt/vif.py are unsuitable, as described in Problem
Description above.  Pre-Juno it was possible to configure use of an
out-of-tree VIF driver (with the virt_driver setting), but this was
deprecated and has now been removed.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

A compute host can guard against IP address spoofing (by a VM) on a
VIF_TYPE_TAP interface by installing iptables rules that require each
packet from a VM to have the expected source IP address.

If a VIF_TYPE_TAP interface is not plugged into a bridge, MAC address
spoofing by a VM has no impact.  If a VIF_TYPE_TAP interface _is_
plugged into a bridge, that bridge can implement similar protections
against MAC spoofing as for existing bridged VIF_TYPEs.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Unless the VIF_TYPE_TAP vif type is explicitly requested (e.g. by a
Neutron/ML2 mechanism driver class), there is no possible performance
impact on a standard OpenStack system.

Other deployer impact
---------------------

The Nova extension proposed here will have no effect on existing or
newly deployed OpenStack systems, unless the VIF_TYPE_TAP vif type
is explicitly requested somewhere (e.g. by a Neutron/ML2 mechanism
driver class).

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  neil-jerram

Other contributors:
  lukasaoz
  cliljenstolpe

Work Items
----------

The changes required for this spec have already been implemented by
us, based on the Icehouse release code, and fairly extensively
tested.

An up to date base is of course appropriate for this spec, so the
changes rebased onto the current proposed/juno branch can be seen at
the following URL:

* https://github.com/Metaswitch/calico-nova/commit/bde91e1afd32c4c033c527e078ec4e5c721302c5

Remaining work items are as follows:

* Implement unit and 3rd party CI tests as described below.
* Verify that proposed changes pass all existing tests (including code
  style), as well as new tests.
* Submit changes formally for review.
* Participate in resulting discussions, mark up and re-review
  processes.
* Repeat until done!


Dependencies
============

There are two related Neutron specs that I have proposed as part of
the Project Calico approach, and that build on the capability that
VIF_TYPE_TAP provides.

* https://blueprints.launchpad.net/neutron/+spec/dhcp-for-routed-ifs
  enhances the Neutron DHCP agent code to handle DHCP for routed TAP
  interfaces.

* https://blueprints.launchpad.net/neutron/+spec/calico-mechanism-driver
  provides a Neutron/ML2 mechanism driver that implements routed
  networking by using VIF_TYPE_TAP.

As already stated above, however, I expect the long term applicability
of VIF_TYPE_TAP to be wider than just for Project Calico.


Testing
=======

Within the OpenStack ecosystem, this change will be tested at
unit-test level, by adding a test case to
nova/tests/virt/libvirt/test_vif.py, that creates and verifies a
virtual interface with type VIF_TYPE_TAP.

(It will also be extensively tested at the system level by continuing
related development and testing at Project Calico
(http://www.projectcalico.org/), which uses VIF_TYPE_TAP, and such
work will generally be conducted and reported in public.

We understand, though, that this is not formally verifiable testing
within the OpenStack ecosystem; so it is mentioned here for
information only.)


Documentation Impact
====================

No documentation changes for Nova are anticipated.  VIF_TYPE_TAP will
be automatically enabled by a related Neutron/ML2 driver, where
appropriate.


References
==========

http://www.projectcalico.org/

https://github.com/Metaswitch/calico-nova

https://github.com/Metaswitch/calico-neutron
