..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Allow custom resource classes in flavor extra specs
===================================================

https://blueprints.launchpad.net/nova/+spec/custom-resource-classes-in-flavors

This spec proposes the ability to create flavors that can select custom
resource classes at scheduling time, and override standard resource classes
to avoid scheduling them, while maintaining a useful display of the flavor.



Problem description
===================

The background to this problem is well described in the custom resource
classes [1]_ spec.

With that spec implemented, we now are able to represent these units of
consumable resources, but not schedule to them. The scheduler currently only
requests units of VCPU, MEMORY_MB, and DISK_GB. It needs to be able to request
custom resource classes as well, to be able to properly filter these resources.

Since the end goal is to be able to schedule only based on the custom resource
class, but flavor display and users rely on VCPU, MEMORY_MB, and DISK_GB, we
will also need to add overrides for these resource classes. These overrides
will allow dashboards, CLIs, etc. to be able to display the resources available
for these flavors, without requiring the scheduler to filter on them.

Use Cases
---------

As a deployer of ironic, I wish to be able to create flavors which request
a specific class of indivisible baremetal machines. I also want my users
to be able to see what sort of CPU/RAM/disk resources are available on my
baremetal flavors, without scheduling on that data.

As an NFV deployer, I have hardware that has FPGA devices. I have tagged that
hardware in the placement engine with custom resource classes based on the
software loaded into the FPGA. I would like to allow my users to select a
flavor that targets their instance to a machine with an FPGA that has
particular software loaded.

Proposed change
===============

We propose to add handling for a number of flavor extra specs to solve this:

* ``resources:$CUSTOM_RESOURCE_CLASS=$N``, where $N is a positive integer
  value. This will be added to the request made by the ``FilterScheduler`` to
  the placement engine, to filter scheduling candidates by the custom resource
  class if present.

* ``resources:$STANDARD_RESOURCE_CLASS=0``, where $STANDARD_RESOURCE_CLASS is
  one of "VCPU", "MEMORY_MB", or "DISK_GB". This causes the scheduler to avoid
  scheduling based on the associated value in the top level Flavor object
  field, while still using it for flavor display.

When the scheduler is constructing the request to placement, it will start by
building a list of resource classes from the base flavor attributes as it does
today. Next it will look for any overrides and add classes and/or adjust
amounts of existing classes based on the extra_specs it finds.

Existing ironic instances will need to go through a migration (described in the
"Data model impact" section) in order to correct allocations if the node has
a resource class defined.

Alternatives
------------

We could instead add new field(s) to the Flavor object that are specifically
meant for custom resource classes and overrides of standard resource classes.
While this does have the benefit of avoiding an off chance that some operator
is already using extra specs like this, there's a couple of reasons not to do
this. First, it creates an extra cycle before we can require ironic operators
to transition their flavors, because the new field wouldn't be available until
Pike. Second, as I understand things, we want to avoid adding to flavors right
now, as it makes it more work to get rid of them altogether in the long term.

Data model impact
-----------------

Existing ironic instances won't have the custom resource class recorded in
their ``instance.flavor`` attribute. As such, allocations won't be recorded for
this resource class, and the node the instance exists on will be schedulable
with new-style flavors.

For example, let's say an existing ironic instance has a resource_class of
``CUSTOM_BAREMETAL_GOLD`` which is accounted for in the baremetal service, but
is not reported as an allocation against the resource provider  in the
placement service. If an operator configures a flavor's extra_specs and sets
``resources:CUSTOM_BAREMETAL_GOLD="1"``, the scheduler may pick a node to host
the instance that placement thinks is available, as there are no allocations
against it, but the resource is actually already consumed. This would result in
a build failure.

To resolve this, we need to do two things:

1. We'll need to check each existing instance at Pike startup, in the driver
   layer. If the ironic node that the instance exists on has a resource class
   defined, we add the custom resource class to ``instance.flavor``.

2. When updating instance allocations in the ``update_available_resource``
   periodic task in the nova-compute service, the scheduler report client will
   need to check for custom resource classes on the ``instance.flavor`` and
   report those into the placement service.

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

Due to the migrations, there will be a small performance penalty to start
nova-compute hosts running the ironic driver for the first time in Pike.

Other deployer impact
---------------------

Deployers will need to adjust their flavors to use custom resource classes,
before upgrading to Queens.

.. warning:: Deployers should not adjust their flavors until the data migration
  described in the `Data model impact`_ section above is complete.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Ed Leafe (edleafe)

Other contributors:
  Jay Pipes (jaypipes)

Work Items
----------

* Add code to migrate ironic instance flavor data.

* Add code to report custom resource class allocations.

* Add support for custom resource classes in the scheduler request.

* Add overrides for standard resource classes (the deployer does this).


Dependencies
============

This change depends on the resource tracker reporting custom resource class
inventory, which is tracked in the "Custom Resource Classes (Pike)"
blueprint. [2]_


Testing
=======

New style flavors will be added to setup for the job that runs ironic and
nova with resource classes on the nodes.


Documentation Impact
====================

These extra specs should be documented in the Install Guide, and also in
the Upgrades guide.

References
==========

.. [1] http://specs.openstack.org/openstack/nova-specs/specs/ocata/approved/custom-resource-classes.html

.. [2] https://blueprints.launchpad.net/nova/+spec/custom-resource-classes-pike

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
