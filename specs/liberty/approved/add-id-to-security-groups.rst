..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================================
Add 'uuid' field into security groups for each server show from API layer
=========================================================================

https://blueprints.launchpad.net/nova/+spec/add-id-to-security-groups-for-server-show

This feature will add "uuid" field into security-groups section together
with the "name" of each security-groups for nova show server action from
nova API layer.


Problem description
===================

Currently, nova-network is NOT allowing 2 security-groups with the same name,
while neutron allows this. Nova show <servers-id> API only return the "name"
of each security-groups, this leads to confusions to the users, especially
for the scenario of neutron using more than 2 security-groups with the same
name. Neutron distinguishes security-groups by uuid, while there are no
"uuid" information returned by "nova show <servers-id>".

Use Cases
---------

As a cloud administrator, I need to know the details about security-groups of
each server connect to, especially when using neutron, I need to distinguish
the security-groups with the same name when calling to the API servers.show().

Project Priority
----------------

None

Proposed change
===============

For nova-network, add 'uuid' column to DB class SecurityGroup, SecurityGroup
object will generate and save the 'uuid' if not exist.

For nova API, change the existing os-security-groups API extension
_extend_servers function with microversion, such that version on the API GET
servers info, could add the security-groups 'uuid' information into servers\
.show response data.

Alternatives
------------

From nova CLI, once you get the server id, you could get the security-groups
details of this server via nova list-secgroup <server-id> API request, this
could be a workaround for nova CLI, but this could not change the fact that
response data from nova show <server-id> does not contain the security-groups
uuid information.

Data model impact
-----------------

nova-network will add an 'uuid' column for security groups DB class, the
security group object will generate and save the uuid when be created. Once
thats in place, we can return uuids for each security group via the API.

Once everything has been updated in the existing DB, we could add a unique
and not null constraint in the next release,

REST API impact
---------------

The proposed change just updates the GET response data in the servers.show
API to include the security-groups 'uuid' field. The details will be changed
in the os-security-groups API extension.

If a deployer is using the required minimum version of the API to get the
'uuid' data, they can begin to use it, otherwise they won't see any change.

* Example use case:

Request:

GET --header "X-OpenStack-Nova-API-Version: 2.xx"  v2/{tenant-id}/servers/\
{server-id}

Response:

::

   {"server":
      {
         ...
         "security_groups": [{"name": "default"}, {"uuid": "e20ccd4b-c316-\
               4df9-8e4c-f003b942a90d"}]
         ...
      }
   }

* There should not be any impacts to policy.json files for this change.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

* The python-novaclient server show command could be updated to show the
  'uuid' status in it's output when the 'uuid' field is in the response data,
  if NOT, the client will show 'name' only as before.

Performance Impact
------------------

None

Other deployer impact
---------------------

None;

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Park heijlong <heijlong@linux.vnet.ibm.com>

Work Items
----------

* Add 'uuid' column to db class SecurityGroup, generate and save the 'uuid'
  if not exist during the security groups creation.

* Add a new microversion and change nova/api/openstack/compute/plugins/v3\
  /security_groups.py to add the 'uuid' attribute to the response data,
  currently, uuid will not replace name/id, so that both 'name' and 'uuid'
  will be in resonse data as details above.


Dependencies
============

None


Testing
=======

* Unit tests and possibly API samples functional tests in the nova tree.
* There are currently not any test cases for verifying the 'uuid' in Tempest.
  We could add support for verifying 'uuid' test case in Tempest with
  microversion support.


Documentation Impact
====================

The nova/api/openstack/rest_api_version_history.rst document will be updated.


References
==========

* Originally reported as a bug: https://bugs.launchpad.net/nova/+bug/1438338

* Old ML thread for the bug:

http://lists.openstack.org/pipermail/openstack-dev/2015-May/064344.html

* add-id-to-security-groups BP:

https://blueprints.launchpad.net/nova/+spec/add-id-to-security-groups-for-server-show
