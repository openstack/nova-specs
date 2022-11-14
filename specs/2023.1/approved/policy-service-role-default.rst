..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Policy Service Role Default
===========================

https://blueprints.launchpad.net/nova/+spec/policy-service-role-default

Ideally all internal service-to-service APIs should not be accessible
by admin or end user by default. From policy defaults it should be
clear which APIs are supposed to be used by admin or end user and
which is for internal service-to-service APIs communication.

Problem description
===================

Currently, internal service-to-service communication APIs have their
default policy as either admin or project roles which means operators
need to assign the admin or project roles to their service users.
That service user having admin or project role access is poor security
practice as they can perform admin or project level operations.

Another problem is that APIs which are meant to only be used by internal
services are able to be called by regular users and human admins. Requiring
(and allowing only) a service role for these APIs help avoid intentional
and accidental abuse.

Use Cases
---------

As an operator I want to keep ``service`` role user to access
service-to-service APIs with least privilege.

Proposed change
===============

We need to make sure all the policy rules for internal service-to-service
APIs are default to ``service`` role only. Example:


.. code-block:: python

   policy.DocumentedRuleDefault(
       name='os_compute_api:os-server-external-events:create',
       check_str='role:service',
       scope_types=['project']
   )

Keystone's ``service`` role is kept outside of the existing role hierarchy
that includes ``admin``, ``member``, and ``reader``. Keeping the ``service``
role outside the current hierarchy ensures we're following the principle
of least privilege for service accounts.

We need to make all the service-to-service APIs which are *only* suitable
for services default to ``service`` role only. But we might have some cases
where APIs are both intended for service usage, as well as admin (any other
user role) usage. For such policy rules we need to default them to ``service``
as well as ``admin`` (or any other user role) role. For example,
'role:admin or role:service'

As Nova have dropped the system scope implementation, service-to-service
communication with ``service`` role will be done with project scope token
(which is currently done in devstack setup).

Below APIs policy will be default to ``service`` role:

* os_compute_api:os-assisted-volume-snapshots:create
* os_compute_api:os-assisted-volume-snapshots:delete
* os_compute_api:os-volumes-attachments:swap
* os_compute_api:os-server-external-events:create

Alternatives
------------

Keep the service-to-service APIs default same as it is and expect operators
to take care of the ``service`` role users access permissions by overriding
it in the policy.yaml.

Data model impact
-----------------

None

REST API impact
---------------

Below APIs policy will be default to ``service`` role:

* os_compute_api:os-assisted-volume-snapshots:create
* os_compute_api:os-assisted-volume-snapshots:delete
* os_compute_api:os-volumes-attachments:swap
* os_compute_api:os-server-external-events:create

Security impact
---------------

Easier to understand service-to-service APIs policy and restricting them to
least privilege.

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

If service-to-service APIs are used by the admin or end user then make
sure to override the required permission in policy.yaml because by default
they will be accessed by the ``service`` role user only.

Developer impact
----------------

New APIs must add policies that follow the new pattern.

Upgrade impact
--------------

If service-to-service APIs are used by the admin or end user then make
sure to override the required permission in policy.yaml because by default
they will be accessed by the ``service`` role user only. If deployment
overrides these policies then, they need to start considering the new
default policy rules.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmann

Feature Liaison
---------------

Feature liaison:
  dansmith

Work Items
----------

* Modify the service-to-service APIs defaults
* Modify policy rule unit tests

Dependencies
============

None

Testing
=======

Modify or add the policy unit tests.

Add a job enabling the new defaults and run the tempest tests to make sure
existing service-service APIs communication work fine. If needed modify the
token used by services as per the new defaults.

Documentation Impact
====================

API Reference should be updated to add all the service-service APIs under
separate section and mention about ``service`` role as their default.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1
     - Introduced
