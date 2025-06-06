..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Policy Manager Role Default
===========================

https://blueprints.launchpad.net/nova/+spec/policy-manager-role-default

This is `SRBAC goal phase-3
<https://governance.openstack.org/tc/goals/selected/consistent-and-secure-rbac.html#phase-3>`_

A project-manager can use project-level management APIs and is denoted by
someone with the manager role on a project. It is intended to perform
more privileged operations than project-member on its project resources.
A project-manager can also perform any operations allowed to a project-member
or project-reader.

Problem description
===================

Currently, compute API policy default has admin (admin in all project),
project member, and project reader roles. But there are many project level
APIs which should be default to user who are more privileged than normal
user (member, reader role user). Instead of allowing such APIs to global
admin, we should have more privileged user within project.

Use Cases
---------

Keep project level management APIs to someone who is less privileged than admin
and more privileged than project member role.

Proposed change
===============

Keystone introduced a new role 'manager' role at project level. A
project-manager can use project-level management APIs and intend
to perform more privileged operations than project-member on its
project resources.

A project-manager can use project-level management APIs and is denoted
by someone with the manager role on a project. It is intended to perform
more privileged operations than project-member on its project resources.
A project-manager can also perform any operations allowed to a
project-member or project-reader (this is handled by the keystone role
implication so that the admin role implies manager, the manager role
implies member, the member role implies reader). One good example for Nova
to use manager role is in locking and unlocking an instance.

project-manager persona in the policy check string:

.. code-block:: python

   policy.RuleDefault(
       name="project_manager",
       check_str="role:manager and project_id:%(project_id)s",
       description="Default rule for project-level management APIs."
   )

Using it in policy rule (with admin + manager access): (because we want to
keep legacy admin behavior same we need to continue giving access of
project-level management APIs to admin role too.)

.. code-block:: python

   policy.DocumentedRuleDefault(
       name='os_compute_api:os-migrate-server:migrate
       check_str='role:admin or (' + 'role:manager and project_id:%(project_id)s)',
       description="Cold migrate a server without specifying a host",
       operations=[
           {
               'method': 'POST',
               'path': '/servers/{server_id}/action (migrate)'
           }
       ],
   )

Below APIs policy will be default to ``PROJECT_MANAGER_OR_ADMIN`` role
----------------------------------------------------------------------

**Current default: ADMIN -> New default: PROJECT_MANAGER_OR_ADMIN:**

