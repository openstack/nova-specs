..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Default allocation ratio configuration
======================================

https://blueprints.launchpad.net/nova/+spec/initial-allocation-ratios

Provide separate CONF options for specifying the initial allocation
ratio for compute nodes. Change the default values for
CONF.xxx_allocation_ratio options to None and change the behaviour of
the resource tracker to only override allocation ratios for *existing*
compute nodes if the CONF.xxx_allocation_ratio value is not None.

The primary goal of this feature is to support both the API and config way to
pass allocation ratios.

Problem description
===================

Manually set placement allocation ratios are overwritten
--------------------------------------------------------------------

There is currently no way for an admin to set the allocation ratio on an
individual compute node resource provider's inventory record in the placement
API without the resource tracker eventually overwriting that value the next
time it runs the ``update_available_resources`` periodic task on the
``nova-compute`` service.

The saga of the allocation ratio values on the compute host
-----------------------------------------------------------

The process by which nova determines the allocation ratio for CPU, RAM and disk
resources on a hypervisor is confusing and `error`_ `prone`_. The
``compute_nodes`` table in the nova cell DB contains three fields representing
the allocation ratio for CPU, RAM and disk resources on that hypervisor. These
fields are populated using different default values depending on the version of
nova running on the ``nova-compute`` service.

.. _error: https://bugs.launchpad.net/nova/+bug/1742747
.. _prone: https://bugs.launchpad.net/nova/+bug/1789654

Upon starting up, the resource tracker in the ``nova-compute`` service worker
`checks`_ to see if a record exists in the ``compute_nodes`` table of the nova
cell DB for itself. If it does not find one, the resource tracker `creates`_ a
record in the table, `setting`_ the associated allocation ratio values in the
``compute_nodes`` table to the value it finds in the ``cpu_allocation_ratio``,
``ram_allocation_ratio`` and ``disk_allocation_ratio`` nova.conf configuration
options but only if the config option value is not equal to 0.0.

.. _checks: https://github.com/openstack/nova/blob/852de1e/nova/compute/resource_tracker.py#L566
.. _creates: https://github.com/openstack/nova/blob/852de1e/nova/compute/resource_tracker.py#L577-L590
.. _setting: https://github.com/openstack/nova/blob/6a68f9140/nova/compute/resource_tracker.py#L621-L645

The default values of the ``cpu_allocation_ratio``, ``ram_allocation_ratio``
and ``disk_allocation_ratio`` CONF options is `currently set`_ to ``0.0``.

.. _currently set: https://github.com/openstack/nova/blob/852de1e/nova/conf/compute.py#L400

The resource tracker saves these default ``0.0`` values to the
``compute_nodes`` table when the resource tracker calls ``save()`` on the
compute node object. However, there is `code`_ in the
``ComputeNode._from_db_obj`` that, upon **reading** the record back from the
database on first save, changes the values from ``0.0`` to ``16.0``, ``1.5`` or
``1.0``.

.. _code: https://github.com/openstack/nova/blob/852de1e/nova/objects/compute_node.py#L177-L207

The ``ComputeNode`` object that was ``save()``'d by the resource tracker has
these new values for some period of time while the record in the
``compute_nodes`` table continues to have the wrong ``0.0`` values. When the
resource tracker runs its ``update_available_resource()`` next perioidic task,
the new ``16.0``/``1.5``/``1.0`` values are then saved to the compute nodes
table.

There is a `fix`_ for `bug/1789654`_, which is to not persist
zero allocation ratios in ResourceTracker to avoid initializing placement
allocation_ratio with 0.0 (due to the allocation ratio of 0.0 being multiplied
by the total amount in inventory, leading to 0 resources shown on the system).

.. _fix: https://review.openstack.org/#/c/598365/
.. _bug/1789654: https://bugs.launchpad.net/nova/+bug/1789654

Use Cases
---------

An administrator would like to set allocation ratios for individual resources
on a compute node via the placement API *without that value being overwritten*
by the compute node's resource tracker.

An administrator chooses to only use the configuration file to set allocation
ratio overrides on their compute nodes and does not want to use the placement
API to set these ratios.

Proposed change
===============

First, we propose to change the default option values of existing
``CONF.cpu_allocation_ratio``, ``CONF.ram_allocation_ratio`` and
``CONF.disk_allocation_ratio`` options relating to allocation ratios to
``None`` from the existing default values of ``0.0``. The reason we change
it is that this value will be change from ``0.0`` to ``16.0``, ``1.5`` or
``1.0`` later, which is weird and confusing.

We will also change the resource tracker to **only** overwrite the compute
node's allocation ratios to the value of the ``cpu_allocation_ratio``,
``ram_allocation_ratio`` and ``disk_allocation_ratio`` CONF options **if the
value of these options is NOT ``None``**.

In other words, if any of these CONF options is set to something *other than*
``None``, then the CONF option should be considered the complete override value
for that resource class' allocation ratio. Even if an admin manually adjusts
the allocation ratio of the resource class in the placement API, the next time
the ``update_available_resource()`` periodic task runs, it will be overwritten
to the value of the CONF option.

Second, we propose to add 3 new nova.conf configuration options:

* ``initial_cpu_allocation_ratio``
* ``initial_ram_allocation_ratio``
* ``initial_disk_allocation_ratio``

