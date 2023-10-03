..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Use extend volume completion action
===================================

https://blueprints.launchpad.net/nova/+spec/assisted-volume-extend

This blueprint proposes to use the ``os-extend_volume_completion`` volume
action that has been proposed for Cinder in [3]_, to provide feedback on
success or failure when handling ``volume-extended`` external server events.

Problem description
===================

Many remotefs-based volume drivers in Cinder use the ``qemu-img resize``
command to extend volume files.
However, when the volume is attached to a guest, QEMU will lock the file and
``qemu-img`` will be unable to resize it.

In this case, only the QEMU process holding the lock can resize the volume,
which can be triggered through the QEMU monitor command ``block-resize``.

There is currently no adequate way for Cinder to use this feature, so the NFS,
NetApp NFS, Powerstore NFS, and Quobyte volume drivers all disable extending
attached volumes.

Use Cases
---------

As a user, I want to extend a NFS/NetApp NFS/Powerstore NFS/Quobyte volume
while it is attached to an instance and I want the volume size and status to
reflect the success or failure of the operation.

Proposed change
===============

Nova's libvirt driver uses the ``block-resize`` command when handling the
``volume-extended`` external server event, to inform QEMU that the size of an
attached volume has changed.
It is in principle also capable of extending a volume file, but is currently
unable to provide feedback to Cinder on the success of the operation.

Currently, Cinder will send the ``volume-extended`` external server event to
Nova only after it has finalized the extend operation and reset the volume
status from ``extending`` back to ``in-use``.

With [3]_, Cinder will allow volume drivers to hold off finalizing the extend
operation and leave the volume status as ``extending``, until after it has
send the ``volume-extended`` event and received feedback from Nova in form of
the ``os-extend_volume_completion`` volume action, with an ``error`` argument
indicating whether to finalize or to roll back the operation.

This will currently affect only the volume drivers mentioned above, all of
which did not previously support online extend.
All other drivers will continue to send the ``volume-extended`` event after
finalizing the operation and resetting to ``in-use`` status, and will not
expect a ``os-extend_volume_completion`` volume action.

Compute Agent
-------------

Nova's compute agent will use the volume status to differentiate between the
two behaviors when handling ``volume-extended`` events:

* If the volume status is ``extending``, then it will attempt to read
  ``extend_new_size`` from the volume's metadata and use this value as the
  new size of the volume, instead of the volume size field.

  After successfully extending the volume, it will call the extend volume
  completion action of the volume, with ``"error": false``.

  If anything goes wrong, including ``extend_new_size`` being missing from the
  metadata, or being smaller than the current size of the volume, it will
  log the error and call the ``os-extend_volume_completion`` action with
  ``"error": true``, so Cinder can roll back the operation.

* For any other volume status, including ``in-use``, the event will be handled
  as before.

API
---

Nova's API will introduce a new microversion, so that Cinder can make sure the
new behavior is available, before leaving an extend operation unfinished.

To handle older compute agents during a rolling upgrade, the API will also
check the compute service version of the target agent when receiving a
``volume-extended`` event with the new microversion.
If a target compute agent is too old to support the feature, the API will
discard the event and call the ``os-extend_volume_completion`` action with
``"error": true``.

Alternatives
------------

* A previous change tried to use the ``volume-extended`` external server event
  to support online extend for the NFS driver [1]_, but did not rely on
  feedback from Nova to Cinder at all.
  Instead, it would just set the new size of the volume, change the status
  back to ``in-use``, notify Nova, and hope for the best.

  If anything went wrong on Nova's side, this would still result in a volume
  state indicating that the operation was successful, which is not acceptable.

