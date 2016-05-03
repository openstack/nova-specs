.. _newton-priorities:

=========================
Newton Project Priorities
=========================

List of themes (in the form of use cases) the nova development team is
prioritizing in Newton (in no particular order).

+-------------------------------------------+-----------------------+
| Priority                                  | Primary Contacts      |
+===========================================+=======================+
| `Cells V2`_                               | `Andrew Laski`_       |
+-------------------------------------------+-----------------------+
| `Scheduler`_                              | `Jay Pipes`_          |
+-------------------------------------------+-----------------------+
| `API Improvements`_                       | `Andrew Laski`_       |
|                                           | `Sean Dague`_         |
+-------------------------------------------+-----------------------+
| `os-vif Integration`_                     | `Daniel Berrange`_    |
+-------------------------------------------+-----------------------+
| `Libvirt Storage Pools (Live Migration)`_ | `Matthew Booth`_      |
+-------------------------------------------+-----------------------+
| `Get Me a Network`_                       | `Matt Riedemann`_     |
+-------------------------------------------+-----------------------+
| `Glance v2 Integration`_                  | `Mike Fedosin`_       |
+-------------------------------------------+-----------------------+

.. _Andrew Laski: https://launchpad.net/~alaski
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Sean Dague: https://launchpad.net/~sdague
.. _Daniel Berrange: https://launchpad.net/~berrange
.. _Matthew Booth: https://launchpad.net/~mbooth-9
.. _Matt Riedemann: https://launchpad.net/~mriedem
.. _Mike Fedosin: https://launchpad.net/~mfedosin

Cells v2
--------

A lot of the design and planning for Cells v2 happened in the Mitaka release
but unfortunately not a lot of code was merged.

In Newton we plan to execute on several parts of the Cells v2 roadmap:

* Online data migration from the cell DB to the global API DB.
* Writing commands to help with upgrading to a Cells v2 deployment.
* Testing a single Cells v2 (cell of one) deployment in the gate using a
  multi-node job along with upgrade testing in grenade.
* Documentation of the upgrade and deployment process for Cells v2.

Supporting multiple v2 cells is going to be a stretch goal.

Scheduler
---------

In Mitaka we laid some groundwork for the scheduler refactor for resource
providers.

In Newton we plan to execute on:

* Online data migrations to the new resource provider inventory and allocation
  tables along with moving those to the API DB.
* Cleanup how the resource tracker deals with PCI devices.
* Migrate PCI and NUMA resources to the new tables.
* Model generic resource pools for things like IP subnet allocation pools and
  shared storage pools.
* Create a separate placement REST API for generic resource pools.

Defining how to model and standardize host capabilities is going to be a
stretch goal.

API Improvements
----------------

In Newton we will focus on two major API improvement efforts:

* Defining API policy defaults in code with oslo.policy. This will simplify
  deployments so that operators only need to populate the policy.json file with
  overrides, otherwise the defaults will all be in code like the config
  options. This will also ensure we have API policy rules defined for all
  actions.
* Completely moving the api-ref documentation into the Nova code tree so it's
  owned by the Nova team. As part of this work, the api-ref documentation will
  be scrubbed to fix errors, fill gaps, and add support for documenting
  microversions.

os-vif Integration
------------------

The os-vif library was created in the Mitaka release. It has an object model
and contains linuxbridge and openvswitch reference implementations. It also
integrates with oslo.privsep.

In Newton we plan to integrate the library with Nova to start replacing parts
of the libvirt driver's VIF plugging code with os-vif.

Libvirt Storage Pools (Live Migration)
--------------------------------------

In Mitaka, a lot of work went into improving the user experience for live
migration and cleaning up the code so it's more maintainable.

In Newton there will be a focused effort on cleaning up technical debt in the
libvirt imagebackend code so it's more maintainable. Then we'll build on that
to use libvirt storage pools, which will then be used for migrating instances
rather than setting up SSH keys between computes.

Get Me a Network
----------------

In Mitaka, the Neutron team delivered the ``auto-allocated-topology`` API which
will setup simple tenant networking.

In Newton, Nova will leverage that Neutron API to make booting an instance and
getting networking automatically provisioned a simple process for the end user.
This is also required for the eventual removal of nova-network.

Glance v2 Integration
---------------------

We've been talking about this since Kilo. Glance wants to remove their v1 API.
We have a plan for adding the Glance v2 support into the nova.image.api code
and write it in such a way that we can easily drop the v1 code in a subsequent
release when Glance drops support for their v1 API.

The Nova os-images proxy API will also be deprecated since there will be
unavoidable incompatibilities when translating from the Glance v2 API to the
Nova os-images proxy API, which is based on Glance v1.
