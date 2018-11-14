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
When this is present, the response of the allocation candidates is limited to
only allocation requests where at least one resource provider in the specified
tree is involved.

In the following environments,

.. code::

                           +-----------------------+
                           | sharing storage (ss1) |
                           |   DISK_GB: 1000       |
                           +-----------+-----------+
                                       | Shared via an aggregate
                     +-----------------+----------------+
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

would return 4 combinations of allocation candidates.

1. numa1_1 (VCPU) + cn1 (DISK_GB)
2. numa1_2 (VCPU) + cn1 (DISK_GB)
3. numa1_1 (VCPU) + ss1 (DISK_GB)
4. numa1_2 (VCPU) + ss1 (DISK_GB)

Note that candidates number 3 and 4 have "ss1", which is out of the specified
tree. They are not excluded because candidates number 3 and 4 have at least
one provider (numa1_1 and numa1_2 respectively) from the specified tree.

The specified tree can be a non-root provider::

    GET /allocation_candidates?resources=VCPU:1,DISK_GB:50&in_tree={numa1_1_uuid}

would return the same result.

Alternatives
------------

We could have other query parameters like ``resource_provider_uuid`` or
``root_provider_uuid``, but ``in_tree`` would be consistent with the similar
``GET /resource_providers`` query parameter.

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
