..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Policy Default Refresh
=======================

https://blueprints.launchpad.net/nova/+spec/policy-defaults-refresh

Ideally most operators should be able to run without modifying policy, as
such we need to have richer defaults.

When modifying policy, the defaults in policy should be easy to understand
and allow operators to easily create additional custom roles.

Problem description
===================

The default policy is not good enough, and hard to understand.

Most APIs default to use one these two policy rules:

* admin_only
* admin_or_owner

Firstly "admin_only" is used for the global admin that is able to make almost
any change to Nova, and see all details of the Nova system.
The rule actually passes for any user with an admin role, it doesn't matter
which project is used, any user with the ``admin`` role gets this global
access.

Secondly "admin_or_owner" sounds like it checks if the user is a member of a
project. However, for most APIs we use the default target which means this
rule will pass for any authenticated user. The database layer has a check
for the project id (with project_only kwargs) that ensures only users in the
correct project can access instances in that project. For example, this
database check means it is impossible to have a custom role that allows a
user to perform live-migration of a server in a different project to their
token, without the user being given the global admin role. In addition,
should a user have any role in a project, using the default policy, that user
is able to access Nova and start instances in that project (subject to any
quota limits on that project).

Thirdly if you want a "reader" role, several APIs share a single policy rule
for read and write actions, i.e. we don't have the granularity for such a role
to be added.

Keystone comes with member, admin and reader roles by default. We should
use these default roles:
https://specs.openstack.org/openstack/keystone-specs/specs/keystone/rocky/define-default-roles.html

In addition, we can use the new "system scope" concept to define
which users are global administrators:
https://specs.openstack.org/openstack/keystone-specs/specs/keystone/queens/system-scope.html

Use Cases
---------

The following user roles should be supported by the default configuration:

* System Scoped Administrator (live-migrate, disable services, etc)
* Project Scoped Member (create servers, delete servers)
* System Scoped Reader (list hosts, list all servers)
* Project Scoped Reader (list servers)

In introducing the above new default permissions, we must ensure:

* Operators using default policy are given at least one cycle to add
  additional roles to users (likely via implied roles)
* Operators with over-ridden policy are given at least one cycle to
  understand how the new defaults may or may not help them

Proposed change
===============

We will support the four new roles described in the use cases section
above.

The change will be made in the following stages:

#. Add tests to each API endpoint. Unit and Functional test of each APIs
   behavior before any changes are made.

#. Ensure all context.can calls specify a target, then make target a required
   parameter and remove the default target. For example project_id.
   Currently we use context.project_id in many place which needs to be
   replaced with actual target project_id. For example, for a server action,
   we need to use the project_id of the server, not the project_id of the
   context which made the request.

#. Change DB check from "role:admin" to "scope:system" if enforce_scope is
   True. We can set system_scope on context for DB check.

#. Refresh each API endpoint picking from: SYSTEM_ADMIN, SYSTEM_READER,
   PROJECT_MEMBER_OR_SYSTEM_ADMIN, PROJECT_READER_OR_SYSTEM_READER
   (and a few other ones for things like keypairs), adding extra
   granularity if needed. Maintain the old check_str working for
   existing users.

#. In a future release, enforce_scope will be enforced to be True. The
   legacy admin_or_owner style checking will be removed. At this point,
   operators will have been given time to ensure all their users work
   with the new policy defaults, and we will be happy we have enough
   testing in place to not regress the checks we have in policy.

Scope
-----

Each policy rules will be covered with appropriate oslo.policy's "scope_types",
'system' and 'project' in nova case.

For example GET /os-services will be scoped as 'system' so that only users
with system-scoped tokens will be authorized to access this API.

POST '/servers/{server_id}/action (lock) will be scoped as
['system', 'project'] which means system scope token as well as project
scope token can lock the servers.

PoC: https://review.openstack.org/#/c/645452/

We need to allow for operators to migrate off of the old policy enforcement
system in a somewhat graceful way. The ``enforce_scope`` config option helps
us with that by giving operators a toggle to enforce scope checking when
they're ready and they've audited their users and assignments.

