..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
API Consistency Cleanup
=======================

https://blueprints.launchpad.net/nova/+spec/api-consistency-cleanup

This blueprint proposes some of the cleanups in API for consistency
and better usage.

Problem description
===================
Currently, there are lot of inconsistency and loose validation in APIs.
Those inconsistencies are because of v2 API compatibility.

Because of loose validation for request body and query param, APIs ignore
the unknown and invalid inputs silently. This gives the impressions to user
that, requested unknown or invalid inputs are valid and taken care by Nova.
But Nova ignore all unknown or invalid inputs at API layer itself without
any warning to users.

server representation is not consistent among all APIs which return the
server info in response body.
GET, PUT, REBUILD /servers APIs return the server representation (with all
server attributes). But PUT and REBUILD /servers response does not
match with GET /servers API.

These are 2 examples of API inconsistency and there might be more such example
which are described in Proposed section.

Use Cases
---------
As an API consumer, I would like to use Nova API in more consistent way and
with strong validation for better usage.

As a Developer, I would like to provide and maintain better/clean/consistent
APIs.

There are maintenance benefits for client side code for parsing the API
response. For developers, maintenance can be easy only if we are able to
bump the minimum microversion in future.

Proposed change
===============
Add a new microversion to the APIs to cleanup multiple issues and
inconsistency.

Proposal is to do all the mentioned cleanup in single microverison.

Cleanup List:

#. 400 for unknown param for query param and for request body.

   Currently unknown param in server query param or in many other APIs request
   body are ignored silently. This leads to lot of inconsistency,
   one good example of this is ``--deleted`` and ``--status DELETED`` query for
   ``nova --list``.

   If you are non-admin then, filter ``--deleted`` and ``--status deleted``
   behave as 200 and 403 respectively. Both are same filter from end user
   point of view but due to our implementation we return different behavior.

   * ``nova list --deleted``:
     200 and it is silenlty ignored due to additionalProperty=True and for
     backward compatibility API accept and ignore the invalid filters.
     ``--deleted`` is invalid filter for non-admin

   * ``nova list --status DELETED`` :
     403. ``--status`` is valid filter for non-admin so API does not ignore
     this.

   We have explicit check for status=DELETED request and if requester
   is non-admin then, 403.
   Details discussion [1]_

   We can fix that by making ``additionalProperties: False`` for query param
   and request body of all the APIs where ``additionalProperties`` is True.
   For Example [2]_ and [3]_

   APIs need modification:
   https://github.com/openstack/nova/search?p=1&q=additionalProperties%3A+True&unscoped_q=additionalProperties%3A+True

#. Making server representation always consistent among all APIs
   returning the complete server representation.

   GET, PUT, REBUILD /servers APIs return the complete server representation
   (with all server attributes). But PUT and REBUILD /servers response does not
   match with GET /servers API.

   Difference between server representation in PUT, REBUILD from GET might
   be with historic reason that PUT and REBUILD only returning the fields
   in the response that could be taken on the request which modify the server,
   but over time we have started returning more fields to the response to make
   it consistent with GET response. That way only newly added fields in GET
   response started return in PUT, REBUILD also but old fields were missed.
   It end up, not keeping the original intent of PUT, REBUILD response and not
   completely consistent with  GET response.

   There are many field which are only returned in GET API but not in PUT or
   REBUILD.
   Response difference which is attributes added as extensions:

   * OS-EXT-AZ:availability_zone
   * OS-EXT-SRV-ATTR:host
   * OS-EXT-SRV-ATTR:hostname
   * OS-EXT-SRV-ATTR:hypervisor_hostname
   * OS-EXT-SRV-ATTR:instance_name
   * OS-EXT-SRV-ATTR:kernel_id
   * OS-EXT-SRV-ATTR:launch_index
   * OS-EXT-SRV-ATTR:ramdisk_id
   * OS-EXT-SRV-ATTR:reservation_id
   * OS-EXT-SRV-ATTR:root_device_name
   * OS-EXT-SRV-ATTR:user_data
   * OS-EXT-STS:power_state
   * OS-EXT-STS:task_state
   * OS-EXT-STS:vm_state
   * OS-SRV-USG:launched_at
   * OS-SRV-USG:terminated_at
   * os-extended-volumes:volumes_attached

   APIs need modification:

   * PUT /servers
   * POST /servers/{server_id}/action {rebuild}

