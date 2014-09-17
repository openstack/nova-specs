..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Return all servers during multiple create
=========================================

https://blueprints.launchpad.net/nova/+spec/return-all-servers-during-multiple-create

In this blueprint, we propose to improve the server create API in V3 by
including all of the created servers in the response instead of only the first
server. In V2, servers[0] is returned to the caller in response to a create
request that has specified min/max_count.

Problem description
===================

End users of the server create API have the ability to create multiple
instances in one batch by specifying min/max_count in the request. One reason
to use this ability is to scale up a cloud-hosted application quickly or in
response to increased load. Upon requesting multiple servers, the user needs to
know the list of servers that have been created in order to work with them. It
would be ideal to receive the list in the response for the create request.

Proposed change
===============

In order to provide the end user with the list of created servers most
efficiently, we propose to change the server create API response in V3 from
returning only one server to returning a list of servers. In the case when the
end user has requested creation of just one server, a list containing one
server will be returned.

Alternatives
------------

Callers can work around in V2 by specifying return_reservation_id=True in the
request to receive a reservation ID which they can use to obtain the list of
servers. This is also currently possible in V3, but it requires an additional
API call to get the server list.

Data model impact
-----------------

None

REST API impact
---------------

V3 API specification:

 * Description: Create one or more servers

 * Method type: POST

 * Normal http response code: 202

 * Expected error http response codes:

  * 400: Invalid request parameter, image/flavor not found

  * 409: Port in use, no unique match

  * 413: Quota or port limit exceeded

 * URL: v3/servers

 * Example JSON request (no change)::

    {
        "server": {
            "name": "server-test-1",
            "image_ref": "b5660a6e-4b46-4be3-9707-6b47221b454f",
            "flavor_ref": "2",
            "max_count": 2,
            "min_count": 2
    }

 * Example JSON response (new format)::

    {
        "servers": [
            {
                "admin_password": "qpYU66rKxmnK",
                "id": "215d1109-216d-48c3-af8e-998bb9bc3ca0",
                "links": [
                    {
                        "href": "http://openstack.example.com/v3/servers/<id>",
                        "rel": "self"
                    },
                    {
                        "href": "http://openstack.example.com/servers/<id>",
                        "rel": "bookmark"
                    }
                ]
            },
            {
                "admin_password": "wfksH3GTTseP",
                "id": "440cf918-3ee0-4143-b289-f63e1d2000e6",
                "links": [
                    {
                        "href": "http://openstack.example.com/v3/servers/<id>",
                        "rel": "self"
                    },
                    {
                        "href": "http://openstack.example.com/servers/<id>",
                        "rel": "bookmark"
                    }
                ]
            }
        ]
    }

 * Partial JSON response schema definition to show change::

    create = {
        'type': 'object',
        'properties': {
            'servers': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties: {
                        'admin_password': {type': 'string'},
                        'id': {'type': 'string'},
                        'links': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'href': {'type': 'string'},
                                    'rel': {'type': 'string'}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The python-novaclient will have to be changed to handle the list of servers in
the V3 API server create response and show the list to the user.

Performance Impact
------------------

For a server create API request for multiple servers, instead of returning only
the first server, all of the created server objects must be serialized and
returned in the response instead of just the first one.

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
  melwitt

Other contributors:
  None

Work Items
----------

 * Change the V3 API response for server create to return a list of instances.

 * Update tests in tempest to handle the changed response.

Dependencies
============

This blueprint is related to the tasks API blueprint [1] because it needs to
interact with how tasks will work in V3. Initial comments on this interaction
are available in the original review [2].

[1] https://blueprints.launchpad.net/nova/+spec/instance-tasks-api

[2] https://review.openstack.org/#/c/54214/

Testing
=======

Tempest tests must be updated to accept the changed server create API
response format. Tempest tests already exercise the various server creation
scenarios, but the response format has changed for V3.

Documentation Impact
====================

The changed REST API response for server create, as represented by the
jsonschema definition above, will need to be documented. The changed API
response will be available as API samples generated from testing.

References
==========

None