That will used to determine how to set the *initial* allocation ratio of
``VCPU``, ``MEMORY_MB`` and ``DISK_GB`` resource classes when a compute worker
first starts up and creates its compute node record in the nova cell DB and
corresponding inventory records in the placement service. The value of these
new configuration options will only be used if the compute service's resource
tracker is not able to find a record in the placement service for the compute
node the resource tracker is managing.

The default value of each of these CONF options shall be ``16.0``, ``1.5``, and
``1.0`` respectively. This is to match the default values for the original
allocation ratio CONF options before they were set to ``0.0``.

These new ``initial_xxx_allocation_ratio`` CONF options shall **ONLY** be used
if the resource tracker detects no existing record in the ``compute_nodes``
nova cell DB for that hypervisor.

Finally, we will need also add an online data migration and continue to read
the ``xxx_allocation_ratio`` or ``initial_xxx_allocation_ratio`` config on
read from the DB if the values are ``0.0`` or ``None``. If it's an existing
record with 0.0 values, we'd want to do what the compute does, which is use
the configure ``xxx_allocation_ratio`` config if it's not None, and fallback
to using the ``initial_xxx_allocation_ratio`` otherwise.

And add an online data migration that updates all compute_nodes
table records that have ``0.0`` or ``None`` allocation ratios. Then we drop
that at some point with a blocker migration and remove the code in the
``nova.objects.ComputeNode._from_db_obj`` that adjusts allocation ratios.

We propose to add a nova-status upgrade check to iterate the cells looking
for compute_nodes records with ``0.0`` or ``None`` allocation ratios and signal
that as a warning that you haven't done the online data migration. We could
also check the conf options to see if they are explicitly set to 0.0 and if
so, we should fail the status check.

Alternatives
------------

None

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

None

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

We need an online data migrations for any compute_nodes with existing ``0.0``
and ``None`` allocation ratio. If it's an existing record with 0.0 values, we
will replace it with the configure ``xxx_allocation_ratio`` config if it's not
None, and fallback to using the ``initial_xxx_allocation_ratio`` otherwise.

.. note:: Migrating 0.0 allocation ratios from existing ``compute_nodes`` table
   records is necessary because the ComputeNode object based on those table
   records is what gets used in the scheduler [1]_, specifically the
   ``NUMATopologyFilter`` and ``CPUWeigher`` (the ``CoreFilter``,
   ``DiskFilter`` and ``RamFilter`` also use them but those filters are
   deprecated for removal so they are not a concern here).

And clearly in order to take advantage of the ability to manually set
allocation ratios on a compute node, that hypervisor would need to be upgraded.
No impact to old compute hosts.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  yikun

Work Items
----------

* Change the default values for ``CONF.xxx_allocation_ratio`` options to
  ``None``.
* Modify resource tracker to only set allocation ratios on the compute node
  object when the CONF options are non- ``None``
* Add new ``initial_xxx_allocation_ratio`` CONF options and modify resource
  tracker's initial compute node creation to use these values
* Remove code in the ``ComputeNode._from_db_obj()`` that changes allocation
  ratio values
* Add a db online migration to process all compute_nodes with existing ``0.0``
  and ``None`` allocation ratio.
* Add a nova-status upgrade check for ``0.0`` or ``None`` allocation ratio.

Dependencies
============

None

Testing
=======

No extraordinary testing outside normal unit and functional testing

Documentation Impact
====================

A release note explaining the use of the new ``initial_xxx_allocation_ratio``
CONF options should be created along with a more detailed doc in the admin
guide explaining the following primary scenarios:

* When the deployer wants to **ALWAYS** set an override value for a resource on
  a compute node. This is where the deployer would ensure that the
  ``cpu_allocation_ratio``, ``ram_allocation_ratio`` and
  ``disk_allocation_ratio`` CONF options were set to a non- ``None`` value.
* When the deployer wants to set an **INITIAL** value for a compute node's
  allocation ratio but wants to allow an admin to adjust this afterwards
  without making any CONF file changes. This scenario uses the new
  ``initial_xxx_allocation_ratios`` for the initial ratio values and then shows
  the deployer using the osc placement commands to manually set an allocation
  ratio for a resource class on a resource provider.
* When the deployer wants to **ALWAYS** use the placement API to set allocation
  ratios, then the deployer should ensure that ``CONF.xxx_allocation_ratio``
  options are all set to ``None`` and the deployer should issue Placement
  REST API calls to
  ``PUT /resource_providers/{uuid}/inventories/{resource_class}`` [2]_ or
  ``PUT /resource_providers/{uuid}/inventories`` [3]_ to set the allocation
  ratios of their resources as needed (or use the related ``osc-placement``
  plugin commands [4]_).

References
==========

.. [1] https://github.com/openstack/nova/blob/a534ccc5a7/nova/scheduler/host_manager.py#L255
.. [2] https://developer.openstack.org/api-ref/placement/#update-resource-provider-inventory
.. [3] https://developer.openstack.org/api-ref/placement/#update-resource-provider-inventories
.. [4] https://docs.openstack.org/osc-placement/latest/

Nova Stein PTG discussion:

* https://etherpad.openstack.org/p/nova-ptg-stein

Bugs:

* https://bugs.launchpad.net/nova/+bug/1742747
* https://bugs.launchpad.net/nova/+bug/1729621
* https://bugs.launchpad.net/nova/+bug/1739349
* https://bugs.launchpad.net/nova/+bug/1789654

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Proposed
