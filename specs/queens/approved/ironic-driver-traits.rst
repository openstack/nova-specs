..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Support traits in the Ironic driver
===================================

https://blueprints.launchpad.net/nova/+spec/ironic-driver-traits

To allow more granular scheduling of Ironic resources, Ironic is exposing
traits for each ironic node, which in turn must be reported up to placement
via the ironic driver.

Problem description
===================

Sometimes a flavor needs to select only a subset of the ironic nodes with a
given resource class, rather than just any node of a given resource class.

Eventually, it is expected that ironic may re-configure a node based on the
requested trait, and a node reporting a trait may mean that such
re-configuration is available for that node, be that BIOS configuration or
RAID configuration changes. For the moment there is no agreed way forward for
this approach, so this part of the problem will be considered out of scope.

Use Cases
---------

Consider flavor Gold targeting resource class CUSTOM_GOLD. Some users want a
kind of Gold++ where it also targets CUSTOM_GOLD but in addition requires
specific set of CPU flags that are not available on all nodes with the
resource class of CUSTOM_GOLD.

Another use case is being able to dedicate specific Ironic nodes for use only
by a specific set of projects. The remainder of the hosts are for general use.
If a user has a dedicated pool of resources, they have the ability to pick if
they create an instance in their dedicated pool or in the general pool. Other
users are only able to build in the general pool. One way to bisect the nodes
like this is assigning traits such as CUSTOM_IRONIC_NODE_PROJECT_B and
CUSTOM_IRONIC_NODE_GENERAL_USE to the appropriate ironic nodes. Then there is
a public flavor to target the general pool of hosts, and a private project
specific flavor that targets their dedicated pool.

Proposed change
===============

All this work depends on the ability for a flavor to have a required set of
traits and for Nova to be able to request from placement resource providers
that have the requested set of traits. This is all implemented in the two
blueprints:

* https://blueprints.launchpad.net/nova/+spec/add-trait-support-in-allocation-candidates
* https://blueprints.launchpad.net/nova/+spec/request-traits-in-nova

There are two main parts to this spec:

* sending requested traits back to ironic
* getting ironic node traits into placement

When Nova boot is called, the ironic driver already sets capabilities related
extra specs from the requested flavor on the ironic node via the Ironic API.
This is done in the virt drivers `_add_instance_info_to_node` method. It is
set on the path `/instance_info/capabilities`. In a similar way we will also
set the traits related flavor extra specs on a path `/instance_info/traits`.
Note, this requires no API changes on the Ironic side, the path is a PATCH
requests JSONPath change identifier.

Currently the nova virt driver has a `get_inventory` call to list the inventory
of a given compute_node. This change will add a `get_traits(nodename)` call
to the virt driver interface to fetch the traits for a given nodename. In a
similar way to get_inventory, this will use the cached node details. For
drivers that don't override the new `get_traits` call we will raise a
NotImplementedError.

These traits for each ironic node need to be checked against the current traits
for the associated Resource Provider, and updated if needed. This is likely
going to be done in the scheduler report client, in a similar way to the
existing `set_inventory_for_provider` method that currently creates the
resource provider and updates its inventory for the appropriate node.
Internally the pattern in `_ensure_resource_provider` method that ensures the
resource provider is in the correct state will be used to ensure the traits are
updated correctly. The existing resource provider APIs will be used to update
the traits.

We are considering the Ironic API as the single source of truth for the Traits
for a given Node. So should someone set any traits directly on the Placement
API, they will be overridden on the next virt driver sync, with will reset the
traits to what is in the Ironic API.

Alternatives
------------

It is hoped the virt driver will move away from `get_inventory()` and towards
`update_provider_tree()`. While that would change details on the
implementation the key data flow is the same. This spec is rather urgent
because the move to Resource Classes makes placement more rigid, and stops the
ability to build on a large ironic host with a smaller flavor. Sadly some
people rely on that feature.

We could allow admins to set traits directly via the placement API, but
this is a bit strange when Nova is creating the resource provider. Its possible
ironic could create the resource provider on Nova's behalf. An additional
complication is that we really want the traits to be populated by ironic
inspector, in a similar way capabilities are set by inspector rules today.

We could allow admins to extend the list of traits with a configuration
variable on the compute host, and that could be behaviour for all drivers that
don't implement `get_traits`, but for the moment this has been ignored because
it is not relevant to the Ironic driver.


Data model impact
-----------------

None

REST API impact
---------------

None, uses exiting placement APIs.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

There will be increased API calls to placement when the inventory is updated.

Other deployer impact
---------------------

A deployer will now be able to set traits in Ironic via the dependent ironic
spec:
https://review.openstack.org/#/c/504531/

This spec is about the Nova virt driver sending these traits to placement.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  John Garbutt (johnthetubaguy)

Work Items
----------

* add `get_traits` to the ironic driver
* push traits to the placement API
* on boot set requested traits on the ironic node

Dependencies
============

* New APIs in Ironic to set traits on a node:
  https://review.openstack.org/#/c/504531/

* There is a loose dependency on Nova adding support for request traits on
  bp add-trait-support-in-allocation-candidates and
  bp request-traits-in-nova
  Without those two blueprints this feature can't be tested end to end.

Testing
=======

Need functional tests that prove we can select the correct ironic node on
traits alone, by correctly configuring a flavor.

Documentation Impact
====================

Related details are mostly covered in the Ironic docs around using resource
classes and Nova flavors. This should be expanded to detail how traits can
also be used.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
