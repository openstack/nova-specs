..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
Server Group Quotas
===================

https://blueprints.launchpad.net/nova/+spec/server-group-quotas

Add quota values to constrain the number and size of server groups a
users can create.

Problem description
===================

Server groups can be used to control the affinity and anti-affinity scheduling
policy for a group of servers (instances).  Whilst this is a useful mechanism
for users such scheduling decisions need to be balanced by a deployers
requirements to make effective use of the available capacity.

For example it may be considered reasonable for a user to be able to request
anti-affinity between a set of 10 servers to support a particular
availability schematic.   However a user creating anti-affinity between 100
servers would be in direct conflict with a stacking policy intended to
avoid fragmentation of the overall cloud capacity.

Unlimited anti-affinity could allow a user to derive information about the
overall size of the cloud, which is generally considered private information
of the cloud provider.

Unlimited server groups could in themselves be used as a DoS attack against
systems not protected by an API rate limiter, a user creating groups until
the DB fills up.

Proposed change
===============

Two new quota values will be introduced to limit the number of sever groups
and the number of servers in a server group.

These will follow the existing pattern for quotas (for example security
groups and rules per security group) in that:

* They are defined by config values, which also include the default value

* They can be defined per project or per user within a project

* A value of -1 for either quota will be treated as unlimited.

* Defaults can be set via the quota groups API

* Values may be changed at any time but will only take effect at the next
  server group or server create.   Reducing the quota will not affect any
  existing groups, but new servers will not be allowed into groups
  that have become over quota.

The new options will be defined as follows:

cfg.IntOpt('quota_server_groups',
           default=10,
           help='Number of server groups per project')

cfg.IntOpt('quota_server_group_members',
           default=10,
           help='Number of servers per server group')


Alternatives
------------

None.

Data model impact
-----------------

None.  The quota values will be simply checked at the point when a server
group is created or a server is created.

REST API impact
---------------

Because this change introduces additional fields to existing API methods
it will be controlled in V2 by the presence of a new api extension.

Name = "ServerGroupQuotas"
Alias = "os-server-group-quotas"


Change in the response when getting the quotas for a user/tenant.
* Method: GET
* Path: /os-quota-sets/{tenant_id}
* Resp: Normal Response Codes 200

JSON response

{
 "quota_set": {
  "cores": 20,
  "fixed_ips": -1,
  "floating_ips": 10,
  "id": "fake_tenant",
  "injected_file_content_bytes": 10240,
  "injected_file_path_bytes": 255,
  "injected_files": 5,
  "instances": 10,
  "key_pairs": 100,
  "metadata_items": 128,
  "ram": 51200,
  "security_group_rules": 20,
  "security_groups": 10,
  "server_groups": 10,
  "server_group_members": 10,

 }

}

Change in the response when getting the default quotas.
* Method: GET
* Path: /os-quota-sets/defaults
* Resp: Normal Response Codes 200

JSON response

{
 "quota_set": {
  "cores": 20,
  "fixed_ips": -1,
  "floating_ips": 10,
  "id": "fake_tenant",
  "injected_file_content_bytes": 10240,
  "injected_file_path_bytes": 255,
  "injected_files": 5,
  "instances": 10,
  "key_pairs": 100,
  "metadata_items": 128,
  "ram": 51200,
  "security_group_rules": 20,
  "security_groups": 10,
  "server_groups": 10,
  "server_group_members": 10,

 }

}

Change in the request when updating the quotas for a user/tenant.
* Method: POST
* Path: /os-quota-sets/{tenant_id}/{user_id}
* Resp: Normal Response Codes 200

JSON response:

{
 "quota_set": {
  "force": "True",
  "instances": 9,
  "server_groups": 10,
  "server_group_members": 10,

 }

}

JSON Schema:

common_quota = {
    'type': ['integer', 'string'],
    'pattern': '^-?[0-9]+$',
    'minimum': -1

}

update = {
    'properties': {
        'type': 'object',
         'quota_set': {
            'properties': {
                'instances': common_quota,
                'cores': common_quota,
                'ram': common_quota,
                'floating_ips': common_quota,
                'fixed_ips': common_quota,
                'metadata_items': common_quota,
                'key_pairs': common_quota,
                'security_groups': common_quota,
                'security_group_rules': common_quota,
                'server_groups': common_quota,
                'server_group_members': common_quota,
                'force': parameter_types.boolean,

            },
            'additionalProperties': False,

        },

    },
    'required': ['quota_set'],
    'additionalProperties': False,

}

Change in the response of the of limits request:


JSON response:

{
    "limits": {
        "rate": [

        ],
    "absolute": {
        "maxServerMeta": 128,
        "maxPersonality": 5,
        "maxImageMeta": 128,
        "maxPersonalitySize": 10240,
        "maxSecurityGroupRules": 20,
        "maxTotalKeypairs": 100,
        "totalRAMUsed": 2048,
        "totalInstancesUsed": 4,
        "maxSecurityGroups": 10,
        "totalFloatingIpsUsed": 0,
        "maxTotalCores": 20,
        "totalSecurityGroupsUsed": 1,
        "maxTotalFloatingIps": 10,
        "maxTotalInstances": 10,
        "totalCoresUsed": 4,
        "maxTotalRAMSize": 51200,
        "maxServerGroups": 10,
        "totalServerGroupsUsed": 2,
        "maxServersPerServerGroups": 10,

    }

  }

}

Change in the response of ServerGroup API:

Create can now return 413 "Quota Exceeded for server groups"



Security impact
---------------

Improves the security of systems with the Server Groups API enabled
by limiting the resources each project can consume.

Notifications impact
--------------------

None.

Other end user impact
---------------------

python-novaclient will be updated to support the new quota values.

If the new values are not returned by the API (i.e the system has not yet
been updated to include this change) then the client will return a value
of -1 (unlimited)

Performance Impact
------------------

None - the quota validation will be a minor additional step in the  API.

Other deployer impact
---------------------

Quotas will only be validated for new requests, so it is possible (as with
any default quota change) that some existing projects may already be over
quota.  No existing groups will be affected, but users will be unable to
create new groups and/or add servers to groups until they drop below their
quota allowances.

Deployers will have to consider what default quota values they want to
configure, and if they want to configure any project specific quotas.

The new quota checks will only be effective and vakues reported via the API
when the new extension is loaded.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  philip-day

Work Items
----------

The change will be submitted as a single patch set.


Dependencies
============

None


Testing
=======

Existing Tempest quota tests will be extended to cover the new values.


Documentation Impact
====================

The new values will need to be included in the documentation.


References
==========

None.
