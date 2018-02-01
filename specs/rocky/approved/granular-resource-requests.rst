..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
 Granular Resource Request Syntax
==================================

https://blueprints.launchpad.net/nova/+spec/granular-resource-requests

As `Generic`_ and `Nested Resource Providers`_ begin to crystallize and be
exercised, it becomes necessary to be able to express:

* _`Requirement 1`: Requesting an allocation of a particular resource class
  with a particular set of traits, and requesting a *different* allocation of
  the *same* resource class with a *different* set of traits.

* _`Requirement 2`: Ensuring that requests of certain resources are allocated
  from the same resource provider.

* _`Requirement 3`: The ability to spread allocations of effectively-identical
  resources across multiple resource providers in situations of high
  saturation.

This specification attempts to address these requirements by way of a numbered
syntax on resource and trait keys in flavor extra_specs and the ``GET
/allocation_candidates`` `Placement API`_.

.. note:: This document uses "RP" as an abbreviation for "Resource Provider"
          throughout.

Problem description
===================

Up to this point with generic and nested resource providers and traits, it is
only possible to request a single blob of resources with a single blob of
traits.  More specifically:

* The resources can only be expressed as an integer count of a single
  resource class.  There is no way to express a second *resource_class*:*count*
  with the same resource class.
* All specified traits apply to all requested resources.  There is no way to
  apply certain traits to certain resources.
* All resources of a given resource class are allocated from the same RP.

The `Use Cases`_ below exemplify scenarios that cannot be expressed within
these restrictions.

Use Cases
---------

Consider the following hardware representation ("wiring diagram"):

.. code::

    +-----------------------------------+
    |                CN1                |
    +-+--------------+-+--------------+-+
      |     NIC1     | |     NIC2     |
      +-+---+--+---+-+ +-+---+--+---+-+
        |PF1|  |PF2|     |PF3|  |PF4|
        +-+-+  +-+-+     +-+-+  +-+-+
           \      \__   __/      /
            \        \ /        /
            |         X         |
            |    ____/ \____    |
            |   /           \   |
          +-+--+-+         +-+--+-+
          | NET1 |         | NET2 |
          +------+         +------+

Assume this is modeled in Placement as:

.. code::

    RP1 (represents PF1):
    {
        SRIOV_NET_VF=16,
        NET_EGRESS_BYTES_SEC=1250000000,  # 10Gbps
        traits: [CUSTOM_NET1, HW_NIC_ACCEL_SSL]
    }
    RP2 (represents PF2):
    {
        SRIOV_NET_VF=16,
        NET_EGRESS_BYTES_SEC=1250000000,  # 10Gbps
        traits: [CUSTOM_NET2, HW_NIC_ACCEL_SSL]
    }
    RP3 (represents PF3):
    {
        SRIOV_NET_VF=16,
        NET_EGRESS_BYTES_SEC=125000000,  # 1Gbps
        traits: [CUSTOM_NET1]
    }
    RP4 (represents PF4):
    {
        SRIOV_NET_VF=16,
        NET_EGRESS_BYTES_SEC=125000000,  # 1Gbps
        traits: [CUSTOM_NET2]
    }


Use Case 1
~~~~~~~~~~
As an Operator, I need to be able to express a boot request for an instance
with **one SR-IOV VF on physical network NET1 and a second SR-IOV VF on
physical network NET2**.

I expect the scheduler to receive the following allocation candidates:

* ``[RP1(SRIOV_NET_VF:1), RP2(SRIOV_NET_VF:1)]``
* ``[RP1(SRIOV_NET_VF:1), RP4(SRIOV_NET_VF:1)]``
* ``[RP3(SRIOV_NET_VF:1), RP2(SRIOV_NET_VF:1)]``
* ``[RP3(SRIOV_NET_VF:1), RP4(SRIOV_NET_VF:1)]``

This demonstrates the ability to get *different* allocations of the *same*
resource class from *different* providers in a single request (`Requirement
1`_).

Use Case 2
~~~~~~~~~~
Request: **one VF with egress bandwidth of 10000 bytes/sec**. (No, it doesn't
make sense that I don't care which physnet I'm on -- mentally replace NET with
SWITCH if that bothers you.)

Expect:

* ``[RP1(SRIOV_NET_VF:1), RP1(NET_EGRESS_BYTES_SEC:10000)]``
* ``[RP2(SRIOV_NET_VF:1), RP2(NET_EGRESS_BYTES_SEC:10000)]``
* ``[RP3(SRIOV_NET_VF:1), RP3(NET_EGRESS_BYTES_SEC:10000)]``
* ``[RP4(SRIOV_NET_VF:1), RP4(NET_EGRESS_BYTES_SEC:10000)]``

