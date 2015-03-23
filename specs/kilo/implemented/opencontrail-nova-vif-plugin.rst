==========================================
Nova Plugin for OpenContrail
==========================================

https://blueprints.launchpad.net/nova/+spec/opencontrail-nova-vif-driver-plugin

This blueprint is to add plugin for OpenContrail in existing Nova
VIF driver to support OpenContrail based network virtualization
for Openstack.

The OpenContrail APIs will cover following:

* Create Interface
* Delete Interface
* Get Interface Config


Problem description
===================

OpenContrail is open source network virtualization solution. It uses standards
based BGP L3VPN closed user groups to implement virtual networks.
The link http://OpenContrail.org/OpenContrail-architecture-documentation/
explains the architecture of OpenContrail plugin
OpenContrail plugin get merged to neutron on Juno timeframe.

OpenContrail is loading its VIF driver via openstack-config command
using option libvirt_vif_driver. In Juno this option is no longer supported
and same needs to be implemented under Nova VIF driver.

Use Cases
---------

Use Nova with Neutron + OpenContrail
For more details, please take a look this link
http://www.opencontrail.org/opencontrail-architecture-documentation/#section1_1

Project Priority
----------------

Not applicable


Proposed change
===============

Add OpenContrail APIs to handle the Creation/Deletion/Get of
interfaces in Nova VIF driver. There are no changes to the Nova common code.


Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

None.
There are no new API added to Nova. For above listed API all features
will be supported by the plugin.

Security impact
---------------
The communication channel to the backend is not secure.
We will support secure channel in the future.

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

None.

Developer impact
----------------

None.

Other Developers wont be effected by this change.

Implementation
==============

Model - VIF_TYPE_VROUTER

Following APIs will be implemented:

def get_config_vrouter(self, instance, vif, image_meta, inst_type, virt_type)

def plug_vrouter(self, instance, vif)

def unplug_vrouter(self, instance, vif)


Assignee(s)
-----------

Primary assignee:
  manishs

Other contributors:
  hajay

Work Items
----------

1. OpenContrail API implementation
2. OpenContrail mocks for unit-tests

Dependencies
============

None.

Testing
=======

Existing and new Nova unit tests will be used.

Existing and new tempest testing for Nova will be used.


Documentation Impact
====================

None.

The link below explains setup of OpenContrail using devstack.

http://pedrormarques.wordpress.com/2013/11/14/using-devstack-plus-OpenContrail/

References
==========

http://www.OpenContrail.org

https://github.com/Juniper/contrail-controller
