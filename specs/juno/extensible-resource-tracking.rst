..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Extensible Resource Tracking
==========================================

https://blueprints.launchpad.net/nova/+spec/extensible-resource-tracking

This blueprint introduces plugins to track resource allocation to allow the
operator to select the resources they wish to track and to allow developers
to add resource types without changing the existing code.

Problem description
===================

The set of allocated compute resources is hard coded in the resource tracker,
Allocation of these resources is always tracked regardless of their relevance
to the cloud operator. In many cases the operator would like to track the use
of different resources or account for their use in a different way.

To support this requirement we need a way to easily develop additional
resource tracking components that meet the operators preference and to make
these optional so that only operators interested in them or are willing to
incur any performance impact related to them, have to use them.

The following is an example use case based on the CPU Entitlement
blueprint referenced in the dependencies section below.

As an operator I want to define a parameter for flavors called cu (compute
unit). For users, cu represents cpu performance delivered by an instance
using that flavor. Internally, cu represents a proportion of physical cpu
capacity that should be assigned to the instance. I want to schedule
instances to servers according to the available cpu capacity measured in cu.

This use case describes a measure for cpu that is different to vcpu and
cannot be implemented in terms of vcpu. The resource tracker needs to track
the quantity of cu used at the host and report cu capacity to the scheduler.
Note that the proportion of physical cpu mapped to cu depends on the
performance of the processor. So in this case the operator would not use
vcpu but would use cu. Other choices may be made in respect of other
resources.

Proposed change
===============

The proposed solution is to provide a plugin mechanism for resource tracking
and make the selection of plugins configurable. This will include plugins
at the resource tracker to represent compute resources, to track their usage,
test availability in claims, and to communicate resource information to
the scheduler. It will also include plugins for the host manager at the
scheduler to interpret and handle the resource information received.

Currently the means to make compute resource information available to the
scheduler is via the compute_nodes table in the database. A field in this
table will be used to communicate a dictionary of values representing the
resource information.

The existing extra_specs parameter of flavors already supports addition of
resource requirements as key value/pairs, so no change is required in the
APIs. However, the extra_specs parameter is not currently retained in the
instances or instance_system_metadata tables so it will be added.

A base class will be defined for a compute resource plugin for the resource
tracker with methods to:

* initialize the plugin

* add and remove instances

* test for sufficient resources to support a new instance

* report resource information

Plugins will be loaded by the resource tracker at start up using stevedore
and called at existing points in the resource tracker code path. Exceptions
occurring during method execution will be handled and logged.

Plugins will be:

* defined as entry points in the names space: **nova.compute.resources**

* selected by name in the resource tracker configuration option:
  **compute_resources**

The resource information from the plugins will be recorded in the
compute_nodes table in the database in **stats** field.

A base class will be defined for a resource consumer plugin for the host
manager with methods to:

* read resource information

* update resource information to reflect scheduler decisions

Plugins will be loaded by the host manager at start up using stevedore and
called at existing points in the host manager code path to make the resource
information available in the host state. Exceptions occurring during method
execution will be handled and logged.

Plungins will be:

* defined as entry points in the name space: **nova.scheduler.consumers**

* selected by name in the host manager configuration option:
  **scheduler_consumers**

The new resource information can be exploited by filters and weights in the
filter scheduler. The filters also have access to flavor extra_specs
providing the ability to define new resource requirements that can be
compared to the new resource information in the host state.

By the nature of a distributed system configuration it is possible that an
inconsistent set of resource, consumer, filter and weight plugins are loaded.
Plugin developers are responsible for the behavior of the plugins in the
event of missing or unexpected information. The exception handling around
plugin method invocation will provide general error handling and reporting.

Alternatives
------------

Our proposed solution defines two types of plugin: compute resource for the
resource tracker and resource consumer for the host manager. The logic to
add an instance to the compute resource plugin and to consume resources in
the resource consumer plugin is essentially the same. These could be
implemented as a single plugin that is loaded in both places. The dual
plugin approach has been taken to avoid sharing code between the scheduler
and the rest of nova in preparation for splitting the scheduler out from the
rest of nova.

