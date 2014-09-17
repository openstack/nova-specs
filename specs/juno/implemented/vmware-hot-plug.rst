..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
VMware: support for vif hotplug
===============================

https://blueprints.launchpad.net/nova/+spec/vmware-hot-plug

Support for hotpluging virtual network cards into instances.

Problem description
===================

Support for hotpluging virtual network cards into instances has already
been implemented in the libvirt driver:
https://blueprints.launchpad.net/nova/+spec/network-adapter-hotplug

The plan is to add the same support into the VMware driver.

Proposed change
===============

Implement the methods attach_interface and detach_interface in the VMware
driver.

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

A user will now be able to add or remove interfaces from an instance that is
run by the VMware driver. The new nic will be added ore removed when the action
takes place and does not require rebooting the guest.

Performance Impact
------------------

None

Other deployer impact
---------------------

Feature parity.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  Gary Kotton<gkotton@vmware.com>

Work Items
----------

Code was posted in Icehouse - https://review.openstack.org/#/c/59365/

Dependencies
============

Common VIF parameters were added - https://review.openstack.org/#/c/72292/

Testing
=======

Unit tests and 3rd party testing. Note that the feature is only supported with
Neutron at the moment.

Documentation Impact
====================

Remove limitation that this is only supported with libvirt.

References
==========

None
