..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Filter Allocation Candidates by Provider Tree
=============================================

https://blueprints.launchpad.net/nova/+spec/alloc-candidates-in-tree

This blueprint proposes to support for filtering allocation candidates
by provider tree.

Problem description
===================

Placement currently supports ``in_tree`` query parameters for the
``GET /resource_providers`` endpoints. This parameter is a string representing
a resource provider uuid, and when this is present, the response is limited to
resource providers within the same tree of the provider indicated by the uuid.
See `Nested Resource Providers`_ spec for details.

However, ``GET /allocation_candidates`` doesn't support the ``in_tree`` query
parameter to filter the allocation candidates by resource tree. This results
in inefficient post-processing in some cases where the caller has already
selected the resource provider tree before calling that API.

Use Cases
---------

This feature is useful when the caller of the ``GET /allocation_candidates``
has already picked up resource providers they want to use.

As described in the `Bug#1777591`_, when an admin operator creates an instance
on a specific host, nova now explicitly sets no limitation for getting
allocation candidates to prevent placement from filtering out the
pre-determined target resource provider by the random limitation. (For the
limitation feature of the API, see the `Limiting Allocation Candidates`_
spec)

Instead of issuing the inefficient request to placement, we can use ``in_tree``
query with the pre-determined target host resource provider uuid calling the
``GET /allocation_candidates`` API.

We would solve the same problem for cases of live migration to a specified
host and rebuilding an instance on the same host.

Proposed change
===============

The ``GET /allocation_candidates`` call will accept a new query parameter
``in_tree``. This parameter is a string representing a resource provider uuid.
When this is present, the only resource providers returned will be those in the
same tree with the given resource provider.

The numbered syntax ``in_tree<N>`` is also supported. This restricts providers
satisfying the Nth granular request group to the tree of the specified
provider. This may be redundant with other ``in_tree<N>`` values specified in
other groups (including the unnumbered group). However, it can be useful in
cases where a specific resource (e.g. DISK_GB) needs to come from a specific
sharing provider (e.g. shared storage).

In the following environments,

.. code::

         +-----------------------+          +-----------------------+
         | sharing storage (ss1) |          | sharing storage (ss2) |
         |   DISK_GB: 1000       |          |   DISK_GB: 1000       |
         +-----------+-----------+          +-----------+-----------+
                     |                                  |
                     +-----------------+----------------+
                                       |
                                       | Shared via an aggregate
                     +-----------------+----------------+
                     |                                  |
      +--------------|---------------+   +--------------|--------------+
      | +------------+-------------+ |   | +------------+------------+ |
      | | compute node (cn1)       | |   | |compute node (cn2)       | |
      | |   DISK_GB: 1000          | |   | |  DISK_GB: 1000          | |
      | +-----+-------------+------+ |   | +----+-------------+------+ |
      |       | nested      | nested |   |      | nested      | nested |
      | +-----+------+ +----+------+ |   | +----+------+ +----+------+ |
      | | numa1_1    | | numa1_2   | |   | | numa2_1   | | numa2_2   | |
      | |   VCPU: 4  | |   VCPU: 4 | |   | |  VCPU: 4  | |   VCPU: 4 | |
      | +------------+ +-----------+ |   | +-----------+ +-----------+ |
      +------------------------------+   +-----------------------------+

for example::

    GET /allocation_candidates?resources=VCPU:1,DISK_GB:50&in_tree={cn1_uuid}

will return 2 combinations of allocation candidates.

result A::

    1. numa1_1 (VCPU) + cn1 (DISK_GB)
    2. numa1_2 (VCPU) + cn1 (DISK_GB)

The specified tree can be a non-root provider::

    GET /allocation_candidates?resources=VCPU:1,DISK_GB:50&in_tree={numa1_1_uuid}

will return the same result.

result B::

    1. numa1_1 (VCPU) + cn1 (DISK_GB)
    2. numa1_2 (VCPU) + cn1 (DISK_GB)

When you want to have ``VCPU`` from ``cn1`` and ``DISK_GB`` from wherever,
the request may look like::

    GET /allocation_candidates?resources=VCPU:1&in_tree={cn1_uuid}
                              &resources1=DISK_GB:10

which will return the sharing providers as well.

result C::

    1. numa1_1 (VCPU) + cn1 (DISK_GB)
    2. numa1_2 (VCPU) + cn1 (DISK_GB)
    3. numa1_1 (VCPU) + ss1 (DISK_GB)
    4. numa1_2 (VCPU) + ss1 (DISK_GB)
    5. numa1_1 (VCPU) + ss2 (DISK_GB)
    6. numa1_2 (VCPU) + ss2 (DISK_GB)

