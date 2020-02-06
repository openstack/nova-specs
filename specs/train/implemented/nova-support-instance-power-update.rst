..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Support server power state update through external event
========================================================

https://blueprints.launchpad.net/nova/+spec/nova-support-instance-power-update

This spec aims at providing more flexibility for operators regarding the
``_sync_power_states`` periodic task (which aligns the server states
between the database and the hypervisor) in nova with respect to use cases for
the baremetal instances (ironic). It proposes to make this periodic power
sync's "source of truth" configurable, depending on situations, like to allow
the physical instance to be the source of truth and make nova update its
database rather than enforcing the database state onto the physical instance.

Problem description
===================

As a part of this periodic power sync between nova and ironic, when a physical
instance goes down during situations like a power outage or when the hardware
team with direct physical access to the machine does system repairs, the
instance is put into the ``SHUTDOWN`` `state by nova`_ in its database since
the hypervisor is regarded as the source of truth. However when the physical
instance comes up again through non-nova-api methods like the IPMI access or
the power button, it will be put into the ``SHUTDOWN`` state `again by nova`_
since the database is regarded as the source of truth here (asynchronous).
This can cause operational inconvenience and inconsistency between
cloud operators and repair teams. Currently the only way to avoid this is by
completely disabling the power synchronisation which is not recommended.

Note that ironic allows a node to be put into the ``maintenance mode`` by which
that `node will be excluded`_ from nova's ``_sync_power_states`` periodic task.
This covers predictable events like scheduled repairs but does not help with
unforseen events such as power failures.

Use Cases
---------

As an operator I would like to have my physical instance's power state as
``RUNNING`` and not be put in ``SHUTDOWN`` by nova once it comes back up after
a system repair or a power outage via IPMI access or direct physical access.

Proposed change
===============

To make nova hear the physical instance come up (or go down) and regard it as
the source of truth, the idea is to add a ``power-update`` event name to the
``os-server-external-events`` nova API. This event will be `sent by ironic`_
whenever there is a change in the power state of the down physical instance
i.e. when the physical instance comes up (or goes down) on the ironic side
and ironic trusts the hardware instead of the database as the source of
truth. Nova will be listening for the ``power-update`` event from ironic
using the existing external-events API endpoint as discussed in the
`nova-ironic cross project session at the Denver2018 PTG`_.

On the nova side, once such an event for a physical instance is received from
ironic, it will be routed to the virt driver. In the virt driver we will add a
new ``driver.power_update_event`` method which will be in a ``NotImplemented``
state for all driver types except ironic. So if we receive a power-update for
an instance backed by a non-ironic driver we will log an error. In the ironic
driver this method will update the ``vm_state`` and ``power_state`` fields of
that instance to ``ACTIVE`` and ``RUNNING`` (or ``STOPPED`` and ``SHUTDOWN``)
in the nova database. Note that before routing the call to the driver the
notifications and instance actions for the power update will be handled by nova
similar to the normal start/stop operations.

Even with this proposed change, depending on the order of occurrence of events
we could still have race conditions where the periodic task is already running
and it overrides the ``power-update`` event. However this window is quite
small. To avoid the periodic task and power-update event from stepping over
each other `a lock can be shared`_ between them.

Alternatives
------------

There have been failed attempts at fixing this problem in the past like
allowing `admins to decide what action`_ to take when the states conflict or
allowing `admins to reboot instances`_ when the states conflict.

Data model impact
-----------------

A new event name will be added to ``objects.InstanceExternalEvent.name`` enum
called ``power-update``.

REST API impact
---------------

The proposed JSON request body for the new "power-update" event is::

    {
        "events": [
            {
                "name": "power-update",
                "server_uuid": "3df201cf-2451-44f2-8d25-a4ca826fc1f3",
                "tag": target_power_state
            }
        ]
    }

Definition of fields:

name
    Name of the event. (“power-update” for this feature).
server_uuid
    Server UUID of the physical instance whose power_state needs to be updated
    in the database.
tag
    The target_power_state values will either be "POWER_ON" (which maps to
    "RUNNING" in nova) or "POWER_OFF" (which maps to "SHUTDOWN" in nova).

The proposed JSON response body for the new "power-update" event is::

    {
        "events": [
            {
                "code": 200,
                "name": "power-update",
                "server_uuid": "3df201cf-2451-44f2-8d25-a4ca826fc1f3",
                "status": "completed",
                "tag": target_power_state
            }
        ]
    }

Definition of fields:

name
  Name of the event. ("power-update" for this feature).
status
  Event status. Possible values:
    * "completed" if accepted by Nova
    * "failed" if a failure is encountered
code
  Event result code. Possible values:
    * 200 means accepted
    * 400 means the request is missing required parameter
    * 404 means the server could not be found
    * 422 means the event cannot be processed because the instance was found
      to not be associated to a host.
server_uuid
  Same value as provided in original request.
tag
  Same value as provided in original request.

This powering up/down of instances on the nova side will be made visible
through the ``GET /servers/{server_id}/os-instance-actions`` and
``GET /servers/{server_id}/os-instance-actions/{request_id}`` API calls for the
users (by default admins and owners of the server).

Security impact
---------------

None.

Notifications impact
--------------------

None.

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

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <tssurya>

Other contributors:
  <wiebalck>

Work Items
----------

#. Add the new external-event type.
#. Make the necessary changes in the compute API and manager for the update of
   the power and vm states of the instance on receiving an event from ironic.
#. Add the new microversion and config option.

Dependencies
============

* The client side changes needed for the events to be `sent by ironic`_ when
  the physical instance comes up or goes down.

Testing
=======

Unit and functional tests to verify the new ``power-update`` event's working.

Documentation Impact
====================

Update the compute API reference documentation with the new power-update event.

References
==========

.. _sent by ironic: https://storyboard.openstack.org/#!/story/2004969

.. _nova-ironic cross project session at the Denver2018 PTG: http://lists.openstack.org/pipermail/openstack-dev/2018-September/135122.html

.. _admins to decide what action: https://review.openstack.org/#/c/190047/

.. _admins to reboot instances: https://review.openstack.org/#/c/218975/

.. _state by nova: https://github.com/openstack/nova/blob/d42a007425d9adb691134137e1e0b7dda356df62/nova/compute/manager.py#L7871

.. _again by nova: https://github.com/openstack/nova/blob/d42a007425d9adb691134137e1e0b7dda356df62/nova/compute/manager.py#L7915

.. _node will be excluded: https://github.com/openstack/ironic/blob/84dfc151ea3091c5683b58a88e2b99302b03f5be/ironic/conductor/manager.py#L1754

.. _a lock can be shared: http://eavesdrop.openstack.org/irclogs/%23openstack-ironic/%23openstack-ironic.2019-03-25.log.html#t2019-03-25T14:11:04

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
