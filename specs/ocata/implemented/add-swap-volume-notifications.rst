..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Add swap volume notifications
=============================

https://blueprints.launchpad.net/nova/+spec/add-swap-volume-notifications

Add versioned notifications when updating volume attachment
(swapping volumes).

This blueprint was proposed and approved for Mitaka and Newton.
It was a specless blueprint.
But according to [1], if the change "needs more then one commit",
it needs a spec. So this spec is submitted.

[2][3] are patches implementing this function.

Problem description
===================

Currently no notifications are emitted when updating volume attachment
(swapping volumes).
Updating volume attachment is an asynchronous operation,
so it cannot be known via the API response whether it succeeds or not,
when it completes.

Use Cases
---------

Users or operators get whether the updating volume attachment operation
succeeds or not and when it completes.

Proposed change
===============

Add the following notifications.

* instance.volume_swap.start
* instance.volume_swap.end
* instance.volume_swap.error

Alternatives
------------

It is possible to know whether the operation completes or not
by calling the API that lists volume attachments (nova) or
get the volume status (cinder). But it is inefficient.

Data model impact
-----------------

No database schema change is required.

The following new objects will be added:

.. code-block:: python

    @nova_base.NovaObjectRegistry.register_notification
    class InstanceActionVolumeSwapPayload(InstanceActionPayload):
        VERSION = '1.0'

        fields = {
            'old_volume_id': fields.UUIDField(),
            'new_volume_id': fields.UUIDField(),
        }

.. code-block:: python

    @nova_base.NovaObjectRegistry.register_notification
    class InstanceActionVolumeSwapNotification(base.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'

        fields = {
            'payload': fields.ObjectField('InstanceActionVolumeSwapPayload')
        }

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

Add the following notifications.

* instance.volume_swap.start
* instance.volume_swap.end
* instance.volume_swap.error

Notification samples are included in [2] and [3] .

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

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  natsume-takashi

Work Items
----------

* Add 'instance.volume_swap.start' notification. [2]
* Add 'instance.volume_swap.end' notification. [2]
* Add 'instance.volume_swap.error' notification. [3]

Dependencies
============

None

Testing
=======

Add the following tests.

* Notification sample functional tests

Documentation Impact
====================

Versioned notification samples will be added to the Nova developer
documentation.

References
==========

* [1] Blueprints, Specs and Priorities - Specs

  - http://docs.openstack.org/developer/nova/blueprints.html#specs

* [2] Add swap volume notifications (start, end)

  - https://review.openstack.org/#/c/250283/

* [3] Add swap volume notifications (error)

  - https://review.openstack.org/#/c/328055/

History
=======

Note: For Mitaka and Newton, this blueprint was a specless blueprint.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Approved
   * - Newton
     - Reapproved
   * - Ocata
     - Reproposed
