..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
VMware: Expand Support for Opaque Networks
==========================================

https://blueprints.launchpad.net/nova/+spec/vmware-expand-opaque-support

An opaque network was introduced in the vSphere API in version 5.5. This is
a network that is managed by a control plane outside of vSphere. The identifier
and name of this network is made known to vSphere so that a host and virtual
machine ethernet device can be connected to them.

The initial code was added to support the NSX-MH (multi hypervisor) Neutron
plugin. This was in commit 2d7520264a4610068630d7664eeff70fb5e8c681. That
support would require the configuration of a global integration bridge and
ensuring that the network was connected to that bridge. This approach is
similar to the way in which this is implemented in the libvirt VIF driver.

In the Liberty cycle, a new plugin was added to the openstack/vmware-nsx
repository, this is called NSXv3. This is to support a new NSX backend. This
is a multi-hypervisor plugin. The support for libvirt, Xen etc. already exists.

This spec will deal with the compute integration for the VMware VC driver.

Problem description
===================

This spec will deal with the configuration of the Opaque network for the NSXv3
Neutron driver.

Use Cases
----------

This is required for the NSXv3 plugin. Without it Nova will be unable to attach
a ethernet device to a virtual machine.

Proposed change
===============

The change is self contained within the VMware driver code and just related to
how the ethernet device backing is configured. This is only when the Neutron
virtual port is of the type 'ovs'. The NSXv3 plugin will ensure that the port
type is set to 'ovs'. The VC driver will need to treat this port type.

When the type is 'ovs' there are two different flows:

* If the configuration flag 'integration_bridge' is set. This is for the
  NSX-MH plugin. This requires that the backing type opaqueNetworkId be set
  as the 'integration_bridge'; the backing type opaqueNetworkType be set as
  'opaque'.

* If the flag is not set then this is the NSXv3 plugin. This requires that
  the backing value opaqueNetworkId be set as the neutron network UUID; the
  backing type opaqueNetworkType will have value 'nsx.LogicalSwitch'; and the
  backing externalId has the neutron port UUID.

.. note::

  * The help for the configuration option 'integration_bridge' will be updated
    to reflect the values for the different plugins.

  * A log warning will appear if the invalid VC version is used.

  * The above should be done regardless of this support.


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

The NSXv3 support will be greenfield.

The NSX-MH will be deprecated in favor of the NSXv3 plugin. As a result of
this we will set the default 'integration_bridge' value as None. This means
that a user running the existing NSX-MH will need to make sure that this value
is set. This is something that will be clearly documented.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  garyk

Work Items
----------

The implementation of the changes in Nova can be seen at:
https://review.openstack.org/#/c/165750/.


Dependencies
============

This code depends on the Neutron driver NSXv3 added in the Liberty cycle.
This code can be found at https://github.com/openstack/vmware-nsx/blob/master/vmware_nsx/plugins/nsx_v3/plugin.py

Testing
=======

The code is tested as part of the Neutron CI testing.


Documentation Impact
====================

We will need to make sure that the release notes are updated to explain the
configuration of CONF.vmware.integration_bridge config. As mentioned above
that is only relevant to the NSX-MH as the code will be changed to support
the NSXv3.


References
==========

* https://www.vmware.com/support/developer/converter-sdk/conv55_apireference/vim.OpaqueNetwork.html

* https://review.openstack.org/#/c/165750/


History
=======

None