This demonstrates the ability to ensure that allocations of *different*
resource classes can be made to come from the *same* resource provider
(`Requirement 2`_).

Use Case 3
~~~~~~~~~~
Request:

* **One VF on NET1 with bandwidth 10000 bytes/sec**
* **One VF on NET2 with bandwidth 20000 bytes/sec on a NIC with SSL
  acceleration**  (This one should always land on RP2.)

Expect:

| * ``[RP1(SRIOV_NET_VF:1, NET_EGRESS_BYTES_SEC:10000),``
|   ``RP2(SRIOV_NET_VF:1, NET_EGRESS_BYTES_SEC:20000)]``
| * ``[RP3(SRIOV_NET_VF:1, NET_EGRESS_BYTES_SEC:10000),``
|   ``RP2(SRIOV_NET_VF:1, NET_EGRESS_BYTES_SEC:20000)]``

This demonstrates *both* `Requirement 1`_ and `Requirement 2`_.

Use Case 4
~~~~~~~~~~
As an Operator, I need to be able to express a request for more than one VF and
have the request succeed even if my PFs are nearly saturated.  For this use
case, assume that **each PF resource provider has only two VFs unallocated**.
I need to be able to express a request for **four VFs on NET1**.

Expect: ``[RP1(SRIOV_NET_VF:2), RP3(SRIOV_NET_VF:2)]``

This demonstrates `Requirement 3`_.

Proposed change
===============

Numbered Request Groups
-----------------------
With the existing syntax (once `Dependencies`_ land), a resource request can be
logically expressed as:

.. code-block:: python

    resources = { resource_classA: rcA_count,
                  resource_classB: rcB_count,
                  ... },
    required = [ TRAIT_C, TRAIT_D, ... ]

Semantically, each resulting allocation candidate will consist of
``resource_class``\ *N*: ``rc``\ *N*\ ``_count`` resources spread arbitrarily
across resource providers within the same tree (i.e. all resource providers in
a single allocation candidate will have the same ``root_provider_uuid``).
*Each* resource provider in *each* resulting allocation candidate will possess
*all* of the listed ``required`` traits.

.. note:: When shared resource providers are fully implemented, the above will
          read, "...spread arbitrarily across resource providers within the
          same tree *or aggregate*".

Also, it is unsupported for resource classes or traits to be repeated.

The proposed change is to augment the above to include numbered resource
groupings as follows:

Logical Representation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    resources = { resource_classA: rcA_count,
                  resource_classB: rcB_count,
                  ... },
    required = [ TRAIT_C, TRAIT_D, ... ],

    resources1 = { resource_class1A: rc1A_count,
                   resource_class1B: rc1B_count,
                   ... },
    required1 = [ TRAIT_1C, TRAIT_1D, ... ],

    resources2 = { resource_class2A: rc2A_count,
                   resource_class2B: rc2B_count,
                   ... },
    required2 = [ TRAIT_2C, TRAIT_2D, ... ],

    ...,

    resourcesX = { resource_classXA: rcXA_count,
                   resource_classXB: rcXB_count,
                   ... },
    requiredX = [ TRAIT_XC, TRAIT_XD, ... ],

Semantics
~~~~~~~~~
The term "results" is used below to refer to the contents of one item in the
``allocation_requests`` list within the ``GET /allocation_candidates``
response.

* The semantic for the (single) un-numbered grouping is unchanged.  That is, it
  may still return results from different RPs in the same tree (or, when
  "shared" is fully implemented, the same aggregate).
* However, a numbered group will always return results from the *same* RP.
  This is to satisfy `Requirement 2`_.
* Separate groups (numbered or un-numbered) may return results from the same
  RP.  That is, you are not guaranteeing RP exclusivity by separating groups.
  (If you want to guarantee such exclusivity, you need to do it with traits.)
* It is still not supported to repeat a resource class within a given (numbered
  or un-numbered) ``resources`` grouping, but there is no restriction on
  repeating a resource class from one grouping to the next.  The same applies
  to traits.  This is to satisfy `Requirement 1`_.
* A given ``required``\ *N* list applies *only* to its matching ``resources``\
  *N* list.  This goes for the un-numbered ``required``/``resources`` as well.
* The numeric suffixes are arbitrary.  Other than binding ``resources``\ *N* to
  ``required``\ *N*, they have no implied meaning.  In particular, they are not
  required to be sequential; and there is no semantic significance to their
  order.
