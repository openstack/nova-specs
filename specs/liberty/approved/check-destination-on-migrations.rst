..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Check the destination host when migrating or evacuating
=======================================================

https://blueprints.launchpad.net/nova/+spec/check-destination-on-migrations

Provide a way to make sure that resource allocation is consistent for all
operations, even if a destination host is provided.

Problem description
===================

Live migrations and evacuations allow the possibility to either specify a
destination host or not. The former option totally bypasses the scheduler by
calling the destination Compute RPC API directly.

Unfortunately, there are some cases when migrating a VM, it breaks the
scheduler rules so it so it potentially breaks future boot requests due
to some constraints not enforced when migrating/evacuating (like allocation
ratios).

We should modify that logic to explicitly call the Scheduler any time a move
(ie. either a live-migration or an evacuation) is requested (whether the
destination host is provided or not) so that the Scheduler would verify the
destination host thru all the enabled filters and if successful consume the
instance usage from its internal HostState.

That said, we also understand that there are usecases where an
operator wants to move an instance manually and not call the scheduler, even
if the operator knows that he explicitly breaks scheduler rules (eg. a
filter not passing, an affinity policy violated or an instance taking an
already allocated pCPU in the context of CPU pinning).

Use Cases
----------

Some of the normal usecases (verifying the destination) could be :

As an operator, I want to make sure that the destination host I'm providing
when live migrating a specific instance would be correct and wouldn't break my
internal cloud because of a discrepancy between how I calculate the destination
host capacity and how the scheduler is taking in account memory allocation
ratio (see the References section below)

As an operator, I want to make sure that live-migrating an instance to a
specific destination wouldn't impact my existing instances running on that
destination host because of some affinity that I missed.


Project Priority
-----------------

Part of the 'scheduler' priority accepted for Liberty.

Proposed change
===============

This spec goes beyond what the persist-request-spec blueprint [1] by making
sure that before each call to select_destinations(), the RequestSpec object is
read from the current instance to schedule and will make sure that after the
result of select_destinations(), the RequestSpec object will be persisted.

That way, we will be able to get the original RequestSpec from the
corresponding instance from the user creating the VM including the scheduler
hints. Given that, we propose to amend the RequestSpec object to include a new
field called ``requested_destination`` which would be a ComputeNode object (at
least having the host and hypervisor_hostname fields set) and would be set by
the conductor for each method (here live-migrate and rebuild_instance
respectively) accepting an optional destination host.

Note that this new field would nothing have in common with a migration object
or an Instance.host field, since it would just be a reference to an equivalent
scheduler hint saying 'I want to go there' (and not the ugly force_hosts
information passed as an Availability Zone hack...).

It will be the duty of the conductor (within the live_migrate and evacuate
methods) to get the RequestSpec related to the instance, add the
``requested_destination`` field, set the related Migration object to
``scheduled`` and call the scheduler's ``select_destinations`` method.
The last step would be of course to store the updated RequestSpec object.
If the requested destination is unacceptable for the scheduler, then the
conductor will change the Migration status to ``conflict``.

The idea behind that is that the Scheduler would check that field in the
_schedule() method of FilterScheduler and would then just call the filters only
for that destination.

As the RequestSpec object blueprint cares about backwards compatibility by
providing the legacy ``request_spec`` and ``filter_properties`` to the old
``select_destinations`` API method, we wouldn't pass the new
``requested_destination`` field as a key for the request_spec.


Since this BP also provides a way for operators to bypass the Scheduler, we
will amend the API for all migrations including a destination host by adding an
extra request body argument called ``force`` (accepting True or False,
defaulted to False) and the corresponding CLI methods will expose that
``force`` option. If the microversion asked by the client is older than the
version providing the field, then it won't be passed (neither True or False,
rather the key won't exist) to the conductor so the conductor won't call the
scheduler - to keep the existing behaviour (see the REST API section below for
further details).

In order to keep track of those forced calls, we propose to log as an instance
action the fact that the migration has been forced so that the operator could
potentially reschedule the instance later on if he wishes. For that, we propose
to add two new possible actions, called ``FORCED_MIGRATE`` (when live-migrating
) and ``FORCED_REBUILD`` (when evacuating)
That way means that an operator can get all the instances having either
``FORCED_MIGRATE`` or ``FORCED_REBUILD`` just by calling the
/os-instance-actions API resource for each instance, and we could also later
add a new blueprint (out of that spec scope) for getting the list of instances
having the last specific action set to something (here FORCED_something).

Alternatives
------------

We could just provide a way to call the scheduler for having an answer if the
destination host is valid or not, but it wouldn't consume the instance usage
which is from our perspective the key problem with the existing design.


Data model impact
-----------------

None.

REST API impact
---------------

