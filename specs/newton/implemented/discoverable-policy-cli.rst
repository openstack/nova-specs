..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Nova discoverable policy CLI
============================

https://blueprints.launchpad.net/nova/+spec/get-policy-settings-cli

Not all users have the same set of privileges. Because of this, adding a way
to list the policy rules the user passes can be helpful.


Problem description
===================

Currently, users have no direct way of knowing which APIs they are allowed to
use or which APIs are enabled by policy. This spec will add a new CLI command
that will return a list of available operations usable by the user.

Use Cases
---------

As an user, I want to know what policies I am passing, so I can know what
actions are available to me.

As an user, I want to know what policies I am passing for a certain target (
e.g.: instance), so I can know what actions I can take.


Proposed change
===============

The proposed change takes two phases. The first phase, detailed in this spec,
implements the necessary plumbing to prove out the concept providing raw data
though a nova CLI command.
The second phase, described in brief below, will transform the raw data
into a long-term viable form presented in a new microversion of the
API.

Phase one
---------

The discoverable policy will be exposed through the ``nova-policy-check``
nova CLI command.

This command will require user authentication. The authentication options will
be the same as python-novaclient, they can be passed in as arguments, or they
will be loaded from the environment.

The command will return a list of policy rule names to the requesting user.
It will not return the authorization conditions required to pass the policy
rules. It cannot be used to determine the list of policy rules passed by
other users.

The returned operations will have to fulfill the following criteria:

* The requesting user will pass the operation's policy rule. For example, if
  the policy states that the operation ``foo-bar`` is only usable by an admin,
  the operation will be returned only if the requesting user is an admin.

* The API endpoint will have to be marked as discoverable. By default, all
  APIs are discoverable [1]. For example, having the following policy rule:
  ``os_compute_api:servers:discoverable": "is_admin:True`` means that the
  ``servers`` API and its operations is discoverable only by an admin and will
  not be returned to any other users.

This will allow testing of all the moving parts, notably user permissions.

Phase two
---------

Once phase one has been released, phase two can begin. In phase two
the raw data will be transformed into a format that does not expose
the internal details of the server's implementation of policy. For
example, clients don't want to know the name of actions, they want
to know the URI.

Once this long term format has been decided and implemented, the
API can then be documented, exposed by default (by changing the
default of the above configuration item) and associated with a
microversion bump.

Alternatives
------------

An alternative would be to combine phases one and two into one unit
of work. There are two issues with this idea:

* Without the break into two phases, the learning from the concrete
  experience of phase one could not be effectively incorporated into
  the work.
* Doing all the work in one push will be challenging to complete in
  a reasonable amount of time, lengthening the time before concrete
  learning can be had from real deployments.

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

The nova ``nova-policy-check`` CLI command will require authentication. The
authentication options will be the same as python-novaclient and they can be
passed in as arguments or loaded from the environment. An exception will be
raised if there are no credentials present or they are wrong.

The command will return as follows, depending on the arguments given:

* No args. The command will check the default policy rules and will return all
  passing policy rule names.
* ``config-file``. The command loads the given ``nova.conf`` configuration
  file and its associated policy file, if any, overriding the default policy
  rules. The command will return all passing policy rule names. For example::

    nova policy-check --config-file /path/to/nova.conf

  If the file was not found, couldn't be read, or couldn't be parsed, an error
  will be raised.

* ``api-name`` argument given. The command will only list passing policy rules
  containing the given API name. For example::

    nova-policy-check --api-name os-keypairs

    or

    nova-policy-check --api-name os-keyp

  This command will only list the passing policies for ``os-keypairs``::

    "os_compute_api:os-keypairs:discoverable": "@"
    "os_compute_api:os-keypairs": "rule:admin_or_owner"
    "os_compute_api:os-keypairs:index": "rule:admin_api or user_id:%(user_id)s"
    "os_compute_api:os-keypairs:show": "rule:admin_api or user_id:%(user_id)s"
    "os_compute_api:os-keypairs:create": "rule:admin_api or user_id:%(user_id)s"
    "os_compute_api:os-keypairs:delete": "rule:admin_api or user_id:%(user_id)s"

* ``target`` arguments given. The command will only list passing policies for
  the given targets. For example::

    nova-policy-check --target instance:<instance_uuid>

  This command will list the passing policies for the given target::

    "os_compute_api:servers:create"
    "os_compute_api:servers:create:attach_network"
    ...
    "os_compute_api:os-admin-actions"
    "os_compute_api:os-admin-actions:reset_network"

  If there is no instance with the given ``instance_uuid``, the command will
  raise an error.

  Multiple ``target`` arguments can be used::

    nova-policy-check --target project_id:<project_id> --target user_id:<uid>

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignees:
  Claudiu Belu <cbelu@cloudbasesolutions.com>
  Andrew Laski <andrew@lascii.com>

Work Items
----------

* ``nova-policy-check`` CLI command.

Phase two will be specified in a separate spec that will be created
in response to what is learned from implementation phase one.


Dependencies
============

Embed policy defaults in code:
  https://review.openstack.org/#/c/290155/


Testing
=======

* Unit & functional tests.


Documentation Impact
====================

New nova CLI command will have to be documented.


References
==========

[1] Default "discoverable" policies to "@"
  https://review.openstack.org/#/c/281911/1

[2] Nova API meeting
  http://eavesdrop.openstack.org/meetings/nova_api/2016/nova_api.2016-04-13-13.00.log.html

[3] Newton Design Summit
  https://etherpad.openstack.org/p/newton-nova-api


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
