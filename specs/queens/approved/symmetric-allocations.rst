..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Symmetric GET and PUT of allocations in Placement
=================================================

https://blueprints.launchpad.net/nova/+spec/symmetric-allocations

When support for placement allocations was added on the nova-side (initially in
the resource tracker) the formats of the representations used in GET and PUT
diverged. GET took on a dict oriented style, and PUT a list oriented style.
Since then this disparity has caused confusion. A dict style is considered
easier to work with, so a new microversion will be created to support that
form.

Problem description
===================

The `Generic Resource Pools`_ specification describes the representations used
in the response and request bodies of ``GET`` and ``PUT
/allocations/{consumer_uuid}``. Not only are these not the same (usually
desirable) they are fundamentally different: one is based on a dict, the other
uses items in a list.

This came about because when support for ``GET`` was added in change
I69fbc4e9834ec6dc80dacf43f8fd9dc6ec139006_ it was built to address the specific
needs of the caller, where inspecting the data by key was most useful. Since
then this format has been declared the most usable and it has been discovered
that retrieving allocations, manipulating them, and sending them back is
relatively common. So we should fix it.

This problem was initially registered in bug 1708204_ and has become more
relevant with the desire to resolve the post-allocations_ blueprint, which
expresses a preference to use the dict-based format, and we should be
consistent.

Use Cases
---------

As a user of the Placement API, I would like representations to be consistent
for read and write, and formatted for most effective use.

Proposed change
===============

The JSON schema for the request body to ``PUT /allocations/{consumer_uuid}``
will be versioned (in a new Placement service microversion) to expect data to
be input in the same form as retrieved from ``GET
/allocations/{consumer_uuid}``. The format is described below.

Because writing allocations requires `project_id` and `user_id` information,
the response body of ``GET /allocations/{consumer_uuid}`` will be extended to
include those fields.

Similarly, because the response to a ``GET /allocation_candidates`` includes
an `allocation_requests` property that includes a series of JSON objects that
are designed to be opaquely sent as bodies in
``PUT /allocations/{consumer_uuid}``, the format of that response will be
updated in the same microversion to reflect the dict-based format.
See example below.

Alternatives
------------

The main alternative is to do nothing.

Data model impact
-----------------

None.

REST API impact
---------------

The existing JSON schema for the request body to ``PUT
/allocations/{consumer_uuid}`` will be updated to expect data in the following
form:

.. code-block:: javascript

    {
        "allocations": {
            "RP_UUID_1": {
                "generation": GENERATION,
                "resources": {
                    "DISK_GB": 4,
                    "VCPU": 2
                }
            },
            "RP_UUID_2": {
                "generation": GENERATION,
                "resources": {
                    "DISK_GB": 6,
                    "VCPU": 3
                }
           }
         },
         "project_id": "PROJECT_ID",
         "user_id": "USER_ID"
    }

``generation`` is optional and if present will be ignored. It is allowed to
preserve symmetry. To further preserve symmetry the response to a ``GET`` on
the same URL will include the ``project_id`` and ``user_id`` fields.

The response body for ``GET /allocation_candidates`` will be updated so that
the ``allocation_requests`` object will change from the following list-based
format (the surrounding JSON, including ``provider summaries`` has been
excluded, see the `list allocation candidates`_ docs for more detail on the
full response body):

.. code-block:: javascript

    "allocation_requests": [
        {
            "allocations": [
                {
                    "resource_provider": {
                        "uuid": "RP_UUID_1"
                    },
                    "resources": {
                        "MEMORY_MB": 512
                    }
                },
                {
                    "resource_provider": {
                        "uuid": "RP_UUID_2"
                    },
                    "resources": {
                        "DISK_GB": 1024
                    }
                }
            ]
        },
        {
            "allocations": [
                {
                    "resource_provider": {
                        "uuid": "RP_UUID_3"
                    },
                    "resources": {
                        "MEMORY_MB": 512,
                        "DISK_GB": 1024
                    }
                }
            ]
        }
    ],

to the new dict based format:

.. code-block:: javascript

    "allocation_requests": [
        {
            "allocations": {
                "RP_UUID_1": {
                    "resources": {
                        "MEMORY_MB": 512
                    }
                },
                "RP_UUID_2": {
                    "resources": {
                        "DISK_GB": 1024
                    }
                }
            }
        },
        {
            "allocations": {
                "RP_UUID_3": {
                    "resources": {
                        "MEMORY_MB": 512,
                        "DISK_GB": 1024
                    }
                }
            }
        }
    ],

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

Developers will now have a choice of formats (by specifying the appropriate
microversion) when sending allocations to the Placement service.

At some point, either during the implementation of this spec, or later as
people find it worth doing, the microversion used when sending allocations
from the scheduler report client should be updated.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  you

Work Items
----------

* Write JSON schema representing the desired format.
* Add support for a new microversion which validates ``PUT
  /allocations/{consumer_uuid}`` bodies against that new schema.
* Modify ``GET /allocations/{consumer_uuid}`` to include `project_id`
  and `user_id`.
* Modify ``GET /allocation_candidates`` to send the dict-based format.
* Integrate processing that data to compose a call to
  ``AllocationList.create_all()``.
* Add gabbi tests exercising the new microversion.
* Add placement-api-ref documentation for the new microversion.

Dependencies
============

None.

Testing
=======

Care should be taken to insure that tests cover the boundary cases of
microversion handling.

Documentation Impact
====================

The main documentation impact is in the `placement api-ref`_ where a new
microversion will need to be described for
``PUT /allocations/{consumer_uuid}``.

References
==========

* Bug 1708204_.
* post-allocations_ blueprint.
* `placement api-ref`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced

.. _Generic Resource Pools: http://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/generic-resource-pools.html#put-allocations-consumer-uuid
.. _I69fbc4e9834ec6dc80dacf43f8fd9dc6ec139006: https://review.openstack.org/#/q/I69fbc4e9834ec6dc80dacf43f8fd9dc6ec139006
.. _1708204: https://bugs.launchpad.net/nova/+bug/1708204
.. _post-allocations: https://blueprints.launchpad.net/nova/+spec/post-allocations
.. _placement api-ref: https://developer.openstack.org/api-ref/placement/
.. _list allocation candidates: https://developer.openstack.org/api-ref/placement/#allocation-candidates
