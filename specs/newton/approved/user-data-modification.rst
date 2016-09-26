..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Allow user_data modification
============================

https://blueprints.launchpad.net/nova/+spec/userdata-modification

Current nova API allows setting up user_data during server creation and
retrieving it along with other extended server attributes.
EC2 API requires public API for modification of this data for compatibility
with Amazon.
However, it will be implemented only for user_data owned by metadata
server. If metadata is stored on config drive it will not be changed.

Problem description
===================

There is no mechanism for end-user to modify user_data.

Use Cases
----------

1. User wants to modify user_data. Impacts end user.

Project Priority
-----------------

None

Proposed change
===============

Add a new microversion allowing modification of OS-USER-DATA:user_data via
PUT method.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The method:

"/v2/{project_id}/servers/{server_id}"

With the method type PUT.

will be updated to allow setting of attribute
"user_data"
The JSON schema will be used exactly the same as for creation (it will be
reused):
::

    server_create = {
        'user_data': {
        'type': 'string',
        'format': 'base64'
    }

Security impact
---------------

None

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

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Alexandre Levine (alexandrelevine@gmail.com)

Work Items
----------

Single work item.

Dependencies
============

None

Testing
=======

Unit tests and functional tests to be created.

Documentation Impact
====================

Compute API documentation changes

References
==========

``https://etherpad.openstack.org/p/YVR-nova-contributor-meetup``

``http://docs.aws.amazon.com/AWSEC2/latest/APIReference/
API_ModifyInstanceAttribute.html``

History
=======

None