When you want to have ``VCPU`` from wherever and ``DISK_GB`` from ``ss1``,
the request may look like::

    GET: /allocation_candidates?resources=VCPU:1
                               &resources1=DISK_GB:10&in_tree1={ss1_uuid}

which will stick to the first sharing provider for DISK_GB.

result D::

    1. numa1_1 (VCPU) + ss1 (DISK_GB)
    2. numa1_2 (VCPU) + ss1 (DISK_GB)
    3. numa2_1 (VCPU) + ss1 (DISK_GB)
    4. numa2_2 (VCPU) + ss1 (DISK_GB)

When you want to have ``VCPU`` from ``cn1`` and ``DISK_GB`` from ``ss1``,
the request may look like::

    GET: /allocation_candidates?resources1=VCPU:1&in_tree1={cn1_uuid}
                               &resources2=DISK_GB:10&in_tree2={ss1_uuid}
                               &group_policy=isolate

which will return only 2 candidates.

result E::

    1. numa1_1 (VCPU) + ss1 (DISK_GB)
    2. numa1_2 (VCPU) + ss1 (DISK_GB)


Alternatives
------------

Alternative 1:

We could mitigate the restriction to include sharing providers assuming that
they are in specified non-sharing tree that shares them. For example, we could
change result A to return::

    1. numa1_1 (VCPU) + cn1 (DISK_GB)
    2. numa1_2 (VCPU) + cn1 (DISK_GB)
    3. numa1_1 (VCPU) + ss1 (DISK_GB)
    4. numa1_2 (VCPU) + ss1 (DISK_GB)
    5. numa1_1 (VCPU) + ss2 (DISK_GB)
    6. numa1_2 (VCPU) + ss2 (DISK_GB)

This is possible if we assume that ``ss1`` and ``ss2`` are in "an expanded
concept of a tree" of ``cn1``, but we don't take this way because we can get
the same result using the granular request. Different result for a different
request means we support more use cases than the same result for a different
request.

Alternative 2:

In result B, we could exclude ``numa1_2`` resource provider (the second
candidate), but we don't take this way for the following reason:
It is not consistent with the existing ``in_tree`` behavior in
``GET /resource_providers``. The inconsistency despite of the same queryparam
name could confuse users. If we need this behaivor, that would be something
like ``subtree`` queryparam which should be symmetrically implemented to
``GET /resource_providers`` as well. This is already proposed in
`Support subtree filter for GET /resource_providers`_ spec.

Data model impact
-----------------

None.

REST API impact
---------------

A new microversion will be created to add the ``in_tree`` parameter to
``GET /allocation_candidates`` API.

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

If the callers of the ``GET /allocation_candidates`` has already picked up
resource providers they want to use, they would get improved performance
using this new ``in_tree`` query because we don't need to get all the
candidates from the database.

Other deployer impact
---------------------

This feature enables us to develop efficient query in nova for cases that is
described in the `Use Cases`_ section.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Tetsuro Nakamura (nakamura.tetsuro@lab.ntt.co.jp)

Work Items
----------

* Update the ``AllocationCandidates.get_by_requests`` method to change the
  database queries to filter on the specified provider tree.
* Update the placement API handlers for ``GET /allocation_candidates`` in
  a new microversion to pass the new ``in_tree`` parameter to the methods
  changed in the steps above, including input validation adjustments.
* Add functional tests of the modified database queries.
* Add gabbi tests that express the new queries, both successful queries and
  those that should cause a 400 response.
* Release note for the API change.
* Update the microversion documents to indicate the new version.
* Update placement-api-ref to show the new query handling.

Dependencies
============

None.

Testing
=======

Normal functional and unit testing.

Documentation Impact
====================

Document the REST API microversion in the appropriate reference docs.

References
==========

* `Nested Resource Providers`_ spec
* `Bug#1777591`_ reported in the launchpad
* `Limiting Allocation Candidates`_ spec

.. _`Nested Resource Providers`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html
.. _`Bug#1777591`: https://bugs.launchpad.net/nova/+bug/1777591
.. _`Limiting Allocation Candidates`: https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/allocation-candidates-limit.html
.. _`Support subtree filter for GET /resource_providers`: https://review.openstack.org/#/c/595236/
