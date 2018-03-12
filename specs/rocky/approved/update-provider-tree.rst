..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Resource tracker allows virt driver to update provider tree
===========================================================

https://blueprints.launchpad.net/nova/+spec/update-provider-tree

In the movement towards using placement for scheduling and resource management,
the virt driver method ``get_available_resource`` was initially superseded by
``get_inventory``, whereby the driver could specify its inventory in terms
understood by placement. In Queens, a `get_traits`_ driver method was added.
But ``get_inventory`` is limited to expressing only inventory (not traits or
aggregates).  And both of these methods are limited to the resource provider
corresponding to the compute node.

Recent developments such as `Nested Resource Providers`_ necessitate the
ability for the virt driver to have deeper control over what the resource
tracker configures in placement on behalf of the compute node.  This blueprint
proposes a new virt driver method, ``update_provider_tree``, and its method of
consumption by the resource tracker, allowing full control over the placement
representation of the compute node and its associated providers and metadata.

Problem description
===================
Existing virt driver methods are limited in their ability to express resource
provider information.

Use Cases
---------
As a virt driver developer, I wish to be able to model my compute node and
associated entities as any combination of provider trees and sharing providers,
along with inventories, traits, and aggregate associations for those providers.

Proposed change
===============

ComputeDriver.update_provider_tree
----------------------------------
``ComputeDriver.update_provider_tree`` is introduced.  It accepts two
parameters:

* A ``nova.compute.provider_tree.ProviderTree`` object representing all the
  providers in the tree associated with the compute node, and any sharing
  providers (those with the ``MISC_SHARES_VIA_AGGREGATE`` trait) associated via
  aggregate with any of those providers (but not *their* tree- or
  aggregate-associated providers), as currently known by placement.  This
  object is fully owned by the ``update_provider_tree`` method, and can
  therefore be modified without locking/concurrency considerations.  Note,
  however, that it may contain providers not directly owned/controlled by the
  compute host.  Care must be taken not to remove or modify such providers
  inadvertently.  In addition, providers may be associated with traits and/or
  aggregates maintained by outside agents.  The ``update_provider_tree`` must
  therefore also be careful only to add/remove traits/aggregates it explicitly
  controls.
* String name of the compute node (i.e. ``ComputeNode.hypervisor_hostname``)
  for which the caller is updating providers and inventory.  Drivers may use
  this to help identify the compute node provider in the ProviderTree.  Drivers
  managing more than one node (e.g. ironic) may also use it as a cue to
  indicate which node is being updated.

The virt driver is expected to update the ProviderTree object with current
resource provider and inventory information. When the method returns, the
ProviderTree should represent the correct hierarchy of nested resource
providers associated with this compute node, as well as the inventory,
aggregates, and traits associated with those resource providers.

.. note:: Despite the name, a ProviderTree instance may in fact contain more
          than one tree.  For purposes of this specification, the ProviderTree
          passed to ``update_provider_tree`` will contain:

          * the entire tree associated with the compute node; and
          * any sharing providers (those with the ``MISC_SHARES_VIA_AGGREGATE``
            trait) which are associated via aggregate with any of the providers
            in the compute node's tree.  The sharing providers will be
            presented as lone roots in the ProviderTree, even if they happen to
            be part of a tree themselves.

          Consider the example below.  ``SSP`` is a shared storage provider and
          ``BW1`` and ``BW2`` are shared bandwidth providers; all three have
          the ``MISC_SHARES_VIA_AGGREGATE`` trait::

                     CN1                 SHR_ROOT               CN2
                    /   \       agg1    /   /\     agg1        /   \
               NUMA1     NUMA2--------SSP--/--\-----------NUMA1     NUMA2
              /     \   /    \            /    \         /     \   /    \
            PF1    PF2 PF3   PF4--------BW1   BW2------PF1    PF2 PF3   PF4
                                 agg2             agg3

          When ``update_provider_tree`` is invoked for ``CN1``, it is passed a
          ProviderTree containing::

                     CN1 (root)
                    /   \       agg1
               NUMA1     NUMA2-------SSP (root)
              /     \   /    \
            PF1    PF2 PF3   PF4------BW1 (root)
                                 agg2

This method supersedes ``get_inventory`` and ``get_traits``: if this method is
implemented, neither ``get_inventory`` nor ``get_traits`` is used.

