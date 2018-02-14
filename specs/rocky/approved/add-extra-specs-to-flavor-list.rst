..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Add extra-specs to the flavor show and detail API calls
=======================================================

https://blueprints.launchpad.net/nova/+spec/add-extra-specs-to-flavor-list

Add a new microversion to the following APIs to return also
``extra-specs`` of the flavor.

* GET /flavors/details
* GET /flavors/{flavor_id}

Problem description
===================

Currently the response of ``GET /flavors/details`` and
``GET /flavors/{flavor_id}`` does not include ``extra_spces`` field,
The users have to call ``GET /flavors/{flavor_id}/extra_specs`` again
to get the extra_specs field.

UIs and SDKs like ``shade`` could time out before all the flavors and
extra-specs are retrieved.

Use Cases
---------

UIs and SDKs can avoid doing a separate call to get ``extra_specs`` for
each flavor, also avoiding timeout when doing this.

Proposed change
===============

Add a new microversion to the following APIs to return also
``extra-specs`` of the flavor.

* GET /flavors/details
* GET /flavors/{flavor_id}

.. note:: The ``extra_specs`` field is already included in the embedded
          instance flavor in the server detail response and will be only
          visible for users that meet certain policy when microversion
          ``2.47`` was added [1].

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Following changes will be introduced in a new API microversion.

* GET /flavors/details

  Add ``extra_specs`` data to response body.

  JSON response body example::

    {
        "flavors": [
        ...
            {
                "OS-FLV-DISABLED:disabled": false,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 0,
                "os-flavor-access:is_public": true,
                "id": "1",
                "links": [
                    {
                        "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/1",
                        "rel": "self"
                    },
                    {
                        "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/1",
                        "rel": "bookmark"
                    }
                ],
                "name": "m1.tiny",
                "ram": 512,
                "swap": "",
                "vcpus": 1,
                "rxtx_factor": 1.0,
                "description": null,
                "extra_specs": {
                    "key1": "value1",
                    "key2": "value2"
                }
            },
        ...
        ]
    }


* GET /flavors/{flavor_id}

  Add ``extra_specs`` data to response body.

  JSON response body example::

    {
        "flavor": {
            "OS-FLV-DISABLED:disabled": false,
            "disk": 20,
            "OS-FLV-EXT-DATA:ephemeral": 0,
            "os-flavor-access:is_public": true,
            "id": "7",
            "links": [
                {
                    "href": "http://openstack.example.com/v2/6f70656e737461636b20342065766572/flavors/7",
                    "rel": "self"
                },
                {
                    "href": "http://openstack.example.com/6f70656e737461636b20342065766572/flavors/7",
                    "rel": "bookmark"
                }
            ],
            "name": "m1.small.description",
            "ram": 2048,
            "swap": "",
            "vcpus": 1,
            "rxtx_factor": 1.0,
            "description": "test description",
            "extra_specs": {
                    "key1": "value1",
                    "key2": "value2"
                }
        }
    }


Security impact
---------------

The visibility of the flavor extra_specs within the flavor resource
will be controlled by the same policy rules as are used for querying
the flavor extra_specs.

Notifications impact
--------------------

None

Other end user impact
---------------------

The novaclient and openstackclient are modified to add ``extra_specs`` field
to response.

Performance Impact
------------------

There will be no performance impact because when we get the flavor from
database, we always join on extra specs, it is already available but just
not exposed by API response.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Kevin Zheng

Other contributors:
  None

Work Items
----------

* Add the 'extra_specs' field to flavor APIs.
* Add the 'extra_specs' field in novaclient/openstackclient
* API docs including note of 'extra_specs' field

Dependencies
============

None

Testing
=======

Add the following tests.

* functional tests
* negative unit tests

Documentation Impact
====================

* API Reference
* CLI Reference

References
==========

* [1] https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#id42

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Proposed
