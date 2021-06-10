..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Rework security group for server details
========================================

https://blueprints.launchpad.net/nova/+spec/rework-security-group-retrieving

Problem description
===================

Generating nova server details could be significantly slowed down if neutron
is used. The cause could be that retrieving security group id/name
requires extra calls to neutron API and number of calls are linear to number
of ports associated with instances divided by 100.

By removing calling to neutron API, it shows a 30% improvement for server
details. Nova already has an `info_cache` which saves port name, so we can
take advantage of this and saves security group name as well. By doing this,
we should be able to boost API performance.

Use Cases
---------

Speed up listing of server details and improving API responsiveness.

Proposed change
===============

Add a new mircoversion and allow user to retrieve server detail list without
security group. User will still be able to query security group info through
neutron API, for example
`openstack port list --server ${VM_UUID} -c security_group_ids`

Cache security group names in `info_cache` for each bounded port, so when
directly retrieving security group from database without calling neutron API.
This will hopefully speed up server detail query given that enough number of
`info_cache` is populated with security group names. Also note that, update
bounded port will also cause neutron server to callback nova-api and there
update `info_cache` items.

Alternatives
------------

None

Data model impact
-----------------

`info_cache` object will have a new property named `security_group`.

REST API impact
---------------

Add a microversion to remove security groups from related APIS when using
neutron network plugin. In the meantime, also remove proxy APIs to query
security groups, user should be able to use neutron API instead.

Remove security groups from following APIs

* ``GET /servers/details``
* ``GET /servers/{server_uuid}``
* ``PUT /servers/{server_uuid}``
* ``POST /servers/{server_id}/action where action is rebuild``

Following APIs will be deprecated,

* ``GET /servers/{server_id}/os-security-groups``

It will still be possible to specify a security group when creating an
instance. This behavior is not modified.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

With the new microversion, user will have to query neutorn API for
security groups

Performance Impact
------------------

Querying server details will be accelerated.

Other deployer impact
---------------------

None

nova APIs layer will take care of cache miss and will still query neutron for
security group.

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
  ushen

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  Ghanshyam

Feature liaison:
  Balazs Gibizer

Work Items
----------

* API change to remove the security groups info for new microversion
* Cache security group name in `info_cache`
* Unit and Functional tests
* python-novaclient and osc change
    * add new microversion

Dependencies
============

None

Testing
=======

Adding API functional sample and unit tests to verify security
group is properly returned.

Documentation Impact
====================

Add a documentation and explain the new microversion as well as server
details may return stale data when quering.

References
==========

Discussion on IRC about the need for a new API microversion:
https://etherpad.opendev.org/p/nova-xena-ptg

History
=======

