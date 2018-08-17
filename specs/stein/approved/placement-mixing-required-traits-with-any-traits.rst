..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Support mixing required traits with any traits
==============================================

https://blueprints.launchpad.net/nova/+spec/mixing-required-traits-with-any-traits

The `any-traits-in-allocation-candidates-query`_ spec proposed to allow
querying traits in the form of ``required=in:TRAIT1,TRAIT2``. This spec goes
one step further and proposes to allow repeating the ``required`` query
parameter to support mixing both  ``required=TRAIT1,TRAIT2,!TRAIT3`` and
``required=in:TRAIT1,TRAIT2`` format in a single query. This is needed for
Neutron to be able to express that a port needs a resource provider having
a specific ``vnic_type`` trait but also having one of the physnet traits the
port's network maps to.

For example::

  GET /allocation_candidates?required1=CUSTOM_VNIC_TYPE_DIRECT&
                             required1=in:CUSTOM_PHYSNET_FOO,CUSTOM_PHYSNET_BAR
                             ...

requests a networking device RP in the candidates that supports the ``direct``
``vnic_type`` and is connected either to ``physnet_foo`` or ``physnet_bar`` or
both.

Problem description
===================

Neutron through Nova needs to be able to query Placement for allocation
candidates that are matching to *at least one* trait from the list of traits as
well as matching another specific trait in a single query.

Use Cases
---------

Neutron wants to use this any(traits) query to express that a port's bandwidth
resource request needs to be fulfilled by a Network device RP that is connected
to one of the physnets the network of the given port is connected to. With
Neutron's multiprovider network extension a single Neutron network can consist
of multiple network segments connected to different physnets. But at the same
time Neutron wants to express that the same RP has a specific vnic_type trait
as well.

Proposed change
===============

Extend the ``GET /allocation_candidates`` and ``GET /resource_providers``
requests to allow repeating the ``required`` and ``required<N>`` query param
to support both the ``required=TRAIT1,TRAIT2,!TRAIT3`` and
``required=in:TRAIT1,TRAIT2`` syntax in a single query.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion the ``GET /allocation_candidates`` and  the
``GET /resource_providers`` query should allow repeating the ``required``
query parameter more than once while supporting both normal and any trait
syntax in the same query.

The ``GET /allocation_candidates`` query having
``required=CUSTOM_VNIC_TYPE_NORMAL&
required=in:CUSTOM_PHYSNET1,CUSTOM_PHYSNET2`` parameters should result in
allocation candidates where each allocation candidate has the traits
``CUSTOM_VNIC_TYPE_NORMAL`` and either ``CUSTOM_PHYSNET1`` or
``CUSTOM_PHYSNET2`` (or both).

The ``GET /resource_providers`` query having
``required=CUSTOM_VNIC_TYPE_NORMAL&
required=in:CUSTOM_PHYSNET1,CUSTOM_PHYSNET2`` parameters should result in
resource providers where each resource provider has the traits
``CUSTOM_VNIC_TYPE_NORMAL`` and either ``CUSTOM_PHYSNET1`` or
``CUSTOM_PHYSNET2`` (or both).

The response body of the ``GET /allocation_candidates`` and
``GET /resource_providers`` query are unchanged.

Note the following two queries express exactly the same requirements::

  ?required=in:A,B,C
  &required=X
  &required=Y
  &required=Z

  ?required=in:A,B,C
  &required=X,Y,Z

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The osc-placement client plugin needs to be updated to support the new
Placement API microversion. This means the the CLI should support providing
the ``--required`` parameter more than once supporting both normal and any
trait syntax.

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

* Extend the resource provider and allocation candidate DB query to support
  more than one set of required traits
* Extend the Placement REST API with a new microversion that supports repeating
  the ``required`` query param
* Extend the osc-placement client plugin to support the new microversion

Dependencies
============

* The `any-traits-in-allocation-candidates-query`_ spec

..  _`any-traits-in-allocation-candidates-query`: https://review.openstack.org/#/c/565730

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

None

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
