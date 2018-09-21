..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Support any traits in allocation_candidates query
=================================================

https://blueprints.launchpad.net/nova/+spec/any-traits-in-allocation-candidates-query

The ``GET /allocation_candidates`` request in Placement supports the
``required`` query parameter. If the caller specifies a list of traits in the
``required`` parameter then placement will limit the returned allocation
candidates to those RP trees that fulfill *every* traits in that list. To
support minimum bandwidth guarantees in Neutron + Nova we need to be able to
query allocation candidates that fulfill *at least one* trait from a list of
traits specified in the query. This is required for the case when a Neutron
network maps to more than one physnets but the port's bandwidth request can be
fulfilled from any physnet the port's network maps to.

Problem description
===================

Neutron through Nova needs to be able to query Placement for allocation
candidates that are matching to *at least one* trait from the list of traits
provided in the query.

Use Cases
---------

Neutron wants to use this any(traits) query to express that a port's bandwidth
resource request needs to be fulfilled by a Network device RP that is connected
to one of the physnets the network of the given port is connected to. With
Neutron's multiprovider network extension a single Neutron network can consist
of multiple network segments connected to different physnets.

Proposed change
===============

Extend the ``GET /allocation_candidates`` and ``GET /resource_providers``
requests with a new ``required=in:TRAIT1,TRAIT2`` query parameter syntax and
change the placement implementation to support this new syntax.

The `granular-resource-requests`_ spec proposes support for multiple request
groups in the Placement query identified by a positive integer postfix in the
``required`` query param. The new ``in:TRAIT1,TRAIT2`` syntax is applicable to
the ``required<N>`` query params as well.

..  _`granular-resource-requests`: https://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/granular-resource-requests.html

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------
Today the ``GET /allocation_candidates`` and ``GET /resource_providers`` query
support the ``required`` query param in the form of
``required=TRAIT1,TRAIT2,!TRAIT3``. This spec proposes to implement a new
microversion to allow the format of ``required=in:TRAIT1,TRAIT2`` as well
as the old format.

Each resource provider returned from a request having
``required=in:TRAIT1,TRAIT2`` should have *at least* one matching trait from
TRAIT1 and TRAIT2.

``required=in:TRAIT1,TRAIT2`` used in a ``GET /allocation_candidates`` query
means that the union of all the traits across all the providers in every
allocation candidate must contain at least one of T1, T2.

``requiredX=in:TRAIT1,TRAIT2`` used in a ``GET /allocation_candidates`` query
means that the resource provider that satisfies the requirement of the granular
request group ``X`` must also has at least one of T1, T2.

The response body of the ``GET /allocation_candidates`` and
``GET /resource_providers`` query are unchanged.

A separate subsequent spec will propose to support repeating the ``required``
query param more than once to allow mixing the two formats.

Note that mixing required and forbidden trait requirements in the same
``required=in:`` query param, like ``required=in:TRAIT1,!TRAIT2`` will not be
supported and will result a HTTP 400 response.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The osc-placement client plugin needs to be updated to support the new
Placement API microversion. That plugin currently support the --required CLI
parameter accepting a list of traits. So this patch propose to extend that
parameter to accept in:TRAIT1,TRAIT2 format.

Performance Impact
------------------

None

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
  balazs-gibizer

Work Items
----------

* Extend the resource provider and allocation candidate DB query to support the
  new type of query
* Extend the Placement REST API with a new microversion that supports the any
  trait syntax
* Extend the osc-placement client plugin to support the new microversion

Dependencies
============

* the osc-placement client plugin can only be extended with the new
  microversion support if every older microversion is already supported which
  is not the case today.

Testing
=======

Both new gabbi and functional tests needs to be written for the Placement API
change. Also the osc-placement client plugin will need additional functional
test coverage.

Documentation Impact
====================

The Placement API reference needs to be updated.

References
==========

* osc-placement `review`_ series adding support for latest Placement
  microversions

..  _`review`: https://review.openstack.org/#/c/548326


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
   * - Stein
     - Reproposed
