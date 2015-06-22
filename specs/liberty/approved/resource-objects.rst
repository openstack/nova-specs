..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Model resources as objects
==========================

https://blueprints.launchpad.net/nova/+spec/resource-objects

Adds model objects to represent the resources that may be requested
for and consumed by an instance.

Problem description
===================

In Nova, we have a very loose way of modeling the resources that are
consumed by virtual machine instances and provided by compute nodes.
The Flavor object has a number of static fields that correspond to amounts
of simple resources like CPU, RAM and local disk. We use dictionaries
of key/value pairs and JSON-serialized BLOBs of data to model other types
of resources, like PCIe devices or NUMA cell layouts.

The resource tracker on the compute node keeps track of the collection of
resources that are consumed on the node. The `ResourceTracker.old_resources`
attribute is a dictionary containing a clutter of nested dictionaries. Some of
these nested dictionaries include the 'stats' dict for the extensible resource
tracker; various 'pci_devices', 'pci_stats' and 'pci_passthrough_devices'
things; a 'numa_topology' blob that stores a JSON-serialized representation of
an object in `nova.virt.hardware` and a 'metrics' dictionary with completely
unstructured and undocumented key/value pairs. In addition to these, the
`ResourceTracker.old_resources` dictionary contains top-level keys including
some that match the simple resource types that a Flavor object exposes:

- `local_gb_used`: Amount of disk in GB used on the compute node
- `local_gb`: Total GB of local disk capacity the compute node provides
- `free_disk_gb`: Calculated amount of disk the compute node has available
- `vcpus_used`: Number of vCPUs consumed on the compute node
- `vcpus`: Total number of vCPUs the compute node provides
- `free_vcpus`: Calculated number of vCPUs the compute node has available
- `memory_mb_used`: Amount of RAM in MB used on the compute node
- `memory_mb`: Total MB of RAM capacity the compute node provides
- `free_ram_mb`: Calculated amount of RAM the compute node has available
- `running_vms`: Number of virtual machine instances running on the node
- `current_workload`: Some calculated value of the workload on the node

Unfortunately, none of the above is documented in the code, and in order to add
new features to the scheduler, people have continued to add free-form keys and
nested dictionaries to the dictionary. This makes communicating actual usage
amounts to the scheduler error-prone: the resource tracker calls the
`scheduler_client.update_resource_stats()` method, passing in this
unstructured, unversioned dictionary of information as-is.  This means the
scheduler interface is incredibly fragile since the interface can be altered on
a whim by any developer who decides to add a new key to the free-form
dictionary of resources. Typos in resource dictionary keys can be very easy to
miss in code reviews, and frankly, there is virtually no functional testing for
a lot of the edge case code in the resource tracker around the extensible
resource tracker.

In addition to the problem of fragile interfaces, the free-form nature of the
resources dictionary has meant that different resources are tracked in
different ways. PCI resources are tracked one way, NUMA topology usage is
tracked in a different way, CPU/RAM/disk are tracked differently again and any
resources modeled in the complete free-for-all of the extensible resource
tracker are tracked in an entirely different way, using plugins that modify a
supplied 'stats' nested dictionary.

An example of the mess this has created in the resource tracker can be
seen here:

.. code:: python

    def _update(self, context, values):
        """Update partial stats locally and populate them to Scheduler."""
        self._write_ext_resources(values)
        # NOTE(pmurray): the stats field is stored as a json string. The
        # json conversion will be done automatically by the ComputeNode object
        # so this can be removed when using ComputeNode.
        values['stats'] = jsonutils.dumps(values['stats'])

        if not self._resource_change(values):
            return
        if "service" in self.compute_node:
            del self.compute_node['service']
        # NOTE(sbauza): Now the DB update is asynchronous, we need to locally
        #               update the values
        self.compute_node.update(values)
        # Persist the stats to the Scheduler
        self._update_resource_stats(context, values)
        if self.pci_tracker:
            self.pci_tracker.save(context)

If resources were actually modeled consistently, the above code would look like
this instead:

.. code:: python

    def _update(self, context, resources):
        if not self._resource_change(resources):
            return
        # Notify the scheduler about changed resources
        scheduler_client.update_usage_for_compute_node(
            context, self.compute_node, resources)

