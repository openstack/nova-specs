..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
XenServer add support for neutron security group
================================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/support-neutron-security-group

This blueprint aims to support neutron security group.


Problem description
===================

XenServer as a compute driver lacks of neutron security group support. As we
know neutron's security group is implemented by using iptables and these
iptables rules are applied to Linux bridge of each VIF. However XenServer
compute driver doesn't create Linux bridges for VIFs when booting instance,
this makes neutron cannot apply iptables rules, so the firewall driver in
neutron can only be configured as NoopFirewallDriver at the moment.


Use Cases
----------

The most common use case is deploy an OpenStack environment which uses neutron
network and neutron security group and then booting an instance and check the
instance's network connectivity.


Proposed change
===============

The proposed change is to add Linux bridge for each VIF when booting a new
instance. This implementation is more or less the same as what libvirt does.
When booting an instance, xen nova compute driver will always create Linux
bridge qbr for each VIF and make qbr be connected to integration bridge
(e.g. br-int) in compute node. So the connection in compute node will looks
like:

|     VIF-1 -> LinuxBridge(qbr-1) ->
| VM                                OvsBridge(br-int) -> OvsBridge(br-eth)
|     VIF-2 -> LinuxBridge(qbr-2) ->

So, with the new added Linux bridge qbr, at neutron side, it can detect these
bridges qbr-XXX automatically and apply security group rules on each of the
VIF's Linux bridge qbr-XXX. The new added Linux bridge will be created all the
time as long as neutron is deployed, no new configuration settings added. This
change doesn't have any effect on nova network(i.e. no qbr-XXX Linux bridges
will be created if nova network is deployed). Then neutron security group will
work well when firewall driver is OVSHybridIptablesFirewallDriver in neutron's
conf file.

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

This implementation is to support neutron security group function with XenSerer
just like other hypervisor does. The main deployment changes if you want to use
this function are:

1. Deploy neutron in OpenStack environment
2. Change nova.conf, below configuration items should be specified::

    [DEFAULT]
    use_neutron = True
    firewall_driver = nova.virt.firewall.NoopFirewallDriver

3. Change neutron config file ml2_conf.ini::

    [securitygroup]
    firewall_driver = \
        neutron.agent.linux.iptables_firewall.OVSHybridIptablesFirewallDriver
    enable_security_group = true

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  huanxie

Other contributors:

Work Items
----------

1. Create Linux bridge for each vif when booting an instance
2. Create tap device between VIF and Linux bridge
3. Create veth pair between Linux bridge and Ovs bridge

Dependencies
============

This depends on a bug fix https://bugs.launchpad.net/neutron/+bug/1268955

Testing
=======

* Scenario test will be done manually or automatically with tempest.
  When it is implemented, we can deploy an environment using neutron VLAN
  network, enable neutron security group and set the correct firewall_driver
  in neutron's ml2_conf.ini file in compute node.

* XenServer Neutron CI will also be updated to test security groups though
  existing tempest tests. When the code patchset is ready, we will change some
  configurations as mentioned above and start full tempest to check the
  function and make sure there is no negative impact. The test report will be
  accessible publicly.

Documentation Impact
====================

None

References
==========

None

History
=======

None
