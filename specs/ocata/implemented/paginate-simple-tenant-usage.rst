..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Simple tenant usage pagination
==========================================

https://blueprints.launchpad.net/nova/+spec/paginate-simple-tenant-usage

The blueprint aims to add optional `limit` and `marker` parameters
to the GET /os-simple-tenant-usage endpoints.

::

    GET /os-simple-tenant-usage?limit={limit}&marker={instance_uuid}
    GET /os-simple-tenant-usage/{tenant_id}?limit={limit}&marker={instance_uuid}

Problem description
===================

The simple tenant usage API can return extremely large amounts of data and
provides no way to paginate the results. Because the API does not use the
pagination code, it doesn't even respect the "max results" sanity limit.
Because it can query a ton of data, it also causes the api workers to inflate
their memory footprint to the size of the DB result set, which is large.
Since horizon queries this by default, most users are affected unless their
ops team is extremely diligent about purging deleted instances (which are
returned by the API by design).

Use Cases
---------

Horizon uses these endpoints to display server usage.

Proposed change
===============

Add an API microversion that allows for pagination of the simple tenant usage
results using Nova'a existing approach to pagination (optional `limit` and
`marker` query parameters).

Pagination would be made available for both the "all tenants" (`index`) and
"specific tenant" (`show`) cases.

::

    List Tenant Usage For All Tenants
    /os-simple-tenant-usage?limit={limit}&marker={instance_uuid}

    Show Usage Details For Tenant
    /os-simple-tenant-usage/{tenant_id}?limit={limit}&marker={instance_uuid}

Currently, the simple tenant usage endpoints include aggregate data (like
`total_hours`) which is the sum of the `hours` for each instance in a
specific time window, grouped by tenant.

.. note:: For clarity, I've removed all other usage response fields from the
          examples.


::

    GET /os-simple-tenant-usage?detailed=1

    {
        "tenant_usages": [
            {
                "server_usages": [
                    {
                        "instance_id": "instance-uuid-1",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    },
                    {
                        "instance_id": "instance-uuid-2",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    },
                    {
                        "instance_id": "instance-uuid-3",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    }
                ],
                "tenant_id": "tenant-uuid-1",
                "total_hours": 3
            },
            {
                "server_usages": [
                    {
                        "instance_id": "instance-uuid-4",
                        "tenant_id": "tenant-uuid-2",
                        "hours": 1
                    }
                ],
                "tenant_id": "tenant-uuid-2",
                "total_hours": 1
            }
        ]
    }

Once paging is introduced, API consumers would need to stitch together the
aggregate results if they still want totals for all instances in a specific
time window, grouped by tenant.

For example, that same data would be returned as follows if the `limit` query
parameter was set to 2. Note that the totals on the first page of results
only reflect 2 of the 3 instances for tenant-uuid-1, and that the
tenant-uuid-1 totals on the second page of results only reflect the remaining
instance for tenant-uuid-1. API consumers would need to manually add these
totals back up if they want the totals to reflect all 3 instances for
tenant-uuid-1.

::

    /os-simple-tenant-usage?detailed=1&limit=2

    {
        "tenant_usages": [
            {
                "server_usages": [
                    {
                        "instance_id": "instance-uuid-1",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    },
                    {
                        "instance_id": "instance-uuid-2",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    }
                ],
                "tenant_id": "tenant-uuid-1",
                "total_hours": 2
            },
        ],
        "tenant_usages_links": [
            {
                "href": "/os-simple-tenant-usage?detailed=1&limit=2&marker=instance-uuid-2",
                "rel": "next"
            }
        ]
    }

::

    /os-simple-tenant-usage?detailed=1&limit=2&marker=instance-uuid-2

    {
        "tenant_usages": [
            {
                "server_usages": [
                    {
                        "instance_id": "instance-uuid-3",
                        "tenant_id": "tenant-uuid-1",
                        "hours": 1
                    }
                ],
                "tenant_id": "tenant-uuid-1",
                "total_hours": 1
            },
            {
                "server_usages": [
                    {
                        "instance_id": "instance-uuid-4",
                        "tenant_id": "tenant-uuid-2",
                        "hours": 1
                    }
                ],
                "tenant_id": "tenant-uuid-2",
                "total_hours": 1
            },
        ]
    }

Paging is done on the inner `server_usages` list. The `marker` is the last
instance UUID in the `server_usages` list from the previous page.

The simple tenant usage endpoints will also include the conventional "next"
links: `tenant_usages_links` in the case of `index` and `tenant_usage_links`
in the `show` case.

::

    /os-simple-tenant-usage?detailed=1&limit={limit}

    {
        "tenant_usages": [
            {
                "server_usages": [
                   ...
                ],
                "tenant_id": "{tenant_id}",
            }
        ],
        "tenant_usages_links": [
            {
                "href": "/os-simple-tenant-usage?detailed=1&limit={limit}&marker={marker}",
                "rel": "next"
            }
        ]
    }

::

    /os-simple-tenant-usage/{tenant_id}?detailed=1&limit={limit}

    {
        "tenant_usage": {
            "server_usages": [
               ...
            ]
        },
        "tenant_usage_links": [
            {
                "href": "os-simple-tenant-usage/{tenant_id}?limit={limit}&marker={marker}",
                "rel": "next"
            }
        ]
    }


.. note:: For clarity, I omitted the additional query parameters (like start
          & end) from the next links, but they need to be preserved. An actual
          next link would look more like this.


::

    "tenant_usages_links": [
        {
            "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/os-simple-tenant-usage?detailed=1&end=2016-10-12+18%3A22%3A04.868106&limit=1&marker=1f1deceb-17b5-4c04-84c7-e0d4499c8fe0&start=2016-10-12+18%3A22%3A04.868106",
            "rel": "next"
        }
    ]

Alternatives
------------

None

Data model impact
-----------------

Sorting will need to be added to the query that returns the instances in the
`server_usages` list. The sort order will need to be deterministic across
cell databases, and we may need to modify/add a new database index as a
result.


REST API impact
---------------

Add an API microversion that allows for pagination of the simple tenant usage
results using optional `limit` and `marker` query parameters. If `limit`
isn't provided, it will default to `CONF.osapi_max_limit` which is currently
1000.

::

    GET /os-simple-tenant-usage?limit={limit}&marker={instance_uuid}
    GET /os-simple-tenant-usage/{tenant_id}?limit={limit}&marker={instance_uuid}

Older versions of the `os-simple-tenant-usage` endpoints will not accept these
new paging query parameters, but they will start to silently limit by
`CONF.osapi_max_limit` to encourage the adoption of this new microversion, and
circumvent the existing possibility DoS-like usage requests on systems with
thousands of instances.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Also change the python-novaclient to accept `limit` and `marker` options for
simple tenant usage.

Performance Impact
------------------

Horizon consumes these API endpoints which are currently slow with a large
memory profile when there are a lot of instances.

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
  diana_clarke

Other contributors:
  None

Work Items
----------

- Create a new API microversion for simple tenant usage pagination.
- Update python-novaclient to be able to take advantage of these changes.
- Communicate these changes to the Horizon team.


Dependencies
============

None

Testing
=======

Needs functional and unit tests.

Documentation Impact
====================

Update the "Usage reports" section of the compute api-ref to mention the new
microversion and optional `limit` and `marker` query parameters.

References
==========

Bug that describes the problem:

[1] https://bugs.launchpad.net/nova/+bug/1421471

Proof of concept (nova & python-novaclient):

[2] https://review.openstack.org/#/c/386093/

[3] https://review.openstack.org/#/c/394653/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
