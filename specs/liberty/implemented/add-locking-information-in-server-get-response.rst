..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Add 'locked' in server Detail Response
======================================

https://blueprints.launchpad.net/nova/+spec/add-locking-information-in-server-get-response

Currently admin or owner can lock/unlock the instance but there is no way to
know whether instance is locked.
This spec is to propose a way to know lock information by adding new
'locked' attribute in server GET APIs Response.

Problem description
===================

Currently Instance can be locked and unlocked by admin or owner. But there is
no way to get to know who locked the instance. Even users cannot know
whether that instance is locked or not.

Use Cases
----------

User can know whether instance is locked. When user want to perform any action
on instance and it is locked then it return error about instance not in proper
state. If there is prior way to know whether instance is locked, it will be
easy for user/admin to do appropriate action accordingly.

As lock/unlock action can be performed by admin or owner (more than one role),
'locked' information can be very useful.

Project Priority
-----------------

None.

Proposed change
===============

Add new attribute 'locked' in server detail response which will
provide instance lock information.

Returned value by 'locked' attribute will be-

* True - If instance is locked.
* False - If instance is not locked.

When user will query about instance details (List Detail or Show), 'locked'
information will be returned in response.

When "locked" is "true", it means there is a lock on instance, it does not
mean instance is locked for requested users.
For example - When instance is locked by the owner but listed by an admin,
"locked" will be "true" even admin can override the owner lock.

So "locked" provides only concrete information whether instance is locked
or not.

We could have provide lock information by exposing "locked_by" (which
holds the lock owner information in current implementation) directly but
as in most cases instance will not be locked so its value will be null.
And its always better to expose the simple and concrete information than
implementation one which can be changed in future as lock things can be
expanded in future.

NOTE-
Lock can be made it's own resource at a later time which will help to know
complete information about instance lock (locked by whom, lock reason,
time stamp etc).
New lock API can looks like something - servers/server_id/lock.

Alternatives
------------

User can get to know locked status from exception returned on performing
invalid action on locked server. But there will not be any way to know who
locked instance.

Data model impact
-----------------

None.

REST API impact
---------------

* Specification for the method

  * Description

    * API Show server details & List servers details

  * Method type

    * GET

  * Normal http response code

    * 200, no change in response code

  * Expected error http response code(s)

    * No change in error codes

  * URL for the resource

    * /v2.1

  * JSON schema definition for the body data if allowed

    * A request body is not allowed.

  * JSON schema definition for the response data if any

::

  {
    'status_code': [200],
    'response_body': {
      'type': 'object',
      'properties': {
        'server': {
          'type': 'object',
          'properties': {
            'id': {'type': 'string'},
            'name': {'type': 'string'},
            'status': {'type': 'string'},
            .
            .
            'locked': {'type': 'boolean'},
            .
            .
            .
            'OS-EXT-STS:task_state': {'type': ['string', 'null']},
            'OS-EXT-STS:vm_state': {'type': 'string'},
            'OS-EXT-STS:power_state': {'type': 'integer'},
            .
            .
            .
          },
        }
      }
      'required': ['server']
    }
  }

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

python-novaclient needs to be updated in order to show the 'locked'
in the 'nova show' commands.

Performance Impact
------------------

None.
Locked by information is already present in Instance object, this will just
show that information to user.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmann

Other contributors:
  None

Work Items
----------

* Add 'locked' in server GET APIs (Show and List Detail)
  Response.
* Modify Sample and unit tests accordingly.

Dependencies
============

None.

Testing
=======

Currently Nova functional test will cover these changes testing.
After discussion of micro version testing in Tempest, these changes
can be tested accordingly.

Documentation Impact
====================

server GET APIs doc will be updated accordingly.

References
==========