* 'os_compute_api:os-migrate-server:migrate' ("Cold migrate a server without
  specifying a host")
* 'os_compute_api:servers:migrations:force_complete' ("Force an in-progress
  live migration for a given server ")
* 'os_compute_api:servers:migrations:delete' ("Delete(Abort) an in-progress
  live migration")

**Current default: PROJECT_MEMBER_OR_ADMIN -> New
default: PROJECT_MANAGER_OR_ADMIN:**

   .. note::

      This is making the below APIs more restrictive. Currently they are
      allowed for ``member`` and ``admin`` users but after this change, it
      will be allowed for 'manager' and 'admin' users (disallowed for 'member'
      user).

* 'os_compute_api:os-deferred-delete:restore' ("Restore a soft deleted server")
* 'os_compute_api:os-deferred-delete:force' ("Force delete a server before
  deferred cleanup")

**Introducing new policy to allow more operation for ``manager`` users:**

  There are some APIs (listed below) which should be allowed for the
  ``manager`` user, but we have single policy to perform operation (migrate
  server) to specific host or return host info in API response. To keep host
  specific operation/info to ``admin`` and rest other to ``admin-or-manager``,
  we need to introduce the separate new policy for host specific things
  which will default to ``admin`` (means no change for host specific things)
  and existing policy will be used for non-host things and will default to
  ``admin-or-manager``

* Live migrate:

  * Existing policy:

    * ``os_compute_api:os-migrate-server:migrate_live`` (live migrate server)

      * Default changing from ``ADMIN`` -> ``PROJECT_MANAGER_OR_ADMIN``

  * New policy:

    * ``os_compute_api:os-migrate-server:migrate_live:host`` (live migrate
      server to specific host)

      * Default: ``ADMIN``

* List server migration:

  * Existing policy:

    * ``os_compute_api:servers:migrations::index`` (Lists in-progress live
      migrations for a given server)

      * Default changing from: ``ADMIN`` -> ``PROJECT_MANAGER_OR_ADMIN``

  * New policy:

    * ``os_compute_api:servers:migrations:index:host`` (Lists in-progress live
      migrations for a given server with host info)

      * Default: ``ADMIN``

.. note::

   Currently, project member can perform the below server actions. It might
   not be good idea to add more strict access control on them.  We will
   continue allow project member user to perform these action. With keystone
   implied roles, project manager can also perform the below actions in their
   project servers.

   * 'os_compute_api:os-lock-server:lock' ("Lock a server")
   * 'os_compute_api:os-lock-server:unlock' ("Unlock a server")
   * 'os_compute_api:os-pause-server:pause' ("Pause a server")
   * 'os_compute_api:os-pause-server:unpause' ("Unpause a paused server")
   * 'os_compute_api:os-rescue' ("Rescue a server")
   * 'os_compute_api:os-unrescue' ("Unrescue a server")
   * 'os_compute_api:os-suspend-server:resume' ("Resume suspended server")
   * 'os_compute_api:os-suspend-server:suspend' ("Suspend server")
   * 'os_compute_api:servers:resize' ("Resize a server")
   * 'os_compute_api:servers:confirm_resize' ("Confirm a server resize")
   * 'os_compute_api:servers:revert_resize' ("Revert a server resize")
   * 'os_compute_api:servers:reboot' ("Reboot a server")
   * 'os_compute_api:servers:rebuild' ("Rebuild a server")
   * 'os_compute_api:servers:rebuild:trusted_certs' ("Rebuild a server with
     trusted image certificate IDs")

Alternatives
------------

Keep admin or member do all project level management operation.

Data model impact
-----------------

None

REST API impact
---------------

Below APIs policy default will be changed:

**Current default: ADMIN -> New default: PROJECT_MANAGER_OR_ADMIN:**

* 'os_compute_api:os-migrate-server:migrate'
* 'os_compute_api:servers:migrations:force_complete'
* 'os_compute_api:servers:migrations:delete'
* 'os_compute_api:os-migrate-server:migrate_live'
* 'os_compute_api:servers:migrations:index'

**Current default: PROJECT_MEMBER_OR_ADMIN -> New
default: PROJECT_MANAGER_OR_ADMIN:**

* 'os_compute_api:os-deferred-delete:restore'
* 'os_compute_api:os-deferred-delete:force'

**Introducing below new policies default to PROJECT_MANAGER_OR_ADMIN:**

* 'os_compute_api:os-migrate-server:migrate_live:host'
* 'os_compute_api:servers:migrations:index:host'

Security impact
---------------

Provide more secure RBAC by adding project manager role to handle project
resources management activities.

Notifications impact
--------------------

None

Other end user impact
---------------------

Below API policies default will not be allowed for 'member' role user,
they need 'manager' role in their project to continue performing these
operations.

* 'os_compute_api:os-deferred-delete:restore'
* 'os_compute_api:os-deferred-delete:force'


Performance Impact
------------------

None

Other deployer impact
---------------------

The below APIs policy default is changed from ``member`` to ``manager`` role,
make sure to override the required permission in policy.yaml or move the
deployment to the new defaults.

* 'os_compute_api:os-deferred-delete:restore'
* 'os_compute_api:os-deferred-delete:force'

New policies are introduced to control the host specific operation/information.
Below policies defaults are changed to allow the project 'manager' role also.

* 'os_compute_api:os-migrate-server:migrate_live'
* 'os_compute_api:servers:migrations:index'

If you have overridden the above policies with other permission, then override
the same permission for the new policies also:

* 'os_compute_api:os-migrate-server:migrate_live:host'
* 'os_compute_api:servers:migrations:index:host'

Developer impact
----------------

New APIs must add policies that follow the new pattern.

Upgrade impact
--------------

New policies are introduced to control the host specific operation/information.
Below policies defaults are changed to allow the project 'manager' role also.

* 'os_compute_api:os-migrate-server:migrate_live'
* 'os_compute_api:servers:migrations:index'

If you have overridden the above policies with other permission, then override
the same permission for the new policies also:

* 'os_compute_api:os-migrate-server:migrate_live:host'
* 'os_compute_api:servers:migrations:index:host'

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmaan

Feature Liaison
---------------

Feature liaison:
  gmaan

Work Items
----------

* Modify the project-level management APIs defaults to ``manager`` role
* Modify policy rule unit tests to use service and manager role token
* Move Tempest tests of changed policies to new defaults.

Dependencies
============

None

Testing
=======

Modify or add the policy unit tests.
Move Tempest tests of changed policies to new defaults.

Documentation Impact
====================

The ``manager`` role API defaults will be updated in policy rule document
as well as in policy sample file.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.2 Flamingo
     - Introduced