#. Change the default return value of ``swap`` field from the empty string
   to 0 (integer) in flavor APIs.

   Currently while creating a flavor, if you don't set the optional ``swap``
   property, the value of the ``swap`` property in the flavor API's response
   will return as an empty string.
   Bug: https://bugs.launchpad.net/nova/+bug/1815476
   While processing this empty string on CLI side, it is shown as blank
   which is confusing and not consistent with other fields for example,
   "OS-FLV-EXT-DATA:ephemeral".
   Flavor representation in server API response has the ``swap`` default
   value as 0.
   Proposal is to make it consistant and return the ``swap`` default value
   as 0 (integer) in below APIs:

   * POST /flavors
   * GET /flavors/detail
   * GET /flavors/{flavor_id}
   * PUT /flavors/{flavor_id}

#. Return ``servers`` field always in the response of GET
   hypervisors API even there are no servers on hypervisor

   Currently, if there are no servers on requested hypervisors then,
   ``servers`` field is omitted from API response. This is not
   consistent response, ideally all fields should be present in
   response even with the empty value.
   Proposal is to return the ``servers`` field always in response
   of below APIs. ``servers`` field will be an empty list if there are
   no servers.

   * GET /os-hypervisors?with_servers=True
   * GET /os-hypervisors/detail?with_servers=True
   * GET /os-hypervisors/{hypervisor_id}?with_servers=True

Alternatives
------------
We leave APIs as it is and use it in same way they are currently or
we can choose the set of issues from above list to fix as single go.

Below cleanup already filtered out from this proposal:

#. Remove extensions (OS-) prefix from request and response field.
#. Fix  inconsistent/incorrect response codes

Data model impact
-----------------
None

REST API impact
---------------
This proposal is to fix the multiple issues in APIs. I am listing
the REST API impact of each issue in same order as they are listed above.

#. 400 for unknown param for query param and for request body.

   APIs which allow unknown request and query param and ignore silently
   wil be changed to return 400.
   Below are the APIs which has ``additionalProperties: True`` and will
   be modified to ``additionalProperties: False``:
   https://github.com/openstack/nova/search?p=1&q=additionalProperties%3A+True&unscoped_q=additionalProperties%3A+True

#. Making server representation always consistent among all APIs

   ``PUT /servers/{server_id}`` and
   ``POST /servers/{server_id}/action {rebuild}`` API response
   will be modified to add all the missing fields which are return by
   ``GET /servers/{server_id}``.

   NOTE: new fields will be added with same name they are present in GET
   /servers API response (means with ``OS-`` prefix).

#. Change the default return value of ``swap`` field from the empty string
   to 0 (integer) in flavor APIs.

   Below APIs response will be changed to return the ``swap`` default value
   as 0 (integer):

   * POST /flavors
   * GET /flavors/detail
   * GET /flavors/{flavor_id}
   * PUT /flavors/{flavor_id}

#. Return ``servers`` field always in the response of GET
   hypervisors API even there are no servers on hypervisor

   Below APIs response will be changed to return the ``servers``
   field always in response body. ``servers`` field will be an
   empty list if there are no servers:

   * GET /os-hypervisors?with_servers=True
   * GET /os-hypervisors/detail?with_servers=True
   * GET /os-hypervisors/{hypervisor_id}?with_servers=True

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
The python novaclient and openstack-client will be updated.

Performance Impact
------------------
None

Other deployer impact
---------------------
None

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
  Ghanshyam Mann

Work Items
----------
* Single microversion change on Nova API
* Add tests for changes
* python client (python-novaclient and  python-openstackclient) change

Dependencies
============
None

Testing
=======
* Add related unit test.
* Add related functional tests.
* Response change schema test in Tempest

Documentation Impact
====================
Modify the api-ref to reflect the API change.

References
==========
* Train PTG agreement: http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005824.html

* https://etherpad.openstack.org/p/nova-api-cleanup
  Nova API cleanup list Etherpad

.. [1] http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2018-07-10.log.html#t2018-07-10T14:14:18
.. [2] https://github.com/openstack/nova/blob/c5a80f4843d1f1a5289e0a3f8dbb4921b6fa44bb/nova/api/openstack/compute/schemas/servers.py#L602
.. [3] https://github.com/openstack/nova/blob/c6218428e9b29a2c52808ec7d27b4b21aadc0299/nova/api/openstack/compute/schemas/agents.py#L93

History
=======
.. list-table:: Revisions
      :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced

