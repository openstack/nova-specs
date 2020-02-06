..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Use in_tree getting allocation candidates
=========================================

https://blueprints.launchpad.net/nova/+spec/use-placement-in-tree

In Stein, we introduced ``in_tree=<rp_uuid>`` parameter in placement for the
``GET /allocation_candidates`` endpoints, which limits the response to
resource providers within the same tree of the specified resource provider.
(See the `Filter Allocation Candidates by Provider Tree`_ spec for details)

This spec proposes to use this parameter for optimization when we create or
move instances and the target host is already picked before asking to the
scheduler.

Problem description
===================

In create and move instance operations, there are cases where the target host
is already picked before calling the scheduler. Even in such cases, nova
retrieves all the possible candidates from placement. This is inefficient and
can cause, for example, `Bug#1777591`_ filtering out the pre-determined target
resource provider by `Limiting Allocation Candidates`_ feature in placement.

Use Cases
---------

* Creating an instance to a host specified by operator
* Migrating an instance to a host specified by operator
* Live-migrating an instance to a host specified by operator without forcing
* Evacuating an instance to a host specified by operator without forcing
* Rebuilding an instance in the same host with a new image.

Proposed change
===============

Instead of issuing the inefficient request to placement, we will use
``in_tree`` query with the pre-determined target host resource provider
uuid calling the ``GET /allocation_candidates`` API.

Alternatives
------------

Disable the `Limiting Allocation Candidates`_ feature calling placement.
This is actually what we have now as workaround, but not efficient.
(See the `unlimiting allocation candidates`_ patch for details)

Data model impact
-----------------

The ``RequestGroup`` object will have a new field, ``in_tree`` in the new
version.

REST API impact
---------------

N/A

Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

N/A

Performance Impact
------------------

The performance would be improved because we don't need to get all
the candidates.

Other deployer impact
---------------------

This spec is proposed on the assumption that the placement code in nova
repository will be removed in Train release and that all the deployers will
use the extracted placement from Train release. Note that ``in_tree``
queryparam to placement is **not** supported in placement hosted in nova.

Developer impact
----------------

N/A

Upgrade impact
--------------

We will have a minimum required placement API check in the
`nova-status upgrade checks` command.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tetsuro0907

Work Items
----------

* Changes to support the new feature

  * Add ``in_tree`` field in ``RequestGroup`` object implementing
    the translation into the placement query parameter
  * Add a database query in the scheduler to translate
    ``RequestSpec.force_hosts/force_nodes`` and
    ``RequestSpec.requested_destination`` to the compute node uuid
    and set it to the new ``RequestGroup.in_tree`` field

* Revert the workaround in `unlimiting allocation candidates`_ patch

Dependencies
============

The `Filter Allocation Candidates by Provider Tree`_ spec, but this has been
completed in Stein.

Testing
=======

Functional tests will be added to ensure the server operations described
in the `Use Cases`_ section.

Documentation Impact
====================

N/A

References
==========

* `Filter Allocation Candidates by Provider Tree`_ spec
* `Limiting Allocation Candidates`_ spec
* `Bug#1777591`_ reported in the launchpad
* `unlimiting allocation candidates`_ patch

.. _`Filter Allocation Candidates by Provider Tree`: https://specs.openstack.org/openstack/nova-specs/specs/stein/implemented/alloc-candidates-in-tree.html
.. _`Bug#1777591`: https://bugs.launchpad.net/nova/+bug/1777591
.. _`Limiting Allocation Candidates`: https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/allocation-candidates-limit.html
.. _`unlimiting allocation candidates`: https://review.openstack.org/#/c/576693/