``enforce_scope`` config option default value is False which means if
token scope does not matches, only a warning is logged. This feature can
be enabled via config option ``nova.conf [oslo_policy] enforce_scope=True``

Note: the Nova use of user_id and project_id are orthogonal, when checking the
user_id we have no concept of project, and when checking project_id we care
little about the user_id.

Keystone already support implied roles means assignment of one role implies
the assignment of another. New defaults roles `reader`, `member` also has
been added in bootstrap. If the bootstrap process is re-run, and a
`reader`, `member`, or `admin` role already exists, a role implication
chain will be created: `admin` implies `member` implies `reader`.

It means if we make something like SYSTEM_READER_OR_PROJECT_READER it implies
the PROJECT_MEMBER and SYSTEM_ADMIN also get access.

New Roles and check_str::

  SYSTEM_ADMIN = 'rule:admin_api and system_scope:all'
  SYSTEM_READER = 'role:reader and system_scope:all'
  PROJECT_MEMBER = 'role:member and project_id:%(project_id)s'
  PROJECT_READER = 'role:reader and project_id:%(project_id)s'
  PROJECT_MEMBER_OR_SYSTEM_ADMIN = PROJECT_MEMBER + 'or' + SYSTEM_ADMIN
  PROJECT_READER_OR_SYSTEM_READER = PROJECT_READER + 'or' + SYSTEM_READER

Below is the mapping of new roles and scope_types with legacy roles::

 Legacy Rule        |    New Rules                     | Operation |scope_type|
 -------------------+----------------------------------+-----------+-----------
                    |-> SYSTEM_ADMIN                   | Global    | [system]
 RULE_ADMIN_API     |                                    Write
                    |-> SYSTEM_READER                  | Global    | [system]
                    |                                  | Read      |

                    |-> PROJECT_MEMBER_OR_SYSTEM_ADMIN | Project   | [system,
 RULE_ADMIN_OR_OWNER|                                  | Write     |  project]
                    |-> PROJECT_READER_OR_SYSTEM_READER| Project   | [system,
                                                       | Read      |  project]

PoC: https://review.opendev.org/#/c/645452

Role
----

Once the scope has checked, we need to ensure what role the user has for their
given scope, and if that matches what the operator has allowed.

We should move the following reader, member, admin pattern:

The reader role is the least privileged, can generally only do non-destructive
GET API calls.

The member role maps to the current default level of privilege.

The admin role maps to the current admin role. Note this means live-migration
is project scoped and admin. Although if you specify a host, you would need
to have system scope to use that parameter.

It is important to consider the scope_type of the policy when defining the
appropriate default roles.

Because config option [oslo_policy].enforce_scope is false by default which
means scope_type is not enabled by default so it might be security leak if new
given roles can access the API out of their scope.
For example: GET /os-services will be given as 'reader' role and
scope_type=['system'] so check_str will be kept as 'role:reader and
system_scope:all' where system_scope:all is special check so that token of
reader role and project scope cannot access this API. Once nova default the
[oslo_policy].enforce_scope to True then, system_scope:all can be removed
from check_str (this only applies to APIs that include the ``system`` as
one of the scope_type).

PoC: https://review.openstack.org/#/c/648480/

Until removed the DB level check for the admin role will be loosened also
allow access for any system scoped token.