Driver implementations of ``update_provider_tree`` are expected to use public
``ProviderTree`` methods to effect changes to the provider tree passed in.
Some of the methods which may be useful are as follows:

* ``new_root``: Add a new root provider to the tree.
* ``new_child``: Add a new child under an existing provider.
* ``data``: Access information (name, UUID, parent, inventory, traits,
  aggregates) about a provider in the tree.
* ``remove``: Remove a provider **and its descendants** from the tree.  Use
  caution in multiple-ownership scenarios.
* ``update_inventory``: Set the inventory for a provider.
* ``add_traits``, ``remove_traits``: Set/unset virt-owned traits for a provider
  (see `ProviderTree.add_traits and .remove_traits`_).
* ``add_aggregates``, ``remove_aggregates``: Set/unset virt-owned aggregate
  associations for a provider (see `ProviderTree.add_aggregates and
  .remove_aggregates`_).

.. note:: There is no supported mechanism for ``update_provider_tree`` to
          effect changes to allocations.  This is intentional: in Nova,
          allocations are managed exclusively outside of virt. (Usually by the
          scheduler; sometimes - e.g. for migrations - by the conductor.)

Porting from get_inventory
~~~~~~~~~~~~~~~~~~~~~~~~~~
Virt driver developers wishing to move from ``get_inventory`` to
``update_provider_tree`` should use the ``ProviderTree.update_inventory``
method, specifying the compute node as the provider and the same inventory as
returned by ``get_inventory``.  For example:

.. code::

  def get_inventory(self, nodename):
      inv_data = {
          'VCPU': { ... },
          'MEMORY_MB': { ... },
          'DISK_GB': { ... },
      }
      return inv_data

would become:

.. code::

  def update_provider_tree(self, provider_tree, nodename):
      inv_data = {
          'VCPU': { ... },
          'MEMORY_MB': { ... },
          'DISK_GB': { ... },
      }
      provider_tree.update_inventory(nodename, inv_data)

Porting from get_traits
~~~~~~~~~~~~~~~~~~~~~~~
To replace ``get_traits``, developers should use the
``ProviderTree.add_traits`` method, specifying the compute node as the
provider and the same traits as returned by ``get_traits``.  For example:

.. code::

  def get_traits(self, nodename):
      traits = ['HW_CPU_X86_AVX', 'HW_CPU_X86_AVX2', 'CUSTOM_GOLD']
      return traits

would become:

.. code::

  def update_provider_tree(self, provider_tree, nodename):
      provider_tree.add_traits(
          nodename, 'HW_CPU_X86_AVX', 'HW_CPU_X86_AVX2', 'CUSTOM_GOLD')

SchedulerReportClient.update_from_provider_tree
-----------------------------------------------
This is the report client method responsible for accepting the ProviderTree
as modified by the virt driver via ``update_provider_tree`` and making the
necessary placement API calls to ensure that the representation in the
placement service matches it.  In particular:

* Providers removed by ``update_provider_tree`` are removed from placement.
* Providers added by ``update_provider_tree`` are created in placement.
* If inventories, traits, or aggregates were changed for any providers by
  ``update_provider_tree``, those changes are flushed back to placement.

.. note:: In multiple-ownership scenarios, virt drivers should be careful not
          to remove or modify providers not owned by the compute host.

ResourceTracker._update
-----------------------
This is where the virt driver is asked to report on compute resources.  It is
where, for example, the call to ``get_inventory`` was added to supersede the
data returned by ``get_available_resource`` if ``get_inventory`` is
implemented.  Here we add another level to allow ``update_provider_tree`` to
supersede ``get_inventory``.  The logic changes from:

.. code::

  try:
      ComputeDriver.get_inventory()
  except NotImplementedError:
      SchedulerReportClient.update_compute_node()

  try:
      ComputeDriver.get_traits()
  except NotImplementedError:
      pass

to:

.. code::

  try:
      ComputeDriver.update_provider_tree()
      SchedulerReportClient.update_from_provider_tree()
  except NotImplementedError:
      try:
          ComputeDriver.get_inventory()
      except NotImplementedError:
          SchedulerReportClient.update_compute_node()

      try:
          ComputeDriver.get_traits()
      except NotImplementedError:
          pass

