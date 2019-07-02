..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Introduce Pending VM state
==========================
https://blueprints.launchpad.net/nova/+spec/introduce-pending-vm-state

This feature adds support for the ``PENDING`` server state. When the scheduler
determines there is no capacity available for the given request, and so the
instance is about to be routed into cell0, the server should be set into the
``PENDING`` state instead of ``ERROR`` if the operator wishes so. This will
allow the execution of subsequent actions transparently to the end user.

Problem description
===================

Use Cases
---------

As an operator, I want to enable an external -to Nova- service, triggered as
soon as a server's build request fails due to ``NoValidHost``, and try to free
up the requested resources.

If the outcome of the follow up actions is:

#. success, the external service will try to rebuild the instance::

        POST /servers/{server_id}/action
        {
            "rebuild": {
                "description": null,
                "imageRef": {image_id}
            }
        }

   .. note:: The rebuild api needs to be adapted to take care of instances that
             fail while building and are mapped to cell0. This change is
             considered out of scope for this spec and is being addressed by
             another spec [#]_.

#. failure, the external service will set the state of the instance to
   ``ERROR`` (using reset-state)::

        POST /servers/{server_id}/action
        {
            "os-resetState": {
                "state": "error"
            }
        }

In order to achieve that, transparently to the user, the instance should not
be set to the ``ERROR`` state but to the new ``PENDING`` state.

We need to clarify here that, as for all the other VM states, the end user
will be able to delete instances set to the ``PENDING`` state. Failures to the
follow up actions, caused by the deletion of instances in the new state, have
to be handled by the external service.

Proposed change
===============

#. Add the ``PENDING`` state in the ``InstanceState`` object.

#. Add the ``PENDING`` state in compute vm_states.

#. Add the ``PENDING`` state in the server ViewBuilder as a new progress
   status.

#. Add a configuration option that defaults to ``False`` in the DEFAULT group
   to enable the use of ``PENDING`` vm_state on ``NoValidHost`` events::

        CONF.use_pending_state

#. Add the following code in the conductor manager ``_bury_in_cell0`` method
   to make sure that the a vm is set to ``PENDING`` only when the operator has
   chosen so and the failure reported by the scheduler is a ``NoValidHost``::

        verify = isinstance(exc, exception.NoValidHost)

        if CONF.use_pending_state and verify:
            vm_state = vm_states.PENDING
        else:
            vm_state = vm_states.ERROR

        updates = {'vm_state': vm_state, 'task_state': None}

#. Add a new API microversion and Map the ``PENDING`` state to ``ERROR`` for
   requests to previous microversions. See `REST API impact`_.

Alternatives
------------

Follow the vendor data example and perform an asynchronous REST API call from
the Nova Conductor to the external service when enabled by the operator. But
having an asynchronous REST API call from the conductor would potentially have
performance impact.

Data model impact
-----------------

None.

REST API impact
---------------

A new API microversion is needed for this change. For the older microversions
the ``PENDING`` state will be mapped to the ``ERROR`` state.

Example responses for a server set to ``PENDING`` would be::

    GET /servers/detail (new microversion)
    {
       "servers":[
          {
             ...: ...,
             "name": "test",
             "id":"2dd26c1e-bc6f-45f6-83b3-2cb72ea026eb",
             "OS-EXT-STS:vm_state":"pending",
             "status":"PENDING",
             ...: ...
          }
       ]
    }

    GET /servers/detail (previous microversions)
    {
       "servers":[
          {
             ...: ...,
             "name": "test",
             "id":"2dd26c1e-bc6f-45f6-83b3-2cb72ea026eb",
             "OS-EXT-STS:vm_state":"error",
             "status":"ERROR",
             ...: ...
          }
       ]
    }


Security impact
---------------

None.

Notifications impact
--------------------

Firstly, the external third party service has to be notified when a server is
set to ``PENDING`` state. For this, the already existing versioned notification
``instance.update`` [#]_.

For the second part, a notification is needed in order to inform the external
service about a server's build procedure outcome. The plan is to use this
notification in order to enable the external Reaper service, to know where the
requested resources have to be freed up. The existing ``select_destinations``
versioned notification can be used [#]_.

Other end user impact
---------------------

From the new microversion that introduces the new instance state and beyond,
end users need to account for the possibility of instances going through the
PENDING state (which may or may not happen, depending on the way the operator
chooses to configure the cloud).

Performance Impact
------------------

None.

Other deployer impact
---------------------

There will be a new config option specifying if the ``PENDING`` state will be
used or not. It seems that the most appropriate place for this option is the
DEFAULT section.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <ttsiouts>

Other contributors:
  <johnthetubaguy>
  <strigazi>
  <belmoreira>

Work Items
----------

See `Proposed change`_.

Dependencies
============

None.

Testing
=======

Updating existing unit and functional tests should be enough to verify the
use of the new state.
New unit and functional tests have to be added to verify the new notification.

Documentation Impact
====================

#. The new configuration option as well as the meaning of the ``PENDING`` state
   should be documented.

#. Update the allowed state transitions documentation to include::

        BUILD to PENDING
        PENDING to BUILD
        PENDING to ERROR

#. Document that the responsibility of managing the instance's lifecycle is
   transferred to the external service as soon as the instance is set to the
   ``PENDING`` state.

#. Document that after the new microversion instances might go through the
   ``PENDING`` state as well, depending on whether the operator chooses to
   enable this state or not.

References
==========

.. [#] https://review.openstack.org/#/c/648686/

.. [#] https://github.com/openstack/nova/blob/a80bc66dc76acd9efbef269e68aef8a88662da9f/nova/notifications/objects/instance.py#L279

.. [#] https://github.com/openstack/nova/blob/a80bc66dc76acd9efbef269e68aef8a88662da9f/nova/notifications/objects/scheduler.py#L23

As discussed in the Dublin PTG:
https://etherpad.openstack.org/p/nova-ptg-rocky L472

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
   * - Stein
     - Re-proposed
   * - Train
     - Re-proposed
