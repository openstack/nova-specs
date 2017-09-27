..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Instance Flavor REST API
==========================================

https://blueprints.launchpad.net/nova/+spec/instance-flavor-api

Replace the existing ``flavor`` property in the ``server`` representation to
include most of the flavor information stored with the instance, instead of the
current flavor ID and link.

Problem description
===================

The REST representation of our ``server`` resource includes links to other
resources (flavor and image) used to create that server. These link to global
REST representations ``/v2.1/flavor/{id}``.

However, flavors can be deleted so this resource may no longer be available.
In addition, flavor extra_specs can be modified, so the current extra_specs may
no longer represent what was used to boot the instance.

Internal to Nova we store the flavor information with
an instance when we first create it, to protect ourselves from just
such deletes/modifications.

In order to provide these same guarantees to the users, we should
output the flavor information in all of our server representations.

Use Cases
---------

As a user I want to always be able to get information about the instance
memory, allocated disk, flavor extra_specs, and other metadata from the API.

Proposed change
===============

A new microversion is proposed which modifies the following calls::

  GET /v2.1/servers/detail
  GET /v2.1/servers/{server_id}
  POST /v2.1/servers/{server_id}/action (rebuild action)
  PUT /v2.1/servers/{server_id}

In all cases the existing ``flavor`` property value will be replaced by a dict
containing most of the information visible when displaying the flavor, with a
nested dict for the extra_specs.

The following fields from the flavor response will be removed:

* links - as a sub resource persistent links seem less important
* id - we choose not to expose the id for the flavor since it could be stale
* os-flavor-access:is_public - irrelevant, this is scope local to the
  instance
* OS-FLV-DISABLED:disabled - irrelevant, this is scope local to the
  instance
* rxtx_factor - useful only for nova-networks, is being deprecated/removed in
  the near future

In any cases where flavor information had odd keys because it was considered
an extension, we will normalize those keys. For instance
``OS-FLV-EXT-DATA:ephemeral`` would become ``ephemeral``.

Finally, the flavor ``name`` field will be displayed under the
``original_name`` key.  There is a (good) chance that it is stale, but it was
determined to be useful for end-users.

The visibility of the flavor data within the server resource will be controlled
by the same policy rules as are used for displaying the flavor extra_specs when
displaying flavor details.

Alternatives
------------

* Not allow the deletion of in-use flavors or deletion/modification of in-use
  flavor extra_specs. This has impacts on Cells v2, which we would like to
  avoid.

* Add a new flavor subresource as per the original version of this spec.

Data model impact
-----------------

None.


REST API impact
---------------

* URLs:

  * /v2.1/servers/{server_id}

* Request Methods:

  * GET
  * PUT

* Original JSON response::

    {
        "server": {
            "flavor": {
                "id": "1860e252-6851-439b-95f9-873b8d5f880d",
                "links": [
                    {
                        "href": "http://192.168.204.2:18774/9d4087df61314635a096a86a28aac6f8/flavors/1860e252-6851-439b-95f9-873b8d5f880d",
                        "rel": "bookmark"
                    }
                ]
            },
            <other stuff>
        }
    }

* Proposed JSON response::

    {
        "server": {
            "flavor": {
                "disk": 1,
                "ephemeral": 0,
                "ram": 512,
                "swap": "",
                "vcpus": 1,
                "original_name": "m1.small",
                "extra_specs": {
                    "hw:cpu_model": "SandyBridge",
                    "hw:mem_page_size": "2048",
                    "hw:cpu_policy": "dedicated"
                }
            },
            <other stuff>
        }
    }




* URL:

 * /v2.1/servers/detail

* Request Method:

  * GET

* Original JSON response::

    {
        "servers": [
            {
                "flavor": {
                    "id": "1860e252-6851-439b-95f9-873b8d5f880d",
                    "links": [
                        {
                            "href": "http://192.168.204.2:18774/9d4087df61314635a096a86a28aac6f8/flavors/1860e252-6851-439b-95f9-873b8d5f880d",
                            "rel": "bookmark"
                        }
                    ]
                },
                <other stuff>
            }
        ]
    }

* Proposed JSON response::

    {
        "servers": [
            {
                "flavor": {
                    "disk": 1,
                    "ephemeral": 0,
                    "ram": 512,
                    "swap": "",
                    "vcpus": 1,
                    "original_name": "m1.small",
                    "extra_specs": {
                        "hw:cpu_model": "SandyBridge",
                        "hw:mem_page_size": "2048",
                        "hw:cpu_policy": "dedicated"
                    }
                },
                <other stuff>
            }
        ]
    }



* URL:

 * /v2.1/servers/{server_id}/action (rebuild action)

* Request Method:

  * POST

* Original JSON response::

    {
        "server": {
            "flavor": {
                "id": "1860e252-6851-439b-95f9-873b8d5f880d",
                "links": [
                    {
                        "href": "http://192.168.204.2:18774/9d4087df61314635a096a86a28aac6f8/flavors/1860e252-6851-439b-95f9-873b8d5f880d",
                        "rel": "bookmark"
                    }
                ]
            },
            <other stuff>
        }
    }

* Proposed JSON response::

    {
        "server": {
            "flavor": {
                "disk": 1,
                "ephemeral": 0,
                "ram": 512,
                "swap": "",
                "vcpus": 1,
                "original_name": "m1.small",
                "extra_specs": {
                    "hw:cpu_model": "SandyBridge",
                    "hw:mem_page_size": "2048",
                    "hw:cpu_policy": "dedicated"
                }
            },
            <other stuff>
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

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

Anyone that currently consumes flavor information may want to adjust
to this new model.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Chris Friesen (cfriesen)

Work Items
----------

* Add the microversion changes to the APIs outlined in the
  `Proposed Change`_ section.
* Unit tests and functional api-samples tests.
* Tempest changes for the microversion server response schema change.

Dependencies
============

None


Testing
=======

Testing will be done in tree with samples / functional testing.

Tempest will most likely need to be updated to adjust the `server response
validation schema`_ for the new microversion.

.. _server response validation schema: http://git.openstack.org/cgit/openstack/tempest/tree/tempest/lib/api_schema/response/compute/v2_1/servers.py?h=15.0.0#n97


Documentation Impact
====================

API documentation will need to be updated.

References
==========

The original approach was to use a new subresource.  More recently an IRC
discussion revived the concept but concensus emerged about directly embedding
the information in the server representation.

Logs of the IRC chat are available at:
http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2017-02-09.log.html

This was also discussed at the Pike PTG:
http://lists.openstack.org/pipermail/openstack-dev/2017-March/113171.html
