..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Add project validation via Keystone to quota and flavor management
==================================================================

https://blueprints.launchpad.net/nova/+spec/validate-project-with-keystone

When an administrator performs functions on other tenants, they have to specify
a project id to identify the tenant. Nova does not currently check the validity
of this administrator-provided project id.

The scope of this blueprint is to add project id validation to quota management
(i.e. quota-defaults, quota-detail, quota-show, quota-update) and to flavor
access management (i.e. flavor-access-add). Adding project id validation to any
functionality outside of quota and flavor management is beyond the scope of
this blueprint.


Problem description
===================

Nova quota sets management and flavor access management through the
CLI require the administrator to specify a project id. Nothing
actually checks if this project id actually exists, so a administrator
can easily specify an invalid project.

If an invalid project id is provided to the quota-update command when
updating the quota for a particular quota class, Nova reports
unexpected quota information. The project id specified by the user
ends up in the project_id field in the entry created in Nova's
project_user_quotas table. When the project id does not match what is
in the project_user_quotas table, invalid quotas are set. Any function
performed on a project that has a quota check will not be affected the
way the administrator expects.

For instance, if the administrator wants to increase the number of
floating ip address for a given project id because that project has
used all of its quota, and the wrong project id was provided to
quota-update, any attempt to add additional floating ip addresses will
unexpectedly fail. Historically, administrators debugging this issue
have filed invalid bugs against Nova quota management.


Use Cases
----------

As an administrator, when I attempt to modify quota or flavor access
information on one of my projects, and I accidentally provide an
invalid project id:

* I want to know the project id I provided is invalid.

* I don't want my existing quota or flavor access data updated when I
  provide an invalid project id.


Proposed change
===============

Nova will use the requestor's user token to query Keystone. The
Keystone response will determine access to the project and indicate if
the project exists.

Keystone will return one of the following results, which will be
translated into a Nova response:

* 200 - project exists, Nova proceeds

* 404 - project does not exist, Nova returns a 400 bad response
  stating that no such project id has been found

* 403 - user does not have permissions to ask the question, we will
  process as if it succeeds but log that we didn't have permissions to
  verify.

* Anything else - something is way wrong. Nova will proceed as if it's
  a success, but we will log the response as a warning.

Because this change is dependent on policy information being set
correctly between Keystone and Nova, we need to provide guidance for
operators setting this policy. This update will require a release note
and a documentation update.

API changes will only be made to v2.1; API v2.0 is currently frozen.

Alternatives
------------

Status Quo: don't validate the project id and leave it up to the user
to figure out the appropriate project id via "keystone
tenant-list". This will continue to be a poor user experience for end
users and the Nova team will continue to field bug reports on
inaccurate quotas and flavor access values.

Another alternative is to have the python-novaclient validate the
project id and expect other clients (e.g. third party) to do the
same. This doesn't solve for the problem in Nova itself where invalid
project id's end up in the database. It does make sense to have the
CLI handle project name verification as this change would only apply
to project id verification.

An alternative discussed during the cross-project session at the
Newton summit was to use the Nova service user token to access the
data from Keystone. This was dismissed because it obfuscates what
users have access to what resources and could present a potential
security risk.

Finally, another option explored in the past was simply doing UUID
verification. This approach was rejected because we don't require
project id's to be UUID's, so valid project id's would be rejected.

Data model impact
-----------------

None. If any entries exist with the project_id set to an invalid id,
they can be deleted using the relevant delete commands. Deletes should
not trigger project id validation.

REST API impact
---------------

Project id validation would create a new error condition for certain
API methods.

If a Keystone service account exists to validate the project id, and
the project id is invalid, the API will return an HTTPBadRequest from
the POST and GET requests with error text.

The following API methods would be impacted:

* quota-defaults

* quota-detail

* quota-show

* quota-update

* flavor-access-add

Security impact
---------------

None. This is using existing authorization mechanisms and doesn't
present any new logic.

Notifications impact
--------------------

None

Performance Impact
------------------

There will be minor impact to performance. While a request to Keystone
is required to validate the project id, it would be a low-frequency
operation because quotas/flavor access are not often changed.

Other end user impact
---------------------

Users will need documentation on how to configure their Keystone and
Nova policy to take advantage of this update.

An attempt to show existing entries for an invalid project id will
result in a 400 error. Future work should provide users with a
mechanism for cleaning up bad entries.

Other deployer impact
---------------------

The quota and flavor operations should not be blocked if either
Keystone does not exist or if the Keystone policy is not set up
correctly for project id validation. In this case, a warning message
should be logged indicating that project id validation is
unavailable. This warning should be logged each time for improved
visibility to the operator, so they can fix their policy.

Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sdague


Work Items
----------

* Access the user token via the current context

* Implement methods to get the project by a given id.

* Modify QuotaSetsController class in
  nova/api/openstack/compute/quotas.py to validate the project id, if
  provided.

* Modify FlavorActionController class in
  nova/api/openstack/compute/flavor_access.py to validate the project
  id, if provided.

* Create tempest test cases and Nova unit and functional test cases to
  verify functionality.

* Update the Keystone DocImpact bug with policy examples so the
  documentation can be updated.

Dependencies
============
None


Testing
=======

Tempest test cases, as well as Nova unit and functional test cases, will be
created to verify project id verification.

Tempest test coverage:

* Keystone validation

* A feature toggle in Tempest to tell it if Keystone is configured properly (in
  devstack) for the policy to work

Commands to be tested with validation:

* quota-defaults

* quota-detail

* quota-show

* quota-update

* flavor-access-add

Test cases for each command:

* valid project id - 200

* invalid project id - 400

* user has access to valid project - 200

* user does not have access to valid project - 403

* Keystone is unavailable - log warning

Commands to be tested with no validation:

* quota-delete

* flavor-access-delete

Test cases for each command:

* pre-existing invalid project id - 200

* new invalid project id - 200 (current behavior)

  ** a new entry should not be created and then deleted

Documentation Impact
====================
None


References
==========
* Previous proposed code change: https://review.openstack.org/#/c/91866/
* Reported bugs:
  https://bugs.launchpad.net/nova/+bug/1313935
  https://bugs.launchpad.net/nova/+bug/1317515
  https://bugs.launchpad.net/nova/+bug/1118066
* Customizing authorization:
  http://docs.openstack.org/trunk/openstack-ops/content/projects_users.html
