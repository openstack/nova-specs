..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================================
select_destinations() scheduler RPC API method to pass RequestSpec object
=========================================================================

https://blueprints.launchpad.net/nova/+spec/sched-select-destinations-use-request-spec-object

Change the `select_destinations()` scheduler RPC API method to use a
`nova.objects.request_spec.RequestSpec` object instead of a nested dict.

Problem description
===================

The main interface into the scheduler, the `select_destinations()` method,
accepts a `request_spec` parameter and a filter_properties parameter that are
nested dict.
The nested `request_spec` dict is constructed in
`nova.scheduler.utils.build_request_spec()`, which is called by nova-conductor
before asking the scheduler to find compute nodes on which to put one or more
requested virtual machine instances.
The nested `filter_properties` dict is mainly built in the
`nova.compute.api._build_filter_properties()` method, which is called before
asking the scheduler to find compute nodes, but can also be built in other
places and needs consistency.

Previous blueprints have introduced a `nova.objects.request_spec.RequestSpec`
object that can model the entire request for multiple instance launches.
However, the scheduler RPC API has not been changed to use this new object.
Instead, nova-scheduler constructs the `RequestSpec` object in its
`_schedule()` method, populating the request spec attributes manually by
looking at the `request_spec` dictionary parameter.

Use Cases
----------

This is a pure refactoring effort for cleaning up all the interfaces in between
Nova and the scheduler so the scheduler could be split out by the next cycle.

Project Priority
-----------------

This blueprint is part of a global effort around the 'scheduler' refactoring
for helping it to be split out. This has been defined as the 3rd priority for
this Kilo cycle.

Proposed change
===============

The RequestSpec object will be amended to add the filter_properties fields.
The `select_destinations()` scheduler RPC API method will be changed to consume
a `nova.objects.request_spec.RequestSpec` object instead of two nested
dictionaries. The RPC API will be incremented and translation code blocks will
be added to allow older nova-conductor workers to continue to transmit the
dictionary `request_spec` and `filter_properties` parameters.

Alternatives
------------

None.

Data model impact
-----------------

None.

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

None.

Developer impact
----------------

None, besides making the scheduler call interfaces gradually easier to read
and understand.

Implementation
==============

We will increment the version of the RequestSpec object by adding new fields
which were previously provided in the `filter_properties` dictionary. The new
RequestSpec object should look like :

.. code:: python

 class RequestSpec(base.NovaObject):

    """Models the request to launch one or more instances in the cloud."""

    VERSION = '1.1'

    fields = {
        'image': fields.DictOfStringsField(nullable=False),
        # This should eventually be deconstructed into component parts
        'instance_properties': fields.ObjectField('Instance'),
        'instance_type': fields.ObjectField('Flavor', nullable=True),
        'num_instances': fields.IntegerField(nullable=False, default=1),
        'force_hosts': fields.StringField(nullable=True),
        'force_nodes': fields.StringField(nullable=True),
        'pci_requests': fields.ListOfObjectsField('PCIRequest', nullable=True),
        'retry': fields.ObjectField('Retry', nullable=True),
        'limits': fields.ObjectField('Limits', nullable=True),
        'group': fields.ObjectField('GroupInfo', nullable=True),
        'scheduler_hints': fields.DictOfStringsField(nullable=True)

    }

PCIRequest, Retry, Limits and GroupInfo objects will be created accordingly.

We will increment the version of the scheduler RPC API and insert translation
blocks in the `select_destinations` method to handle an older nova-conductor
node sending the old-style dictionaries `request_spec` and `filter_properties`
parameters to a newer nova-scheduler node that expects a `RequestSpec` object.

The nova-conductor manager code will then be updated to construct a
`RequestSpec` object to pass to the `select_destinations()` scheduler RPC API
instead of calling `nova.scheduler.utils.build_request_spec()`.  The
`build_request_spec()` method will then be removed.

All calls made for updating filter_properties dictionary will be replaced by
setting fields to the RequestSpec object attached.

The code added in the `request-spec-objects` blueprint that constructed a
`RequestSpec` object in the `FilterScheduler._schedule()` method will then be
removed, as it will no longer be needed since the `request_spec` parameter will
already be an object.

Assignee(s)
-----------

Primary assignee:
  bauzas

Work Items
----------

- Increment RequestSpec object by adding new fields related to
  `filter_properties`

- Increment the scheduler RPC API `select_destinations()` method to take a
  `RequestSpec` object instead of a dictionary for the `request_spec`
  parameter. In the same patch, modify the conductor manager to construct a
  `RequestSpec` object and pass that to `select_destinations()` instead of
  dict. Remove the code in filter_scheduler.FilterScheduler._schedule() that
  constructs a `RequestSpec` object, since the object is now being passed to
  `select_destinations()`

- Remove the `nova.scheduler.utils.build_request_spec` function.

Dependencies
============

This blueprint is dependent on the completion of the following blueprints:

- `request-spec-object`

Testing
=======

New unit tests for the request spec objects will be added. The existing unit
tests of the scheduler will be overhauled in the patch set that converts the
filters to use the new request_spec object model instead of its current
free-form `filter_properties` dictionary of things.

Documentation Impact
====================

Developer reference material that explains the new placement spec class
will be delivered as a part of this blueprint.

References
==========

This blueprint is part of an overall effort to clean up, version, and stabilize
the interfaces between the nova-api, nova-scheduler, nova-conductor and
nova-compute daemons that involve scheduling and resource decisions.

See https://wiki.openstack.org/wiki/Gantt/kilo#Tasks for the list of all
blueprints targeted for Kilo.