Similarly, the following code (again from the resource tracker):

.. code:: python

    def _update_usage(self, context, resources, usage, sign=1):
        mem_usage = usage['memory_mb']

        overhead = self.driver.estimate_instance_overhead(usage)
        mem_usage += overhead['memory_mb']

        resources['memory_mb_used'] += sign * mem_usage
        resources['local_gb_used'] += sign * usage.get('root_gb', 0)
        resources['local_gb_used'] += sign * usage.get('ephemeral_gb', 0)

        # free ram and disk may be negative, depending on policy:
        resources['free_ram_mb'] = (resources['memory_mb'] -
                                    resources['memory_mb_used'])
        resources['free_disk_gb'] = (resources['local_gb'] -
                                     resources['local_gb_used'])

        resources['running_vms'] = self.stats.num_instances
        self.ext_resources_handler.update_from_instance(usage, sign)

        # Calculate the numa usage
        free = sign == -1
        updated_numa_topology = hardware.get_host_numa_usage_from_instance(
                resources, usage, free)
        resources['numa_topology'] = updated_numa_topology

would instead look like this:

.. code:: python

    def _update_usage(self, context, amounts):
        for resource, amount in amounts.items():
            self.inventories[resource].consume(amount)

Use Cases
----------

Nova contributors wish to extend the functionality of the scheduler and intend
to break the scheduler out into the Gantt project. In order to do this
effectively, the internal interfaces around the resource tracker and the
scheduler must be cleaned up to use structured objects.

Project Priority
-----------------

This blueprint is part of the `scheduler` refactoring effort defined as a
priority for the Liberty release.

Proposed change
===============

Modeling requested and used resource amounts is the foundational building block
that must be done first before any further refactoring or cleanup of the
scheduler or resource tracker interfaces.

This blueprint encompasses the addition of sets of classes to represent:

- Amounts of different datatypes, e.g. `IntegerAmount` or `NUMATopologyAmount`.
- Inventories of different datatypes, which describe the actual capacity, the
  amount used up already and any overcommit ratio. E.g. `IntegerInventory`,
  `NUMAInventory`.
- Different types of resources, e.g. RAM which uses `IntegerAmount` and
  `IntegerInventory`, or NUMA topology which uses `NUMAAmount` and
  `NUMAInventory`.

These amount, inventory and resource classes will be `nova.objects` object
classes and will enable Nova to evolve, in a versioned manner, the way that it
tracks resources and exposes resource consumption.

The goals of the extensible resource tracker (ERT) were to put in place a
framework that allowed adding new resource types and allowed accounting for
those resources in different ways. While this blueprint does indeed remove the
ERT, because these resource, amount and inventory classes are being added
as `nova.object` objects, we will gain the flexibility that the ERT intended
but with the stability of the nova objects system.

The resource tracker code will then be converted to use the above classes when
representing inventories of all resources on a compute node. As today, these
will be persisted by simply calling `compute_node.save()`.

No changes are proposed to the database schema of the `compute_nodes` table or
the fields in `nova.objects.ComputeNode`, however we do add translation methods
to `nova.objects.ComputeNode` that will be able to produce a dict of
`Inventory` objects (keyed by `Resource`) from the compute node and update the
compute node from a similar structure.

Alternatives
------------

None.

Data model impact
-----------------

None. The objects added in this blueprint are not stored in a database. These
objects are a replacement for an unstructured nested dictionary that is
currently used to represent resource amounts.

REST API impact
---------------

None.

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

None.

Other deployer impact
---------------------

The ERT will be removed when this blueprint is completed.

Developer impact
----------------

Once this blueprint is completed, code handling the construction of the
request_spec will be more structured and much of the spaghetti code in the
resource tracker around the ERT, PCI tracker and NUMA topology quirks will go
away.

Implementation
==============

The following abstract classes will be provided:

.. code:: python

 class Amount(object):
    """Represents a quantity of a resource."""

    def __eq__(self, other):
        raise NotImplementedError

    def __ne__(self, other):
        return not self == other

    def __hash__(self, other):
        raise NotImplementedError

    def __neg__(self, other):
        raise NotImplementedError


 class Inventory(object):
    """Describes the capacity, available and used amounts for a resource."""

    def consume(self, amount):
        """Update (i.e. add) the given amount to the used amount in this
        inventory. If the amount is negative, more resources will be available
        afterwards than were before.

        :param amount 'Amount' to add to the usage.
        :raises ValueError if amount is the wrong type for this inventory.
        :raises CapacityException if accommodating this request would cause
                either available or used resources to go negative.
        """
        raise NotImplementedError

    def can_provide(self, amount):
        """Determine if this inventory can provide the given amount of
        resources. An overcommit ratio may be applied.

        :param amount 'Amount' to determine if there is room for.
        :raises ValueError if amount is the wrong type for this inventory or is
                negative.
        :returns True if the requested amount of resources may be consumed,
                 False otherwise.
        """
        raise NotImplementedError


 class Resource(object):
    """Describes a particular kind of resource."""

    @classmethod
    def make_amount(cls, *args, **kwargs):
        """Makes an Amount of the type appropriate to this resource."""
        raise NotImplementedError

    @classmethod
    def make_inventory(cls, *args, **kwargs):
        """Makes an Inventory of the type appropriate to this resource."""
        raise NotImplementedError

Each concrete specialization of the Inventory class must be able to handle
overcommit ratios for the type of resource that it handles.

With the idea that *all* requested resources for an instance should be able
to be compared to *all* resource inventories for a compute node in the
same way, using code that looks like this:

.. code:: python

 for resource, amount in request_spec.resources.items():
    if compute_node.inventories[resource].can_provide(amount):
        # do something... perhaps claim resources on the compute
        # node, which might eventually call:
        compute_node.inventories[resource].consume(amount)

Assignee(s)
-----------

Primary assignee:
  jaypipes

Other contributors:
  lxsli

Work Items
----------

- Add classes for amount and inventory representation.

- Add classes for resource representation.

- Add translation methods (`get_inventories` and `update_inventories`) to
  `nova.objects.ComputeNode` to return or update from a dict of `Resource,
  Inventory` objects with unit tests.

- Convert resource tracker to use inventories instead of triples of
  free/total/used amounts in key/value pairs in a dictionary for the non-PCI,
  non-ERT, non-NUMA resources.

- Remove the extensible resource tracker code.

- Convert resource tracker to use inventories instead of 'numa_topology' key
  and `nova.virt.hardware.VirtNUMATopology` object in the `old_resources`
  dictionary.

- Convert resource tracker to use inventories instead of 'pci_devices' and
  'pci_passthrough_devices' keys and a `nova.pci.pci_stats.PciDeviceStats`
  object in the `pci_tracker` attribute of the resource tracker.

- Convert the virt driver's `get_available_resources` method to return a
  dictionary of resource objects.

- Deprecate the old `update_resource_stats()` conductor RPC API method.

- Convert the scheduler's `HostStateManager` to utilize the new
  `ComputeNode.get_inventories()` and `ComputeNode.update_inventories` methods.

- Add developer reference documentation for how resources are modeled.

Dependencies
============

None.

Testing
=======

New unit tests for the objects will be added. The existing unit tests of
resource tracker will be overhauled in the patch set that converts the resource
tracker to use the new resource object models instead of its current free-form
dictionary of things.

Documentation Impact
====================

There are currently no developer reference docs that explain how the different
resources are tracked within Nova.  Developer reference material that explains
the new resource type and amount classes will be delivered as a part of this
blueprint.

References
==========

This blueprint is part of an overall effort to clean up, version, and stabilize
the interfaces between the nova-api, nova-scheduler, nova-conductor and
nova-compute daemons that involve scheduling and resource decisions.

- `detach-service-from-computenode`
- `resource-objects` <-- this blueprint
- `request-spec-object`
- `sched-select-destinations-use-request-spec-object`
- `placement-spec-object`
- `condition-objects`
- `sched-placement-spec-use-resource-objects`
- `sched-placement-spec-use-condition-objects`
- `sched-get-placement-claims`
