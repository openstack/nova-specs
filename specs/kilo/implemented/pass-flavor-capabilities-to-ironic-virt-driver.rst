..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Pass on the capabilities in the flavor to the ironic
=====================================================

https://blueprints.launchpad.net/nova/+spec/pass-flavor-capabilities-to-ironic-virt-driver

Today nova doesn't pass on the `capabilities` defined in `extra-spec`
key of the flavor. The ironic needs to be aware of the requested
capability in the flavor.

Problem description
===================

Today nova doesn't pass on the `capabilities` defined in `extra-spec`
key of the flavor. Today Nova is able to read the capabilities
defined in the ironic node's properties field and select the node
using the ComputeCapabilities Filter. Now, the ironic needs to be aware
of the requested capability in the flavor so that it can take specific
actions as per the request in the flavor once the node has been scheduled
by Nova.

Use Cases
----------

The ironic can use it for following:

1. Prepare the node in the desired state before deploy.

2. The same can be used during decommisioning the node for unwinding to its
   original state.

Example: say a capability as, `power_optimized=True` as given in
flavor-key. The ironic has node.properties updated with capability as
`power_optimzied=True`. The node is selected via
ComputeCapabilities Filter. Now, if the node's instance_info is updated
by nova as `power_optimzied=True`, the ironic driver can prepare the
node in desired power state.
This is applicable for all the hardware capabilities which requires
some action from the driver as per the requested capability in the
flavor extra-spec key.

Project Priority
-----------------

None.

Proposed change
===============

The proposal is to update the instance_info field of the node object with
the capabilities defined in the flavor extra-spec.

Alternatives
------------

Ironic can in fact look this information up by calling the Nova API. However,
that would require Ironic to have sufficient permissions to see the flavor,
and would add a Keystone round trip for Ironic to fetch an authentication
token. Nova already passes a lot of meta data through in a boot request, so
avoiding the extra round trip seems worthwhile.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

This change takes immediate effect once the ironic is supported for
hardware capabilities which is a work-in-progress for kilo in ironic.

Developer impact
----------------

None.

Implementation
==============

See Work Items below.

Assignee(s)
-----------

Primary assignee:
  agarwalnisha1980

Work Items
----------

* Require changes in nova/virt/ironic/patcher.py to update the instance_info
  field with the flavor capabilities.

Dependencies
============

None.

Testing
=======

Unit tests will be added.

Documentation Impact
====================

This will be documented under ironic.

References
==========

Exposing Hardware capabilities:
https://review.openstack.org/#/c/131272/

https://etherpad.openstack.org/p/kilo-ironic-exposing-different-capabilities

For supporting multiple values with `capabilities`:
https://review.openstack.org/133534
