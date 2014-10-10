..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Create RequestSpec Object
=========================

https://blueprints.launchpad.net/nova/+spec/request-spec-object

Add a structured, documented object that represents a specification for
launching multiple instances in a cloud.

Problem description
===================

The main interface into the scheduler, the `select_destinations()` method,
accepts a `request_spec` parameter that is a nested dict. This nested dict is
constructed in `nova.scheduler.utils.build_request_spec()`, however the
structure of the request spec is not documented anywhere and the filters in the
scheduler seem to take a laisse faire approach to querying the object during
scheduling as well as modifying the `request_spec` object during loops of the
`nova.scheduler.host_manager.HostStateManager.get_filtered_hosts()` method,
which calls the filter object's `host_passes` object, supplying a
`filter_properties` parameter, which itself has a key called `request_spec`
that contains the aforementioned nested dict.

This situation makes it very difficult to understand exactly what is going on
in the scheduler, and cleaning up this parameter in the scheduler interface is
a pre-requisite to making a properly-versioned and properly-documented
interface in preparation for a split-out of the scheduler code.


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

A new class called `RequestSpec` will be created that models a request to
launch multiple virtual machine instances. The first version of the
`RequestSpec` object will simply be an objectified version of the current
dictionary parameter. The scheduler will construct this `RequestSpec` object
from the `request_spec` dictionary itself.

The existing
`nova.scheduler.utils.build_request_spec` method will be removed in favor of a
factory method on `nova.objects.request_spec.RequestSpec` that will construct
a `RequestSpec` from the existing key/value pairs in the `request_spec`
parameter supplied to `select_destinations`.

Alternatives
------------

None.

Data model impact
-----------------

This spec is not focusing on persisting the RequestSpec object but another
blueprint (and a spec) will be proposed with this one as dependency for
providing a save() method to the RequestSpec object which would allow it to be
persisted in (probably) instance_extra DB table.

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

The `request_spec` dictionary is currently constructed by the nova-conductor
when it calls the `nova.scheduler.utils.build_request_spec()` function, which
looks like this:

.. code:: python

 def build_request_spec(ctxt, image, instances, instance_type=None):
    """Build a request_spec for the scheduler.

    The request_spec assumes that all instances to be scheduled are the same
    type.
    """
    instance = instances[0]
    if isinstance(instance, obj_base.NovaObject):
        instance = obj_base.obj_to_primitive(instance)

    if instance_type is None:
        instance_type = flavors.extract_flavor(instance)
    # NOTE(comstud): This is a bit ugly, but will get cleaned up when
    # we're passing an InstanceType internal object.
    extra_specs = db.flavor_extra_specs_get(ctxt, instance_type['flavorid'])
    instance_type['extra_specs'] = extra_specs
    request_spec = {
            'image': image or {},
            'instance_properties': instance,
            'instance_type': instance_type,
            'num_instances': len(instances),
            # NOTE(alaski): This should be removed as logic moves from the
            # scheduler to conductor.  Provides backwards compatibility now.
            'instance_uuids': [inst['uuid'] for inst in instances]}
    return jsonutils.to_primitive(request_spec)

A possible first version of a class interface for the `RequestSpec`
class would look like this, in order to be as close to a straight conversion
from the nested dict's keys to object attribute notation:

.. code:: python

 class RequestSpec(base.NovaObject):

    """Models the request to launch one or more instances in the cloud."""

    VERSION = '1.0'

    fields = {
        'image': fields.DictOfStringsField(nullable=False),
        # instance_properties could eventually be deconstructed into component
        # parts
        'instance_properties': fields.ObjectField('Instance'),
        'instance_type': fields.ObjectField('Flavor', nullable=False),
        'num_instances': fields.IntegerField(default=1),
    }

As `request_spec` dictionary is having a deprecated `instance_uuids` field, we
will not provide this field into the RequestSpec object and instead bump the
RPC API version and remove it from the dictionary before as a work item.

This blueprint does not change the `select_destinations` scheduler RPC API
method, so we would construct a `nova.objects.request_spec.RequestSpec` object
*on the nova-scheduler side*, from the `request_spec` dictionary key in the
`FilterScheduler._schedule()` method, like so:

.. code:: python

    def _schedule(self, context, request_spec, filter_properties):
        """Returns a list of hosts that meet the required specs,
        ordered by their fitness.
        """
        elevated = context.elevated()
        request_spec = objects.RequestSpec.from_dict(request_spec)
        instance_type = request_spec.instance_type

        update_group_hosts = self._setup_instance_group(context,
                filter_properties)

        config_options = self._get_configuration_options()

        filter_properties.update({'context': context,
                                  'request_spec': request_spec,
                                  'config_options': config_options,
                                  'instance_type': instance_type})

        self.populate_filter_properties(request_spec,
                                        filter_properties)

        # Find our local list of acceptable hosts by repeatedly
        # filtering and weighing our options. Each time we choose a
        # host, we virtually consume resources on it so subsequent
        # selections can adjust accordingly.

        # Note: remember, we are using an iterator here. So only
        # traverse this list once. This can bite you if the hosts
        # are being scanned in a filter or weighing function.
        hosts = self._get_all_host_states(elevated)

        selected_hosts = []
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.num_instances
        for num in xrange(num_instances):
            # Filter local hosts based on requirements ...
            hosts = self.host_manager.get_filtered_hosts(hosts,
                    filter_properties, index=num)

The final steps of implementing this blueprint would be to change all
of the scheduler filters to access the original properties via object
notation instead of dict-notation.

As said above in the data model impact section, this blueprint is not targeting
to persist this object at the moment. We are also not yet removing the
`filter_properties` dictionary in this blueprint.

Assignee(s)
-----------

Primary assignee:
  bauzas

Other contributors:
  None

Work Items
----------

- Remove `instance_uuids` field from `request_spec` and bump a new version for
  the Scheduler RPC API

- Add request spec class to `nova/scheduler/request_spec.py` w/ unit tests

- Add a factory classmethod on `nova.scheduler.RequestSpec` that constructs a
  `RequestSpec` object from the *existing* set of instance type extra_specs,
  scheduler_hints, flavor and image objects that are supplied to the
  `nova.scheduler.utils.build_request_spec` function.

- Modify `FilterScheduler._schedule()` to construct a `RequestSpec` object
  from the supplied nested `request_spec` dictionary

- Convert all filter classes to operate against the `RequestSpec` object
  instead the nested `request_spec` dictionary.

- Add developer reference documentation for what the request spec models.

Dependencies
============

None.

Testing
=======

New unit tests for the request spec objects will be added. The existing unit
tests of the scheduler filters will be modified to access the `RequestSpec`
object in the `filter_properties` dictionary.

Documentation Impact
====================

Update any developer reference material that might be referencing the old
dictionary accesses.

References
==========

This blueprint is part of an overall effort to clean up, version, and stabilize
the interfaces between the nova-api, nova-scheduler, nova-conductor and
nova-compute daemons that involve scheduling and resource decisions.

See https://wiki.openstack.org/wiki/Gantt/kilo#Tasks for the list of all
blueprints targeted for Kilo.
