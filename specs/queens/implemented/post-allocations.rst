..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
POST Multiple Allocations
=========================

https://blueprints.launchpad.net/nova/+spec/post-allocations

With `migration allocations`_ we plan to have the resources claimed by a
move-like operation represented by two allocations to the placement service:
one identified by the instance uuid, the other by a migration uuid. This can
currently be done by making two separate ``PUT`` requests to
``/allocations/{consumer_uuid}`` in the `Placement API`_. This can work, but
has risks as a race condition and requires two steps where logically we want
the caller to be thinking in terms of one.

Problem description
===================

One the main goals of the Placement service has been to more accurately
represent the true use of resources in the cloud and use that increased
accuracy to avoid making promises (e.g., "yes we have the resources to do this
move") that we then can't keep because something changes after the promise has
been made but before the action has been completed.

If, in the case of move operations, we attempt to make allocations in two steps
we have situations where there is a window of time (admittedly usually short,
but latency is unpredictable) where Placement's representation of reality is
not what we want it to be. If resources are scarce something else can claim
them in the gap.

In the case of a move we want, for example, to:

* change an instance claim into a migration claim by removing the instance
  claim and creating the migration claim in one request
* create the instance claim on the new destination
* if the build succeeds remove the migration claim

That first step is where we need the solution described in this document.

Use Cases
---------

As an end user or an operator I want to have reliable move operations that make
the most efficient use of resources.

Proposed change
===============

To address this requirement a new handler will be created in the `Placement
API`_ at ``POST /allocations`` which will accept a collection of allocation
requests for multiple consumers and save all of them in a single transaction,
or fail all of them if resources are not available or the allocation requests
are malformed.

Details of the various options for the request body are discussed in
:ref:`rest-api` below.

Alternatives
------------

An open question on how to implement this is related to the existing bug
about `asymmetric PUT and GET`_ for ``/allocations/{consumer_uuid}``. We can
consider either a dict or list-based representation for ``POST``. See
:ref:`rest-api` below for examples.

There aren't really any reasonable alternatives to ``POST /allocations`` for
this use case. ``PUT`` to the same URI violates HTTP semantics. That would mean
"replace all the allocations on the system with what I've provided". Using a
different URI is hard to contemplate: ``PUT
/allocations/{consumer_uuid},{migration_uuid},{some_uuid}``. No thank you.

Data model impact
-----------------

The existing database tables are adequate. The ``project_id`` and ``user_id``
attributes currently associated with the `AllocationList`` object need to be
moved to the `Allocation` object to ensure that a collection of allocations
from multiple logical users can be handled correctly.

.. _rest-api:

REST API impact
---------------

A new handler at ``POST /allocations`` will be created, accepting an
``application/json`` body. Upon success it will return a ``204`` status code
and an empty body. Error conditions include:

* 400 Bad Request: When the JSON body does not match schema
* 400 Bad Request: When a resource provider or resource class named in the body
                   does not exist.
* 409 Conflict: When at least one of the allocations will violate Inventory
                constraints or available capacity.
* 409 Conflict: When, during the allocation process there is a resource
                provider generation mismatch (if this happens the client should
                retry). This 409 is distinguished from the previous by the
                error text in the body.

.. highlight:: javascript

The format of the body will be as follows, based on resolving the
`asymmetric PUT and GET`_ bug to align on a dict-like format::

    {
        "$INSTANCE-UUID": {
            "allocations": {
                "$TARGET_UUID": {
                    "resources": {
                        "MEMORY_MB": 1024,
                        "VCPU": 2
                    }
                },
                "$SHARED_DISK": {
                    "resources": {
                        "DISK_GB": 5
                    }
                }
            },
            project_id: "$PROJECT_ID",
            user_id: "$USER_ID"
        },
        "$MIGRATION_UUID": {
            "allocations": {
                "$SOURCE_UUID" {
                    "MEMORY_MB": 1024,
                    "VCPU": 2
                }
            },
            project_id: "$PROJECT_ID",
            user_id: "$USER_ID"
        }
    }

``$INSTANCE_UUID`` and ``$MIGRATION_UUID`` are consumer uuids. If no
allocations exist on the server for a consumer they will be created using
values in the body of the ``allocations`` key. If allocations already exist,
they will be replaced. An empty value for the ``allocations`` key will mean
that the allocations for that consumer will be removed.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

If the osc-placement plugin becomes a thing, this functionality will need to be
added there.

Performance Impact
------------------

None expected.

Other deployer impact
---------------------

None.

Developer impact
----------------

Scheduler Report Client will need to be aware of the new URI and microversion
in order to take advantage of the functionality. Users of that client, such as
the compute manager will need to be updated.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  dansmith

Work Items
----------

* Write JSONschema for the new body representation
* Add URI and handler to Placement
* Integrate with AllocationList object
* Add gabbi tests for the new microversion
* Add document of the URI to placement-api-ref


Dependencies
============

* Related to `migration allocations`_


Testing
=======

Gabbi tests will be able to cover most of the scenarios for how data will be
passed over the API. What will matter more is one the report client is using
this code making sure that functional tests are verifying the allocations end
up correct. A lot of these tests are already in place, so that's nice.


Documentation Impact
====================

placement-api-ref will need to be updated to explain the new URI.

References
==========

* `Placement API`_
* `Proof of Concept`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced

.. _migration allocations: https://blueprints.launchpad.net/nova/+spec/migration-allocations
.. _Placement API: https://developer.openstack.org/api-ref/placement/
.. _asymmetric PUT and GET: https://bugs.launchpad.net/nova/+bug/1708204
.. _Proof of Concept: https://review.openstack.org/#/c/500073/
