..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
servers list API support specify multi-status
==============================================

https://blueprints.launchpad.net/nova/+spec/servers-list-support-multi-status

Allow to specify multiple status value concurrently in the servers list API.

Problem description
===================

Currently the service list API allows the user to specify an optional status
value to use as a filter - for example to limit the list to only servers with
a status of Active.

However often the user wants to filter the list by a set of status values,
for example list servers with a status of Active or Error,
which requires two separate API calls.

Allowing the API to accept a list of status values would reduce this to a
single API call.

Proposed change
===============

Enable servers list API to support to specify multiple status values
concurrently.


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Allow to specify status value for many times in a request.

For example::

    GET /v2/{tenant_id}/servers?status=ACTIVE&status=ERROR
    GET /v3/servers?status=ACTIVE&status=ERROR

V2 API extension::

    {
        "alias": "os-server-list-multi-status",
        "description": "Allow to filter the
            servers by a set of status values.",
        "links": [],
        "name": "ServerListMultiStatus",
        "namespace": "http://docs.openstack.org/compute/ext/
            os-server-list-multi-status/api/v2",
        "updated": "2014-05-11T00:00:00Z"
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
  boh.ricky

Work Items
----------

Implement the support for servers list API to specify multiple status values
concurrently.

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

Need to document in the API document.

References
==========

None
