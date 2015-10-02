..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Allow admins to query and create keypairs owned by any user
===========================================================

https://blueprints.launchpad.net/nova/+spec/admin-query-any-keypair

This change allows admin users to query keypairs owned by users
other than themselves, as well as to create/import new keypairs on
their behalf.

Problem description
===================

Currently, keypairs are only available to their owners. Admins should
be able to see the keypairs of other users, and create new keypairs
on their behalf, when needed.

Use Cases
----------

As the admin of an openstack cluster I need to see what keypairs a
user has.

As someone with admin permission, I want to be able to create an
instance with someone else's keypair assigned so that they can log
into it.

Allowing the administrators to create keypairs and importing public keys on
behalf of the users will allow the users to have access to an instance booted
with it.

For instances that require additional post-deployment configuration using
Configuration Management tools (Ansible, Puppet etc..), having a pre-installed
keypair deployed by the administrator is also very useful.

Project Priority
-----------------

(yet to be defined)

Proposed change
===============

For querying operations, this change doesn't affect the API format
or schema in any way, but merely adds a query key to select a specific
user for the keypair query.
However, an optional user_id parameter will need to be added to POST
operation to specify the user for which a keypair is being created.

The following requests are currently allowed for querying:

  GET /os-keypairs
  GET /os-keypairs/[keypair]

After this change, admins would be able to do this:

  Get a list of keypairs for [user_id]:
    GET /os-keypairs?user_id=[user_id]

  View a specific user's keypair
    GET /os-keypairs/[keypair]?user_id=[user_id]

* Future work:
    Allowing the admins to list keypairs from all users will require additional
    work, that will involve changes to the database scheme, will be submitted
    in a separate spec.

Alternatives
------------

We could add a new admin API method to facilitate this, but doing so
would be a lot more work for little (if any) benefit.

Data model impact
-----------------

None.

REST API impact
---------------

* Specification for the querying methods

  * The existing index operation for keypairs will be extended to
    honor an optional "user_id" parameter, if the proper microversion
    is active.

  * Method type: GET

  * Normal http response code(s): 200

  * Expected error http response code(s)

    * 403: If the user does not have permissions, per the policy file

  * ``/v2.1/{tenant_id}/os-keypairs?user_id={user_id}``
  * ``/v2.1/{tenant_id}/os-keypairs/{keypair_name}?user_id={user_id}``

  * Parameters which can be passed via the url: The alternate user id

  * JSON schema definition for the body data is unchanged

  * JSON schema definition for the response data is unchanged

* Example use case:

Request:

GET http://127.0.0.1:8774/v2.1/e0c1f4c0b9444fa086fa13881798144f/os-keypairs?user_id=example_userid

* Specification for the create/import methods

  * Create method will be extended to honor an optional "user_id" parameter,
    that will be provided in the request body,
    if the proper microversion is active.

  * Method type: POST

  * Normal http response code(s): 200

  * Expected error http response code(s)

    * 403: If the user does not have permissions, per the policy file

  * ``/v2.1/{tenant_id}/os-keypairs``

  * JSON schema definition for the response data is unchanged

  * JSON schema definition for the body data will change to include the
    optional user_id parameter:

.. code-block:: javascript

    create:
    {
      "keypair": {
          "name": "%(keypair_name)s",
          "type": "%(keypair_type)s",
          "user_id": %(user_id)s"
      }
    }

    import:
    {
      "keypair": {
          "name": "%(keypair_name)s",
          "type": "%(keypair_type)s",
          "public_key": "%(public_key)s,"
          "user_id": %(user_id)s"
      }
    }


* This will add new policy elements which will allow assigning this
  permission:

::

  "os_compute_api:os-keypairs:index": "is_admin:True or user_id:%(user_id)s"
  "os_compute_api:os-keypairs:show": "is_admin:True or user_id:%(user_id)s"
  "os_compute_api:os-keypairs:create": "is_admin:True or user_id:%(user_id)s"


Security impact
---------------

Admin users will be able to see the public keys of other
users and create new keypairs on their behalf.
However, these are generally regarded as material suitable for
public viewing anyway.

Notifications impact
--------------------

None

Other end user impact
---------------------

* This change will imply changes to the python-novaclient to allow
  specifying the user for which keypairs should be listed or created.

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

Primary assignee:
  vladikr

Other contributors:
  Dan Smith, Dan Radez

Work Items
----------

* Add a new microversion and make os-keypairs honor the user_id query/create
  parameter


Dependencies
============

None

Testing
=======

Unit tests are sufficient to verify this functionality, as it is
extremely simple. API samples tests can be added to make sure that the
output of the list call does not differ when a user_id parameter is
passed. Add new API sample to verify the create/import request schemas.

Documentation Impact
====================

The nova/api/openstack/rest_api_version_history.rst document will be updated.


References
==========

* Bug https://bugs.launchpad.net/nova/+bug/1182965 requesting this
  feature.