When this blueprint was first implemented in the Icehouse cycle it was
decided that the resource data would be communicated in a field called
**extra_resources**. That field was created for this purpose and merged in
Icehouse-2. Subsequently a separate change was made to remove the
compute_node_stats table and put stats information in the compute_nodes
table as well. The **stats** field was created for that purpose.

Since the creation of the stats field there has been a debate over the
future of the extra_resources field and which field should be used for this
blueprint. There is an intention to refactor stats as resource plugins when
this blueprint has been implemented. A key factor in the decision is how
to do that refactor.

It is possible to migrate stats handling to resource and consumer plugins
without changing the representation of stats data in the database. So to ease
the migration we propose to use the stats field and drop the extra_resources
field.

Data model impact
-----------------

The blueprint used the extra_resources field in the compute node table to
communicate the resource tracking information. This field was added to the
database in Icehouse-2 but has not yet been used. As discussed above, this
will be removed and the existing stats field will be used instead.

The extra_specs field will be added to the instances table.

REST API impact
---------------

This blueprint does not affect the existing REST APIs. New resource
requirements can be set for flavors using the existing extra_specs API
extension.

Security impact
---------------

This blueprint does not introduce any new security issues. The selection of
plugins will be determined by operators and they will operate on data
communicated through an existing path. Developers are able to make their
plugins more robust by checking the integrity of the data they operate on.

Notifications impact
--------------------

This blueprint does not introduce new notifications.

Other end user impact
---------------------

This blueprint provides an extended resource management capability to the
operator. It does not affect end users beyond the placement of their
instances.

Performance Impact
------------------

The plugin mechanism has no inherent performance impact, but performance may
be impacted by the quantity of data exchanged by plugins and the performance
of any operations they perform in the plugin methods.

The compute resource plugins are called when instances are created, resized
or migrated, and when the compute node executes its periodic resource update.

The consumer plugins at the scheduler are called to interpret data received
and to update host state when an instance placement decision is made. These
are likely to be light weight operations.

Other deployer impact
---------------------

The plugins will be configured in the following ways:

* the nova setup.cfg file will contain the entry points for plugins

* the compute_resources config option select compute resource plugins

* the scheduler_consumers config option select resource consumer plugins

The default config options will be empty lists so no plugins will be loaded.
This will ensure that this new feature only has effect if it is explicitly
configured.

Developer impact
----------------

Developers will be able to add new plugins for this feature.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  pmurray

Other contributors:
  andrea-rosa-m

Work Items
----------

see: 
https://review.openstack.org/#q,topic:bp/extensible-resource-tracking,n,z

The first two work items have patches are ready for review:

* Add the resource plugin mechanism to resource tracker

* Add the resource consumer plubin mechanism to the host manager

* Add extra_specs to the instances table and write it to
  instance_system_metadata

The following work item is for house keeping:

* The extra_resources field for the compute_nodes table was merged in
  Icehouse-2. It will now be removed due to adopting the new stats field

Dependencies
============

The following blueprints have a dependency on this one:

* https://blueprints.launchpad.net/nova/+spec/cpu-entitlement

* https://blueprints.launchpad.net/nova/+spec/network-bandwidth-entitlement

* https://blueprints.launchpad.net/nova/+spec/cache-qos-monitoring

Testing
=======

Unit tests are sufficient to cover feature changes.

Documentation Impact
====================

Configuration options are derived automatically. New plugins
should be listed as they are implemented.

References
==========

Original blueprint for refactoring compute node stats:
https://blueprints.launchpad.net/nova/+spec/stats-as-rt-extension

Original specification that accompanied this blueprint in the Icehouse cycle:
https://wiki.openstack.org/wiki/ExtensibleResourceTracking
