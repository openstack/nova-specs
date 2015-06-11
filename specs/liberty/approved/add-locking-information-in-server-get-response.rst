..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================
Add 'locked_by' in server GET (Show and List Detail) Response
=============================================================

https://blueprints.launchpad.net/nova/+spec/add-locking-information-in-server-get-response

Currently admin or owner can lock/unlock the instance but there is no way to
know who locked the instance.
This spec is to propose a way to know lock information by adding new
'locked_by' attribute in server GET APIs (Show and List Detail) Response.

Problem description
===================

Currently Instance can be locked and unlocked by admin or owner. But there is
no way to get to know who locked the server. Even users cannot know
whether that instance is locked or not.

Use Cases
----------

User can know whether instance is locked and who locked the instance. When
user want to perform any action on instance and it is locked then it return
error about instance not in proper state. If there is prior way to know whether
instance is locked and who has locked then, it will be easy for user/admin
to do appropriate action accordingly.

As lock/unlock action can be performed by admin or owner (more than one role),
'locked_by' information can be very useful.

Project Priority
-----------------

None.

Proposed change
===============

Add new 'locked_by' attribute in server GET APIs (Show and List Detail)
Response which will provide instance lock information.

Returned value by 'locked_by' attribute will be-

* 'admin' - If instance is locked by admin.
* 'owner' - If instance is locked by owner.
* null - If instance is not locked.

When user will query about instance details (List Detail or Show), 'locked_by'
information will be returned in response.

If 'locked_by' is null then it means instance is not locked.

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
            'locked_by': {'enum': [None, 'admin', 'owner']},
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

python-novaclient needs to be updated in order to show the 'locked_by'
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

* Add 'locked_by' in server GET APIs (Show and List Detail)
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

