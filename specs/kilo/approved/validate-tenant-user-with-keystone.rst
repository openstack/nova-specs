..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Validate project with Keystone
==========================================

https://blueprints.launchpad.net/nova/+spec/validate-project-with-keystone

Today there is no functionality to validate the project that is consumed by
Nova.  One reason for the lack of such functionality is performance, where
validating to external services can cause poor performance.  However, such
functionality is needed in cases where the user passes in the project ID or
name (i.e. quota management), so that the correct quota is set.  Such
functionality is also needed where the user wants to grant a project
access to a flavor.

This blueprint is only intended for cases where the API calls are done on a
very infrequent basis.  More specifically, it is only meant to be used for
validating project ID in quota management (i.e. quota-defaults, quota-show,
quota-update) and in flavor management (i.e. flavor-access-add,
flavor-access-list).  A separate blueprint is required for any functionality
that is outside of quota and flavor management.

It is important to note that this implementation does not support
validating the user ID.  Federated users are not mirrored in the Keystone
identity backend, i.e. SQL.  An external Identity Provider is responsible for
authenticating users and communicates the result of authentication to Keystone
using SAML assertions.

Problem description
===================

The quota management feature of Nova requires a project ID to be specified as
part of the CLI.  This affects nova quota-show and quota-update.  When a
project is specified in one of the quota actions above, they are not checked
against Keystone to validate their IDs.

A user could specify a project name instead of the project ID, e.g.
nova quota-update --instances 9 demo.  Since no checks are done, an entry
is created in Nova's project_user_quotas table where the project_id is set to
the project name.  This causes invalid quotas to be set and returned if the
project ID does not match what is in the project_user_quotas table.

It also affects flavor management.  More specifically, nova flavor-access-add
and flavor-access-list.  When a project is specified in one of the flavor
actions above, they are not checked against Keystone to validate their IDs.

Use Cases
----------
As an end user, I want to correctly set the quota and flavor access for a
given project ID.  I do not want to accidentally set the quota or flavor
access using an invalid project ID and assume that the operation succeeded
when it actually did not.

This implementation provides a layer of validation, such that the project
ID provided by an end user are correctly validated against Keystone for
quota and flavor management.  Invalid project ID provided by an end user are
rejected and would not create an invalid entry in the database.

Project Priority
-----------------
The priority is undefined at the moment.  This implementation provides a layer
of validation, such that the project ID provided by an end user are correctly
validated against Keystone for quota and flavor management.


Proposed change
===============

The proposed solution is to expose a Keystone client in Nova, similar to the
cinder client that exists today in nova/volume/cinder.py.  Methods to get the
project by their ID would be implemented.  When a project ID is specified,
it would be queried against the Keystone client and validated.

Alternatives
------------
The existing behavior, where the project ID is not validated, could be left
as-is.  It would be up to the user to figure out the appropriate project ID
from "keystone tenant-list".  However, this alternative presents user errors,
where the user could mistakenly specify the project name instead of the
project ID for nova quota-show or quota-update.  If this occurs, the quota
would not be set correctly.

Another alternative is to have the python-novaclient validate the project ID
and expect other clients (e.g. third party) to do the same.  However, it
does not prevent wrong data from being inserted into Nova if other clients do
not do the validation before calling Nova.

Data model impact
-----------------
It may be possible that there are entries in Nova's project_user_quotas table,
where the project_id is set to an invalid ID.  However, these entries do not
hold any significant value, since no actual project is tied to them.  In such
case, the quota-delete command can still be used to delete the invalid
entries, since no project_id validation are done against delete operations.

REST API impact
---------------
Previously, a POST and GET request using an invalid project ID would create an
entry in Nova's project_user_quotas table or return the quota value (if any)
for the project.  With this proposal, if a Keystone service account exists to
validate the project ID, HTTPBadRequest (code 400) will be returned from the
POST and GET requests for an invalid project.  If a Keystone service account
does not exist, the functionality would continue to function as before and
only a warning message would be logged (not returned via the POST or GET
request).

Security impact
---------------
To properly validate a project ID, a Keystone service account with enough
privileges to lookup a project needs to be created.  The account should have
limited access to Keystone and not any other services.  This can be done by
creating the appropriate role-based rules in /etc/keystone/policy.json and
granting the ability to lookup projects to a role.

For example, an admin can create a user (e.g. validator) and add a role to it
(e.g. validation).  Under /etc/keystone/policy.json, the admin would add these
rules::

  "identity:get_project": "rule:admin_required or role:validation",

Under /etc/nova/nova.conf, the admin would add these credentials::

  keystone_service_project_name = service
  keystone_service_user = validator
  keystone_service_password = keystone

A Keystone client would be instantiated using the credentials above, if they
exists.

If Nova is not configured to perform the lookup, the operation should not be
blocked.  Instead, a warning message should be logged stating that Nova is
not configured to perform the lookup.  If Nova is configured to perform the
lookup, but the Keystone service account is invalid, the operation should be
blocked and an error should be reported.

Notifications impact
--------------------
None

Other end user impact
---------------------
If a Keystone service account exists to validate the project ID,
HTTPBadRequest will be returned from the POST and GET requests for an invalid
project.  The explaination would be:

* The specified project ID is not valid.

Performance Impact
------------------
There will be minor impact to performance.  A connection to Keystone is
required to validate the project ID.  However, it would be a
low-frequency operation because quotas/flavor access are not often changed.

Other deployer impact
---------------------
None

Developer impact
----------------
To properly validate a project ID, a Keystone service account needs to be
created.  If a Keystone service account does not exist, the quota and flavor
operation should not be blocked.  Instead, a warning message should be
logged stating that the Keystone service account does not exist.  This will
allow existing deployments to continue to work.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  thang-pham

Other contributors:
  None

Work Items
----------

* Create a method to instantiate the Keystone client.

* Implement methods to get the project by a given ID.

* Modify QuotaSetsController class in
  nova/api/openstack/compute/contrib/quotas.py to validate the project ID, if
  any.

* Modify FlavorActionController class in
  nova/api/openstack/compute/contrib/flavor_access.py to validate the project
  ID, if any.

* Modify devstack to create the Keystone service account, saving its
  credentials in /etc/nova/nova.conf, and limiting its access in
  /etc/keystone/policy.json.

* Create tempest test cases and Nova unit test cases to verify functionality.


Dependencies
============
None


Testing
=======
Tempest test cases, as well as Nova unit test cases, will be created to verify
this feature.  The following commands should be tested: nova quota-show and
quota-update.  More specifically, the --tenant options need to be specified
with the proper ID for positive test cases, and invalid IDs for negative test
cases.  The following commands should also be tested: flavor-access-add and
flavor-access-list.  The tenant_id needs to be specified with the proper ID
for positive test cases, and invalid IDs for negative test cases.


Documentation Impact
====================
None


References
==========
* Proposed code change: https://review.openstack.org/#/c/91866/
* Reported bugs:
  https://bugs.launchpad.net/nova/+bug/1313935
  https://bugs.launchpad.net/nova/+bug/1317515
  https://bugs.launchpad.net/nova/+bug/1118066
* Customizing authorization:
  http://docs.openstack.org/trunk/openstack-ops/content/projects_users.html