* For both numbered and un-numbered ``resources``, a single
  *resource_class*:*count* will never be split across multiple RPs.
  While such a split could be seen to be sane for e.g. VFs, it is clearly not
  valid for e.g. DISK_GB.  If you want to be able to split, use separate
  numbered groups.  This satisfies `Requirement 3`_.
* Specifying a ``resources`` (numbered or un-numbered) without a corresponding
  ``required`` returns results unfiltered by traits.
* It is an error to specify a ``required`` (numbered or un-numbered) without a
  corresponding ``resources``.

Syntax In Flavors
~~~~~~~~~~~~~~~~~
In reference to the `Logical Representation`_, the existing (once
`Dependencies`_ have landed) implementation is to specify ``resources`` and
``required`` traits in the flavor extra_specs as follows:

* Each member of ``resources`` is specified as a separate extra_specs entry of
  the form:

.. parsed-literal::

    resources:*resource_classA*\ =\ *rcA_count*

* Each member of ``required``  is specified as a separate extra_specs entry of
  the form:

.. parsed-literal::

    trait:*TRAIT_B*\ =required

For example::

    resources:VCPU=2
    resources:MEMORY_MB=2048
    trait:HW_CPU_X86_AVX=required
    trait:CUSTOM_MAGIC=required

**Proposed:** Allow the same syntax for numbered resource and trait groupings
via the number being appended to the ``resources`` and ``trait`` keyword:

.. parsed-literal::

    resources\ *N*:*resource_classC*\ =\ *rcC_count*
    trait\ *N*:*TRAIT_D*\ =required

A given numbered ``resources`` or ``trait`` key may be repeated to specify
multiple resources/traits in the same grouping, just as with the un-numbered
syntax.

For example::

    resources:VCPU=2
    resources:MEMORY_MB=2048
    trait:HW_CPU_X86_AVX=required
    trait:CUSTOM_MAGIC=required
    resources1:SRIOV_NET_VF=1
    resources1:NET_EGRESS_BYTES_SEC=10000
    trait1:CUSTOM_PHYSNET_NET1=required
    resources2:SRIOV_NET_VF=1
    resources2:NET_EGRESS_BYTES_SEC:20000
    trait2:CUSTOM_PHYSNET_NET2=required
    trait2:HW_NIC_ACCEL_SSL=required

Syntax In the Placement API
~~~~~~~~~~~~~~~~~~~~~~~~~~~
In reference to the `Logical Representation`_, the existing (once
`Dependencies`_ have landed) `Placement API`_ implementation is via the ``GET
/allocation_candidates`` querystring as follows:

* The ``resources`` are grouped together under a single key called
  ``resources`` whose value is a comma-separated list of
  ``resource_class``\ *N*:``rc``\ *N*\ ``_count``.
* The traits are grouped together under a single key called ``required`` whose
  value is a comma-separated list of *TRAIT_Y*.

For example::

    GET /allocation_candidates?resources=VCPU:2,MEMORY_MB:2048
        &required=HW_CPU_X86_AVX,CUSTOM_MAGIC

**Proposed:** Allow the same syntax for numbered resource and trait groupings
via the number being appended to the ``resources`` and ``required`` keywords.
In the following example, groups 1 and 2 represent `Use Case 3`_::

    GET /allocation_candidates?resources=VCPU:2,MEMORY_MB:2048
        &required=HW_CPU_X86_AVX,CUSTOM_MAGIC
        &resources1=SRIOV_NET_VF:1,NET_EGRESS_BYTES_SEC:10000
        &required1=CUSTOM_PHYSNET_NET1
        &resources2=SRIOV_NET_VF:1,NET_EGRESS_BYTES_SEC:20000
        &required2=CUSTOM_PHYSNET_NET2,HW_NIC_ACCEL_SSL

There is no change to the response payload syntax.

Alternatives
------------

* `Requirement 2`_ could also be expressed via aggregates by associating each
  RP with a unique aggregate, once shared resource providers are fully
  implemented.

* We could allow the "number" suffixes to be any arbitrary string.  However,
  using integers is easy to understand and validate, and obviates worries about
  escaping/encoding special characters, etc.

* There has been discussion over time about the need for a JSON payload-based
  API to enable richer expression to request allocation candidates.  While this
  is still a possibility for the future, it was considered unnecessary in this
  case, as the current requirements can be met via the proposed (relatively
  simple) enhancements to the querystring syntax of the existing ``GET
  /allocation_candidates`` API.

* It has been suggested to include (or at least keep the way open for) syntax
  that would allow the user to express (anti-)affinity of resources.  The
  change proposed by this spec leaves a small niche of affinity-related use
  cases unsatisfied.  The scope and exact form of, and real-world need for,
  these use cases is poorly understood at this time, and is therefore not
  addressed by this specification.

