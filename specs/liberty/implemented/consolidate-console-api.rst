..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Consolidate the APIs for getting consoles
==========================================

https://blueprints.launchpad.net/nova/+spec/consolidate-console-api

We have different public API for getting console access for each kind of
console that is supported in Nova. The proposal is to consolidate all these
APIs into one.

Problem description
===================

The APIs for getting console access are tightly coupled with the name of the
underlying protocol: os-getVNCConsole, os-getRDPConsole, etc. The result is
that every time we want to add support for a new console, we need to introduce
a new public API. A far better solution is to have only one API, get_console,
which can be used for obtaining access to all types of consoles.

Use Cases
----------

As a Nova developer I want to add support for a new console type and I don't
want to add more clutter to the public API.

Project Priority
-----------------

None

Proposed change
===============

The proposal is to introduce a single public API for getting console access and
deprecate all of the current public APIs that we have. The implementation will
inspect the request and will call the relevant get_XXX_console of the
ComputeManager.

Alternatives
------------

The alternative is to keep adding public APIs for each new console type which
is not really desired.

Data model impact
-----------------

None

REST API impact
---------------

The new API will be exposed with API microversion and will have the following
definition:

Request::

    POST /servers/<uuid>/remote-consoles
    {
        "remote_console": {
            "protocol": ["vnc"|"rdp"|"serial"|"spice"],
            "type": ["novnc"|"xpvnc"|"rdp-html5"|"spice-html5"|"serial"]
        }
    }

The 'type' parameter in the request is optional and should be used when the
chosen protocol supports multiple connection types.

Response::

    200 OK
    {
        "remote_console": {
            "url": string,
            "protocol": ["vnc"|"rdp"|"serial"|"spice"],
            "type": ["novnc"|"xpvnc"|"rdp-html5"|"spice-html5"|"serial"]
        }
    }

Some of failure scenarios and their corresponding error code include:
* wrong values for protocol/type in the request - "400 Bad Request"
* the instance is not yet ready - "409 Conflict"
* the virt driver doesn't support this console type - "501 Not Implemented"

The old API 'os-getVNCConsole', 'os-getSPICEConsole', 'os-getSerialConsole'
and 'os-getRDPConsole' will be removed at the microversion which new API
added.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

There will be a new 'console-get' subcommand for the Nova CLI that will support
all of the console types.

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
  rgerganov

Work Items
----------

There is already a patch which implements the blueprint which didn't land in
Kilo: https://review.openstack.org/#/c/148509/

Dependencies
============

None

Testing
=======

A new test will be added to tempest which will exercise the new API.

Documentation Impact
====================

The new API should be documented and we should encourage users to use this
instead of the old APIs which will be deprecated.

References
==========

None
