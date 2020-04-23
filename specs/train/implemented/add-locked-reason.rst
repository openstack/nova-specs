..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Support adding the reason behind a server lock
==============================================

https://blueprints.launchpad.net/nova/+spec/add-locked-reason

Currently as a part of locking an instance, while we know who locked it we do
not have a way of knowing "why" it was locked. This spec aims at addressing
this question.

Problem description
===================

When locking a server using the nova lock action there is no provision to set
a description or mention a reason of why it's being locked. This is often a
much needed information in situations (eg. security/hardware team locking the
server or when an automated job locks the server or an admin locks it and goes
on vacation) when it's not ideal to just ask the user why it was locked and if
it could be unlocked.

Use Cases
---------

As a cloud operator I would like to know why a certain user locked the server
when that user is not contactable or without having to open internal tickets
to find out.

As an user/admin I would like to add a reason when locking the server like the
date after which it is safe to unlock so that the other admins know this.

Proposed change
===============

This spec proposes to store the locked_reason as an item in the system metadata
of the instance.

The request for ``POST /servers/{server_id}/action`` where action is "lock"
will get a new optional argument called ``locked_reason`` by which the user can
specify the reason for locking the instance. If the reason is specified, it
will create the ``locked_reason`` item in the instance_system_metadata for
that instance which will be deleted upon unlocking the instance.

The plan is to expose ``locked_reason``  information by adding it as a new key
in the response of ``GET servers/{server_id}``, ``GET /servers/detail``,
``POST /servers/{server_id}/action``  where the action is rebuild and
``PUT servers/{server_id}`` requests. See the `REST API impact`_ section for
more details on how this would be done.

Alternatives
------------

One alternative would be to not have the
``POST /servers/{server_id}/action`` at all for the locking mechanism and just
do this via the ``PUT servers/{server_id}`` request.

Another alternative is to make lock as its `own resource`_ in which case we can
add a new lock API which would look like ``GET servers/{server_id}/lock`` that
can include the details like locked or not, locked_by, locked_reason and
timestamp. But we already have a
``GET servers/{server_id}/os-instance-actions/{request_id}`` request API to get
the details like timestamp. So it does not make sense to add a whole new API
for just retrieving the locked_reason information.

Data model impact
-----------------

None.

REST API impact
---------------

The request for ``POST /servers/{server_id}/action`` will change since it will
get a new optional argument called ``locked_reason`` which will accept the
reason for locking the server and store this in the instance_system_metadata
table in the database.

A sample JSON request for locking a server would look like this::

    "lock": {
       "locked_reason": "because I am mad at belmiro"
    }

The request body would either be a "null" object in case the reason is not
specified or it will have a "locked_reason" field in the object (possible from
the new microversion).

We plan to expose the ``locked_reason`` information through
``GET servers/{server_id}``, ``GET /servers/detail``,
``POST /servers/{server_id}/action``  where the action is rebuild and
``PUT servers/{server_id}`` REST APIs whose reponses will have that key.

Currently the response only contains the "locked" key which is of type boolean
that conveys if the instance is locked or not based on if it's true or false.
We will now also include the ``locked_reason`` key in addition to the locked
key.

A sample JSON response would look like this for a locked server::

    {
        "servers": [
            {
                "OS-EXT-STS:task_state": null,
                "id": "b546af1e-3893-44ea-a660-c6b998a64ba7",
                "status": "ACTIVE",
                .
                .
                .
                "locked": true,
                "locked_reason": "foo-test",
                .
                .
                .
                "name": "surya-probes-001",
                "OS-EXT-SRV-ATTR:launch_index": 0,
                "created": "2018-06-29T15:07:29Z",
                "tenant_id": "940f47b984034c7f8f9624ab28f5643c",
                .
                .
                "host_status": "UP",
                "trusted_image_certificates": null,
                "metadata": {}
            }
        ]
    }

Note that it is the duty of the admin locking the instance to put information
that can be user-visible in the reason because there is no protection there.

A sample JSON response would look like this for an unlocked server::

    {
        "servers": [
            {
                "OS-EXT-STS:task_state": null,
                "id": "b546af1e-3893-44ea-a660-c6b998a64ba7",
                "status": "ACTIVE",
                .
                .
                .
                "locked": false,
                "locked_reason": null,
                .
                .
                .
                "name": "surya-probes-001",
                "OS-EXT-SRV-ATTR:launch_index": 0,
                "created": "2018-06-29T15:07:29Z",
                "tenant_id": "940f47b984034c7f8f9624ab28f5643c",
                .
                .
                "host_status": "UP",
                "trusted_image_certificates": null,
                "metadata": {}
            }
        ]
    }

Filtering/Sorting: The ``locked`` key will be added to the existing list of
valid sorting/filtering keys so that instances can be filtered/sorted based
on this field.

Security impact
---------------

The admin locking the instance should take care not to expose information
through the locked_reason that the owner should not know about.

Notifications impact
--------------------

The InstancePayload object will be updated to include the
"locked_reason" field which can be added to the InstanceActionPayload
notification that would be emitted when locking the instance. This would
require a version bump for the payload notification objects.

A sample notification for a locked server::

    {
        "event_type": "instance.lock",
        "payload": {
            "$ref": "common_payloads/InstanceActionPayload.json#",
            "nova_object.data": {
                "locked": true,
                "locked_reason": "foo-test"
            }
        },
        "priority": "INFO",
        "publisher_id": "nova-api:fake-mini"
    }

Other end user impact
---------------------

In order to be able to provide a reason and then see this when asking for a
server show, python-openstackclient and python-novaclient will be updated:

* to add the new optional parameter ``--reason`` for
  ``POST /servers/{server_id}/action`` where the action is "lock".
* to accommodate the parsing of the new keys in the server
  response for ``GET servers/{server_id}``, ``GET /servers/detail``,
  ``POST /servers/{server_id}/action``  where the action is rebuild and
  ``PUT servers/{server_id}`` REST APIs from the new microversion.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <tssurya>

Work Items
----------

#. Handle ``POST /servers/{server_id}/action`` on receiving an optional
   "locked_reason" parameter for lock action on the client side.
#. Expose the ``locked_reason`` through ``GET servers/{server_id}``,
   ``GET /servers/detail``, ``POST /servers/{server_id}/action``  where the
   action is rebuild and ``PUT servers/{server_id}`` REST APIs after
   setting/deleting the reason while locking/unlocking and bumping the
   microversion on the server side.
#. Support filtering and sorting servers on the ``locked`` parameter.

Dependencies
============

None.


Testing
=======

Unit and functional tests for verifying the functionality. Tempest schema test
for changing the REST API response schema format.

Documentation Impact
====================

Update the description of the Compute API reference with regards to the
changes in the REST APIs.

References
==========

.. _own resource: https://review.openstack.org/#/c/206864/1/specs/liberty/approved/add-locking-information-in-server-get-response.rst@55

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