ProviderTree.add_traits and .remove_traits
------------------------------------------
Since outside agents (e.g. operators) need to be able to set and unset
traits which are outside of the purview of the virt driver,
`ComputeDriver.update_provider_tree`_ needs to be able to add and remove traits
explicitly, rather than simply overwriting the entire set of traits for a given
provider.  To facilitate this, we will add the following methods to
ProviderTree:

.. code::

 def add_traits(self, name_or_uuid, \*traits)
 def remove_traits(self, name_or_uuid, \*traits)

Arguments:

* ``name_or_uuid``: Either the name or the UUID of the resource provider whose
  traits are to be affected.
* ``traits``: String names of traits to add or remove.  Any other traits
  associated with the provider are untouched.

ProviderTree.add_aggregates and .remove_aggregates
--------------------------------------------------
Since outside agents (e.g. operators) need to be able to set and unset
aggregate associations which are outside of the purview of the virt driver,
`ComputeDriver.update_provider_tree`_ needs to be able to add and remove
aggregate associations explicitly, rather than simply overwriting the entire
set of aggregate associations for a given provider.  To facilitate this, we
will add the following methods to ProviderTree:

.. code::

 def add_aggregates(self, name_or_uuid, \*aggregates)
 def remove_aggregates(self, name_or_uuid, \*aggregates)

Arguments:

* ``name_or_uuid``: Either the name or the UUID of the resource provider whose
  aggregates are to be affected.
* ``aggregates``: String UUIDs of aggregates to add or remove.  Any other
  aggregates associated with the provider are untouched.

Alternatives
------------
* Continue to provide piecemeal methods in the spirit of ``get_inventory``
  and ``get_traits``.  The proposed solution can subsume the functionality of
  both of those methods and more, but it can also grow along with placement and
  Nova's use thereof.
* Allow virt drivers direct control over placement.  While we can't stop
  out-of-tree drivers from doing this, it has been discussed and decided that
  in-tree drivers should be funneled through the choke point of the
  SchedulerReportClient for actual placement API communication.

Data model impact
-----------------
None

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
No direct impact.  This change, followed by virt drivers implementing
``update_provider_tree``, followed by virt drivers extending their resource
provider models, will ultimately allow operators to exert more power over
scheduling operations.

Performance Impact
------------------
This change increases the amount of traffic to the placement service, which has
the potential to affect performance.  However, there is as yet no evidence that
doing lots of placement calls is "expensive" relative to the other processing
occurring in these code paths.  The intent is to mitigate such impact if and
when it is demonstrated to be problematic.

One mitigation strategy, already largely implemented, is caching the placement
representation locally via a separate ProviderTree instance maintained in the
SchedulerReportClient.  The specifics are outside the scope of this document.
However, the existing code in this area is inconsistent and needs to be
codified in a separate specification so we can work towards consistency.

Other deployer impact
---------------------
None

Developer impact
----------------
See above.

Upgrade impact
--------------
None

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  efried

Work Items
----------
The code for this has been completed.  Some of it merged in Queens, including:

* https://review.openstack.org/#/c/521187/ introduces the
  ``update_provider_tree`` method in the ``ComputeDriver`` base class.
* https://review.openstack.org/#/c/533821/ implements the
  ``update_from_provider_tree`` method in the report client.
* https://review.openstack.org/#/c/520246/ implements the changes in the
  resource tracker to use the above.

These changes were developed under the `Nested Resource Providers`_ blueprint.

Dependencies
============
None (all dependencies have merged in Queens).

Continuing development of such features as `Nested Resource Providers`_,
`Granular Resource Requests`_, and shared resource providers will expand the
range of things driver developers can do through their implementation of
``update_provider_tree``.

Testing
=======
Extensive functional testing is included in addition to unit tests.

Documentation Impact
====================
None

References
==========
* `Nested Resource Providers`_ spec
* Support `Traits`_ in Allocation Candidates spec
* Support traits in the Ironic driver spec (`get_traits`_)
* `Granular Resource Requests`_ spec

.. _`Nested Resource Providers`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html
.. _`Traits`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/add-trait-support-in-allocation-candidates.html
.. _`get_traits`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/ironic-driver-traits.html
.. _`Granular Resource Requests`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/granular-resource-requests.html

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Code finished and mostly merged.
   * - Rocky
     - Figured we really ought to have something written down, so proposed an
       actual blueprint and this spec.