Data model impact
-----------------
None.

REST API impact
---------------

See `Syntax In the Placement API`_.  To summarize, the ``GET
/allocation_candidates`` `Placement API`_ is modified to accept arbitrary query
parameter keys of the format ``resources``\ *N* and ``required``\ *N*, where
*N* can be any integer.  The format of the values to these query parameters is
identical to that of ``resources`` and ``required``, respectively.

Otherwise, there is no REST API impact.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
Operators will need to understand the `Syntax In Flavors`_ and the `Semantics`_
of the changes in order to create flavors exploiting the new functionality.
See `Documentation Impact`_.

There is no impact on the nova or openstack CLIs.  The existing CLI syntax is
adequate for expressing the newly-supported extra_specs keys.

Performance Impact
------------------

Use of the new syntax results in the ``GET /allocation_candidates`` `Placement
API`_ effectively doing multiple lookups per request.  This has the potential
to impact performance in the database by a factor of N+1, where N is the number
of numbered resource groupings specified in a given request.  Clever SQL
expression may reduce or eliminate this impact.

There should be no impact outside of the database, as this feature should not
result in a significant increase in the number of records returned by the ``GET
/allocation_candidates`` API (if anything, the increased specificity will
*decrease* the number of results).

Other deployer impact
---------------------
None

Developer impact
----------------

Developers of modules supplying Resource Provider representations (e.g. virt
drivers) will need to be aware of this feature in order to model their RPs
appropriately.

Upgrade impact
--------------
None

Implementation
==============

Assignee(s)
-----------

* efried

Work Items
----------

Implementation work was begun in Queens.  Several patches were merged; the
remaining patches have been started but are waiting on dependencies.

https://review.openstack.org/#/q/project:openstack/nova+branch:master+topic:bp/granular-resource-requests

Scheduler
~~~~~~~~~

* Negotiate microversion capabilities with the `Placement API`_.
* Recognize and parse the new `Syntax In Flavors`_.
* If the new flavor extra_specs syntax is recognized and the `Placement API`_
  is not capable of the appropriate microversion, error.
* Construct the ``GET /allocation_candidates`` querystring according to the
  flavor extra_specs.
* Send the ``GET /allocation_candidates`` request to Placement, specifying the
  appropriate microversion if the new syntax is in play.

Placement
~~~~~~~~~

* Publish a new microversion.
* Recognize and parse the new ``GET /allocation_candidates`` querystring key
  formats if invoked at the new microversion.
* Construct the appropriate database query/ies.
* Everything else is unchanged.

Dependencies
============
This work builds on reapproval and completion of the `Nested Resource
Providers`_ effort.

Testing
=======
Functional tests, including gabbits, will be added to exercise the new syntax.
New fixtures may be required to express some of the more complicated
configurations, particularly involving nested resource providers.  Test cases
will be designed to prove various combinations and permutations of the items
listed in `Semantics`_.  For example, a ``GET /allocation_candidates`` request
using both numbered and un-numbered groupings against a placement service
containing multiple nested resource provider trees with three or more levels
and involving trait propagation.  Migration scenarios will also be tested.

Documentation Impact
====================

* The `Placement API`_ reference will be updated to describe the new syntax to
  the ``GET /allocation_candidates`` API.
* The `Placement Devref`_ will be updated to describe the new microversion.
* Admin documentation (presumably the same as introduced/enhanced via the
  `Traits in Flavors`_ effort) will be updated to describe the new `Syntax In
  Flavors`_.

References
==========

* `Traits in Flavors`_ spec
* `Traits in the GET /allocation_candidates API`_ spec
* `Generic`_ Resource Providers original spec
* `Nested Resource Providers`_ spec
* `Placement API`_ reference
* `Placement Devref`_
* `<https://etherpad.openstack.org/p/nova-multi-alloc-request-syntax-brainstorm>`_
* `<https://review.openstack.org/#/q/project:openstack/nova+branch:master+topic:bp/granular-resource-requests>`_

.. _`Traits in Flavors`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/request-traits-in-nova.html
.. _`Traits in the GET /allocation_candidates API`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/add-trait-support-in-allocation-candidates.html
.. _`Generic`: https://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/resource-providers.html
.. _`Nested Resource Providers`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html
.. _`Placement API`: https://developer.openstack.org/api-ref/placement/#list-allocation-candidates
.. _`Placement Devref`: https://docs.openstack.org/nova/latest/user/placement.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced, approved, implementation started
   * - Rocky
     - Reproposed