* A previous version of this spec proposed a new synchronous API in Nova [2]_,
  that would directly call ``CompVirtAPI.extend_image`` of the nova-compute
  instance managing the guest that a volume was attached to.
  This API would provide a single mechanism to trigger the resize operation,
  communicate the new size to Nova, and get feedback on the success of the
  operation.

  The problem with a synchronous API is, that RPC and API timeouts limit the
  maximum time an extend operation can take.
  For QEMU, this seemed to be acceptable, because storage preallocation is
  hard disabled for the ``block-resize`` command, and because all currently
  plausible file systems support sparse file operations.

  However, this may not be true for other volume or virt drivers that might
  require this API in the future.
  It would also break with the established pattern of asynchronous
  coordination between Nova and Cinder, which includes the assisted snapshot
  and volume migration features.

* Following this pattern, we could make the proposed API asynchronous and use
  a new callback in Cinder, similar to Nova's ``os-assisted-volume-snapshots``
  API, which uses the ``os-update_snapshot_status`` snapshot action to provide
  feedback to Cinder.

  The function of the new Nova API would then just be to trigger the operation
  and to communicate the new size.
  The question is then, whether that warrants adding a new API to Nova, since
  there are existing mechanisms that could be used for either.

* The existing mechanism for triggering the extend operation in Nova is of
  course the ``volume-extended`` external server event.
  Using it for this purpose, as this spec proposes, requires the target size
  to be transferred separately, because external server events only have a
  single text field that is freely usable, which for ``volume-extended``
  is already used for the volume ID.

  Besides storing it in the admin metadata, as [3]_ and this spec propose,
  there is also the option of updating the size field of the volume, as [1]_
  was essentially doing.

  This would require the volume size field to be reset on a failure.
  If an error response from Nova was lost, the volume would just keep the new
  size.
  We would need to extend ``os-reset_status`` to allow a size reset, or
  something similar to clean up volumes like this.
  This would be possible, but updating the size field only after the volume
  was successfully extended seems like a cleaner solution.

* We could also extend the external server event API to accept additional data
  for events, and use this to communicate the new size to Nova.

  This option was judged favorably by reviewers on the previous version of
  this spec, [2]_, but it would be a more complex change to the Nova API.

  However, if additional data fields become available in a future version of
  the external server event API, it would be a relatively minor change to use
  this instead of volume metadata.

Data model impact
-----------------

None

REST API impact
---------------

The behavior of the external server event API will change.

* If Nova receives a ``volume-extended`` event, and the referenced volume has
  status of ``extending``, Nova will look for the ``extend_new_size`` key in
  the volume metadata, and use this instead of the volume size field as the
  target size to update the block device mapping and to pass to the virt
  driver's ``extend_volume`` method.

  Nova will also attempt to call Cinder's new ``os-extend_volume_completion``
  volume action proposed in [3]_ to let Cinder know if the operation was
  successful or not.

* Otherwise, the API will behave as before.

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

Checking the target compute service version allows the API to handle rolling
upgrades gracefully.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  kgube

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None yet

Work Items
----------

* Update the external server event API to check the target compute service
  version for ``volume-extended`` events.
* Update the ``ComputeVirtAPI.extend_volume`` method to follow the behavior
  outlined in `Compute Agent`_.
* Add unit tests.
* Adapt NFS job in the Nova gate to validate online extend.

Dependencies
============

* The extend volume completion action [3]_

Testing
=======

We should test that the ``os-extend_volume_completion`` gets called correctly
in all possible error or success condition if a volume has ``extending``
status.

We should test the case that the call to ``os-extend_volume_completion`` fails.

We also need to test that ``volume-extended`` continues to be handled correctly
for volumes not in ``extending`` status.

Documentation Impact
====================

The new behavior of the ``volume-extended`` event should be added to the
documentation of the external server event API.

References
==========

.. [1] https://review.opendev.org/c/openstack/cinder/+/739079
.. [2] https://review.opendev.org/c/openstack/nova-specs/+/855490/6
.. [3] https://review.opendev.org/c/openstack/cinder-specs/+/877230

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Accepted
   * - 2023.2 Bobcat
     - Reproposed