NOTE: At the same time, we will update all policy checks to specify the
correct target's project_id. When there is no relevant project, we do not
specify a project_id at all (i.e. stop defaulting to
target={context.project_id}

Granular
--------

To implement the reader role, some of the APIs do not have a granular enough
policy. We will add additional policy checks for these APIs:

We will deprecate the old rule and add new granular rules.
For exmaple: ``os_compute_api:os-agents`` will be deprecated and
new rules will be added ``os_compute_api:os-agents:delete``,
``os_compute_api:os-agents:get``, ``os_compute_api:os-agents:create``,
``os_compute_api:os-agents:update``.

* 'os_compute_api:os-agents':

  * File: nova/policies/agents.py
  * APIs Operation it control:

    * POST /os-agents,
    * PUT /os-agents,
    * GET /os-agents,
    * DELETE /os-agents

* 'os_compute_api:os-attach-interfaces':

  * File: nova/policies/attach_interfaces.py
  * APIs Operation it control:

    * GET '/servers/{server_id}/os-interface'
    * GET '/servers/{server_id}/os-interface/{port_id}'
    * POST '/servers/{server_id}/os-interface',
    * DELETE '/servers/{server_id}/os-interface/{port_id}'

* 'os_compute_api:os-deferred-delete':

  * File: nova/policies/deferred_delete.py
  * APIs Operation it control:

    * POST '/servers/{server_id}/action (restore),
    * POST '/servers/{server_id}/action (forceDelete)'

* 'os_compute_api:os-hypervisors':

  * File: nova/policies/hypervisors.py
  * APIs Operation it control:

    * GET '/os-hypervisors',
    * GET '/os-hypervisors/details',
    * GET '/os-hypervisors/statistics',
    * GET '/os-hypervisors/{hypervisor_id}',
    * GET '/os-hypervisors/{hypervisor_id}/uptime',
    * GET '/os-hypervisors/{hypervisor_hostname_pattern}/search',
    * GET '/os-hypervisors/{hypervisor_hostname_pattern}/servers',

* 'os_compute_api:os-instance-actions':

  * File: nova/policies/instance_actions.py
  * APIs Operation it control:

    * GET '/servers/{server_id}/os-instance-actions',
    * GET '/servers/{server_id}/os-instance-actions/{request_id}'

* 'os_compute_api:os-instance-usage-audit-log':

  * File: nova/policies/instance_usage_audit_log.py
  * APIs Operation it control:

    * GET '/os-instance_usage_audit_log',
    * GET '/os-instance_usage_audit_log/{before_timestamp}'

* 'os_compute_api:os-remote-consoles':

  * File: nova/policies/remote_consoles.py
  * APIs Operation it control:

    * POST '/servers/{server_id}/action (os-getRDPConsole)',
    * POST '/servers/{server_id}/action (os-getSerialConsole)',
    * POST '/servers/{server_id}/action (os-getSPICEConsole)',
    * POST '/servers/{server_id}/action (os-getVNCConsole)',
    * POST '/servers/{server_id}/remote-consoles',

* 'os_compute_api:os-rescue':

  * File: nova/policies/rescue.py
  * APIs Operation it control:

    * POST '/servers/{server_id}/action (rescue)',
    * POST '/servers/{server_id}/action (rescue)'

* 'os_compute_api:os-security-groups':

  * File: nova/policies/security_groups.py
  * APIs Operation it control:

    * POST '/servers/{server_id}/action (addSecurityGroup)',
    * POST '/servers/{server_id}/action (removeSecurityGroup)'

* 'os_compute_api:os-server-password':

  * File: nova/policies/server_password.py
  * APIs Operation it control:

    * GET '/servers/{server_id}/os-server-password',
    * DELETE '/servers/{server_id}/os-server-password'

* 'os_compute_api:servers:show:host_status:

  * File: nova/policies/servers.py
  * APIs Operation it control:

    * GET '/servers/{server_id}',
    * GET '/servers/detail'

* 'network:attach_external_network':

  * File: nova/policies/ servers.py
  * APIs Operation it control:

    * POST  '/servers',
    * POST '/servers/{server_id}/os-interface'

* 'os_compute_api:os-services':

  * File: nova/policies/ services.py
  * APIs Operation it control:

    * PUT  '/os-services/enable',
    * PUT '/os-services/disable',
    * GET '/os-services',
    * PUT '/os-services/disable-log-reason',
    * PUT '/os-services/force-down',
    * PUT '/os-services/{service_id}',
    * PUT '/os-services/{service_id}'

Below policies have same issue but their APIs are deprecated so this proposal
would not change anything in these.

* 'os_compute_api:os-floating-ips-bulk'
* 'os_compute_api:os-fping'
* 'os_compute_api:os-hosts'
* 'os_compute_api:os-networks'
* 'os_compute_api:os-networks-associate'
* 'os_compute_api:os-security-group-default-rules'
* 'os_compute_api:os-baremetal-nodes'
* 'os_compute_api:os-fixed-ips'
* 'os_compute_api:os-floating-ip-dns'
* 'os_compute_api:os-floating-ips'
* 'os_compute_api:os-multinic'
* 'os_compute_api:os-tenant-networks'
* 'os_compute_api:os-volumes'

PoC: https://review.openstack.org/#/c/645427/

Backward Compatibility and Migration plan
-----------------------------------------

Old rules are maintained as deprecated rule with same defaults as today
so that existing deployement will keep working as it is.

For two cycle (this is big updates so I think we should give two cycle
transition period to operators), we need existing user permissions to
work alongside the new set of roles, so operators can migrate their
users to the new roles.

Note this means:

* Remove any project or user checks from the policy file defaults, as this
  is now done in code, without breaking user-id-based-policy-enforcement
* Things the reader is not allowed access in the future, but currently anyone
  with a role can access must get an explicit not reader role check
* System scope check failures only log a warning for this cycle
* etc...

This will be done by using the oslo.policy's deprecation methods. That way
we can allow the access with old check_str as well with new check_str with
appropriate warnings.

* Deprecation Plan:
  Because these policy updates are huge and almost effecting all the nova
  policies, We are defining the two cycle transition plan which used to be
  one cycle for policy and config option modification.

* Below warning can be seen by operator to migrate the old policies
  to new one:

  /opt/stack/nova/.tox/py27/local/lib/python2.7/site-packages/oslo_policy/
  policy.py:665: UserWarning: Policy "os_compute_api:os-services":
  "rule:admin_api" was deprecated in 19.0.0 in favor of "compute:services:
  disable":"rule:admin_api". Reason:
  Since Stein release, nova API policies are more granular and introducing
  new default roles with scope_type capabilities. These new changes improve
  the security level, manageability. New policies are more rich in term of
  handling access at system and project level with read, write roles. Nova
  APIs are consuming these new policies improvements and automatically
  migrate the old overridden policies. Old policies are silently going to
  be ignored in nova 21.0.0 (OpenStack U) release.
  . Either ensure your deployment is ready for the new default or
  copy/paste the deprecated policy into your policy file and maintain it
  manually.

Example: https://review.opendev.org/#/c/662971/

Alternatives
------------

We could do only one or two of the above steps, but seems more efficient
to fix these issues in one go.

Instead of deprecated rule, we can have a fallback mechanish of registering
the either the new or old policy defaults in the base based on
CONF.oslo_policy.enforce_scope.

Data model impact
-----------------

None

REST API impact
---------------

Existing users should be unaffected by these changes till the deprecated
policies are removed or enforce_scope is enabled.

Once enforcing scope, system scope users will need to learn how to request
system scoped tokens. But regular project scoped tokens remain the same for
the majority of users.

Operators should be able to create new roles with more restrictive permissions
in the near future.

Security impact
---------------

Easier to understand policy defaults will help keep the system secure.

Once the deprecated defaults are dropped, we will be able to have users with
a role in a project and not have any access to Nova (i.e. a swift only user).

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

None

Developer impact
----------------

New APIs must add policies that follow the new pattern.

Upgrade impact
--------------

The API policies name and defaults roles has been modified which
might effect the deployment if it use the default policy defined
in nova. If deployment overrides these policies then, they need to
start considering the new default policy rules.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmann

Other contributors:
  johnthetubaguy
  melwitt

Feature Liaison
---------------

Feature liaison:
  melwitt

Work Items
----------

* Improve policy rule unit tests
* Add policy functional tests for current behavior
* Add support for system scoped admin and project scoped member
* Loose the DB check for system scoped users, update functional tests
* Add System Reader and Project Reader, add additional policy rules
  where extra granularity is needed.

Dependencies
============

None

Testing
=======

The current unit tests are generally quite bad at testing policy, this should
be addressed before making any of the above changes.

Modify the Tempest tests for scope and default roles.

Focus on functional tests to cover the DB check and policy do the right thing
today, so we know as the code evolves we don't break existing users.

Patrole may be considered later, as it would be useful for operators to
validate their cloud's policy works the way they intended.

Documentation Impact
====================

API Reference should be kept consistent with any policy changes, in particular
around the default reader role.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Ussuri
     - Re-proposed
