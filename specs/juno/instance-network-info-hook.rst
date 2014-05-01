..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Add hook for update_instance_cache_with_nw_info
===============================================

https://blueprints.launchpad.net/nova/+spec/instance-network-info-hook

A hook of the update_instance_cache_with_nw_info call will allow hooks access
to valuable network information as soon as it becomes available. This will be
useful for sending this data to scripts that can make informed tweaks to the
networking on hosts.

Problem description
===================

Right now there is no way to hook into the updating of network info.

Usecase:
* Deployer would be able to register a hook to send networking information
to a script that could make informed tweaks to networking on hosts. This
might include flows or QoS.


Proposed change
===============

Add a hook to the update_instance_cache_with_nw_info call to allow hooks
access to this information.

Alternatives
------------

This information is stored in the database, and could be accessed from there.
But, this would require giving access to the database to outside applications
and could potentitally increase load on the database.

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

The new code itself will not introduce any performance impact, but due to the
nature of hooks, any deployer introduced hooks could have a performance impact.
It will be up to the deployer to test their hooks for performance impact.

Other deployer impact
---------------------

This change will introduce a new location for hooks. It will not immediately
effect a deployment, as new hooks would need to be introduced that would
take advantage of this new hook location.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  andrew-melton

Other contributors:
  None

Work Items
----------

* Register a new hook for update_instance_cache_with_nw_info

Dependencies
============

None

Testing
=======

Unit testing to verify that you can register a hook for
update_instance_cache_with_nw_info should be sufficient. The functional
testing of the actual hooks should be left to the deployer.


Documentation Impact
====================

If there is a list of hook locations, it will need to be updated to include
this new location.

References
==========

* Dev docs on nova hooks: http://docs.openstack.org/developer/nova/devref/hooks.html