The proposed change just updates the POST request body for the
``os-migrateLive`` and ``evacuate`` actions to include the
optional ``force`` boolean field defaulted to False if the request has a
minimum version.

Depending on whether the ``host`` and ``force`` fields are set or null, the
actions and return codes are:

- If a host parameter is supplied in the request body, the scheduler will now
  be asked to verify that the requested target compute node is actually able to
  accommodate  the request, including honouring all previously-used scheduler
  hints. If the scheduler determines the request cannot be accommodated by the
  requested target host node, the related Migration object will change the
  ``status`` field to ``conflict``.

- If a host parameter is supplied in the request body, a new --force parameter
  may also be supplied in the request body. If present, the scheduler shall
  **not** be consulted to determine if the target compute node can be
  accommodated, and no 409 Conflict would be returned to the user.

- If --force parameter is supplied in the request body but the host parameter
  is either null (for live-migrate) or not provided (for evacuate), then an
  HTTP 400 Bad Request will be served to the user.

Of course, since it's a new request body attribute, it will get a new API
microversion, meaning that if the attribute is not provided, the scheduler
won't be called by the conductor (to keep the existing behaviour where setting
a host bypasses the scheduler).

* JSON schema definition for the body data of ``os-migrateLive``:

::

  migrate_live = {
      'type': 'object',
      'properties': {
          'os-migrateLive': {
              'type': 'object',
              'properties': {
                  'block_migration': parameter_types.boolean,
                  'disk_over_commit': parameter_types.boolean,
                  'host': host,
                  'force': parameter_types.boolean
              },
              'required': ['block_migration', 'disk_over_commit', 'host'],
              'additionalProperties': False,
          },
      },
      'required': ['os-migrateLive'],
      'additionalProperties': False,
  }


* JSON schema definition for the body data of ``evacuate``:

::

  evacuate = {
      'type': 'object',
      'properties': {
          'evacuate': {
              'type': 'object',
              'properties': {
                  'host': parameter_types.hostname,
                  'force': parameter_types.boolean,
                  'onSharedStorage': parameter_types.boolean,
                  'adminPass': parameter_types.admin_password,
              },
              'required': ['onSharedStorage'],
              'additionalProperties': False,
          },
      },
      'required': ['evacuate'],
      'additionalProperties': False,
  }


* There should be no policy change as we're not changing the action by itself
  but rather just providing a new option.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Python-novaclient will accept a ``force`` option for the following methods :

 - evacuate
 - live-migrate

Performance Impact
------------------

A new RPC call will be done by default when migrating or evacuating
but it shouldn't really impact the performance since it's the normal behaviour
for a general migration. In order to leave that RPC asynchronous from the API
query, we won't give the result of the check within the original request, but
rather modify the Migration object status (see the REST API impact section
above).

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza


Work Items
----------

- Read any existing RequestSpec before calling ``select_destinations()`` in all
  the conductor methods calling it
- Amend RequestSpec object with ``requested_destination`` field
- Modify conductor methods for evacuate and live_migrate to fill in
  ``requested_destination``, call ``scheduler_client.select_destinations()``
  and persist the amended RequestSpec object right after the call.
- Modify FilterScheduler._schedule() to introspect ``requested_destination``
  and call filters for only that host if so.
- Extend the API (and bump a new version) to add a ``force`` attribute for both
  above API resources with the appropriate behaviours.
- Bypass the scheduler if the flag is set and log either ``FORCED_REBUILD`` or
  ``FORCED_MIGRATE`` action.
- Add a new ``force`` option to python-novaclient and expose it in CLI for both
  ``evacuate`` and ``live-migrate`` commands


Dependencies
============

As said above in the proposal, since scheduler hints are part of the request
and are not persisted yet, we need to depend on persisting the RequestSpec
object [1] before calling ``select_destinations()`` so that a future migration
would read that RequestSpec and provide it again.


Testing
=======

API samples will need to be updated and unittests will cover the behaviour.
In-tree functional tests will be amended to cover that option.

Documentation Impact
====================

As said, API samples will be modified to include the new attribute.


References
==========

[1] http://specs.openstack.org/openstack/nova-specs/specs/liberty/approved/persist-request-spec.html

Lots of bugs are mentioning the caveat we described above. Below are the ones
I identified and who will be closed once the spec implementation lands :

- https://bugs.launchpad.net/nova/+bug/1451831
  Specifying a destination node with nova live_migration does not take into
  account overcommit setting (ram_allocation_ratio)
- https://bugs.launchpad.net/nova/+bug/1214943
  Live migration should use the same memory over subscription logic as instance
  boot
- https://bugs.launchpad.net/nova/+bug/1452568
  nova allows to live-migrate instance from one availability zone to another
