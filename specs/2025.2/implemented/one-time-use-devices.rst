..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Support for "one time use" devices
==================================

https://blueprints.launchpad.net/nova/+spec/one-time-use-devices

As the use of direct-passthrough accelerator devices increases, so does the
need for some sort of post-use cleaning workflow between tenants. A NIC that
is passed directly through to a guest may need to have known-good firmware
re-written to it to make sure the previous user hadn't violated it in some
way. A GPU might have sensitive residue in memory that needs to be zeroed.
An NVMe device is a storage medium that needs to be wiped or discarded.

Problem description
===================

Currently there is no good way for operators to define and execute a
device-cleaning workflow outside of Nova. Further, Nova does not intend to
take on such tasks itself, in support of the long-term "no more orchestration"
goal.

Use Cases
---------

As an operator, I want to provide passthrough devices to instances with known-
safe firmware and device state.

As a special-purpose cloud operator, I may have specialized hardware that
requires special handling after use (power or bus resets, config
initialization, etc).

As a cloud operator, I want to provide fast direct-passthrough storage support,
but without risking information leakage between tenants.

As a cloud operator, I want to check the write-wear indicator on my passthrough
NVMe devices after each user to avoid returning devices over the safety
threshold to be allocated.


Proposed change
===============

Nova will support "one time use" devices. That is a device where we will
allocate it for a new instance only once. When that instance is deleted, the
device will not be returned to an allocatable state automatically (as would
normally happen) and instead remain in a reserved state until some action is
taken by the operator's own workflow to mark it as usable again. Making sure
such a device is not re-allocatable (until cleaned) is a potentially very
security-sensitive step that can not be missed, and it makes sense for Nova
to do this itself, even though it will not take on the actual task of doing
any device cleaning.

The annotation mechanism here will utilize the `reserved` inventory count,
on top of PCI-in-placement. Basically, when Nova goes to allocate the device
for the instance, it will follow up with a bump of the `reserved`` count. When
we go to de-allocate the device, we will not touch the `reserved` count, thus
leaving the resource provider for the device fully-reserved (and thus not
allocatable).

.. note::

  This is expected to be used for PCI-in-placement and PF devices only due to
  the one-to-one resource provider accounting. A future change could enable
  this for VFs through another mechanism if we determine a need.

Through whatever workflow the operator decides, they can clean the device, and
decrement the `reserved` count once they are ready for the device to rejoin
the pool of allocatable devices again. This would likely be listening to
notifications for deleted instances and scheduling such cleaning.

We will also introduce a new trait (tentatively called `HW_ONE_TIME_USE`) that
nova will add to resource providers that it is managing as one-time-use. This
will make it easier for operators to survey all the device providers that are
*potentially* in need of cleaning. This will not convey whether or not cleaning
is required (which is signaled by total=1,reserved=1,used=0) but rather that
this device *may* need cleaning if the conditions are correct.

Implementation
--------------
The reservation of a device (i.e. "burning" its one-time-use) will happen in
the compute node, (temporally) near where we do the claim and accounting in
the PCI tracker. This will minimize the window for failure after which the
device will be "burned" but not actually used by the instance. At the end of
`instance_claim()` in the resource tracker, we currently call `_update()`
which calls `_update_to_placement()`. There, we do some inventory and
allocation healing, including of placement-tracked PCI devices. Within this
inventory-healing routine, we will reserve PCI devices that are allocated since
we are already auditing (and healing/updating) inventory as needed.

.. note::

  From this point on, we will use the term "burned" to refer to a device that
  has been reserved such that it will not be re-allocated. This happens before
  the point at which the instance is able to run with it (in all situations)
  and remains in that state until an external action drops the reserved count
  back to zero. In other words, "burned" means ``reserved=total``.

By doing this in the above described way we will get synchronous reservation
of the devices (i.e. it will happen before the instance starts running) as
late as is reasonable. We will also get the ability to "heal" already-
allocated devices into reserved state if they happen to be marked as one-time-
use by the administrator at a later time.

Move operations will function similarly, as the `_move_claim()` method also
calls `_update()` synchronously after the local claims are completed. It should
be noted that a move of an instance with a one-time-use device will "burn" the
device on the destination as soon as it starts running there (i.e. when it
reaches the verify state) and a revert will not "un-burn" it.


Lifecycle Operations
--------------------

Technically one-time-use devices should be able to fully participate in all of
the instance lifecycle operations. There are some caveats however, so a few
cases are discussed below:

* Rebuild: The device can be re-used in place without any other action
* Evacuate: The original device will have been "burned" when the instance was
  booted and will remain as such after the original host is recovered and it
  removes the allocation for the original instance. The process of evacuation
  will allocate and burn a new device on the new host during the boot process.
* Cold migrate: A new device will allocated on the destination when the
  instance is being started there. Once the instance reaches the verify state,
  the destination's new device will be burned. On confirm, the source device
  will remain burned, and on revert, the destination device will have been
  burned. Note that state (i.e. data) on a stateful device will not be copied
  by Nova.
* Live migrate: If the device is already live migratable, then it will be be
  allowed, with the source device remaining "burned" after the operation
  completes and of course the new device on the destination will be burned
  in the process of the migration.

.. note::

  We will need a change in placement to allow over-subscribed resource
  providers to progress "towards safety", meaning "become less
  over-subscribed". For one-time-use devices we must be allowed to swap the
  instance's allocation for the migration UUID on the source node, even though
  the provider is already technically over-subscribed due to the device being
  reserved. Note that this is already a problem in Nova/Placement and we have
  multiple bugs reported against this, where a change in allocation ratio
  resulting in over-subscription will prevent operators from migrating
  instances away. We need to fix this anyway, and that fix will also apply to
  one-time-use devices. Until then, migrate operations (cold, resize, and live)
  will be (implicitly) blocked for one-time-use devices. Fixing this will be
  slightly outside the scope of this spec, but expect to be completed in
  parallel or just afterwards.

.. note::

  Evacuation without consulting the scheduler may result in us sending an
  instance to a host requesting a PCI device for which there was no prior
  check for whether it is allocatable (i.e. already burned). We need to make
  sure that whatever happens on the compute node in this case will fail before
  assigning the device to an instance (which should happen during
  ``ResourceTracker._update()`` as part of the allocation healing).

Alternatives
------------

One alternative is to do nothing and continue to operate as we do today. Nova
intentionally does not provide any device cleaning ability, nor any real hooks
or integration for operators desiring it.

Another alternative is to say that this is in the scope of Cyborg, it is. Nova
officially recognizes Cyborg as the solution for external, stateful device
prep, cleaning, and lifecycle management and this does not change that. The
one-time-use-devices idea sits somewhere in the middle of "do nothing" and
"do it in Cyborg" in that it's a _very_ small change to nova to allow an
external integration for which we have existing APIs for people to do what
they need in a simpler case. Certainly from the perspective of an operator
where support for their device does not exist in Cyborg, a simpler workflow
would be easier to craft a homegrown solution. For an operator with bespoke
(maybe scientific) hardware, requiring them to write a full Cyborg driver in
order to call a shell script after each use is a big ask.

Data model impact
-----------------

There should be no data model impact if we use the existing PCI `dev_spec` to
flag a device as `one_time_use=(yes|no)`. This is a similar approach to the
recent migrate-vfio-devices-using-kernel-variant-drivers spec which allows
operators to flag them as `live_migratable=(yes|no)`.

REST API impact
---------------

None.

Security impact
---------------

No direct security impact, although it will theoretically allow operators to
improve security of device-passthrough workloads by sanitizing or
re-initializing their devices between uses.

Notifications impact
--------------------

None.


Other end user impact
---------------------

None (invisible to users).

Performance Impact
------------------

This will involve a single additional call to placement to update the
inventory after we allocate the device. This should be negligible in terms of
performance impact, and the error handling will be identical to that of the
case where we fail to do the allocation itself.

Other deployer impact
---------------------

Deployers who do not wish to use this feature will not be impacted. Those
that do will be able to enable this via config for their PCI devices and
write their own external integrations based on the assumption that devices
will remain reserved after allocation.

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
  danms

Feature Liaison
---------------

Feature liaison:
  N/A

Work Items
----------

* Parse `one_time_use` from `[pci]dev_spec` config
* Add code to bump reserved count when we update allocations and inventories
  for the PCI device in placement in the `instance_claim()` path
* Add documentation and a sample cleanup listener script
* Work on squashing placement `bug_1943191`__ (probably in parallel)

.. __: https://bugs.launchpad.net/nova/+bug/1943191

Dependencies
============

This has a soft dependency on a fix to Placement that allows swapping an
allocation while over-subscribed. While not strictly required, fixing this
long-standing issue will enable cold migration of one-time-use devices.

Testing
=======

This will be tested fully in unit/functional tests since it requires a real
device to test with tempest.

One-off testing with real devices will be performed locally during review and
submission.

Documentation Impact
====================

Operator documentation will be added explaining the meaning of the flag, and
the guarantees it makes that the operators can rely on. A sample script for
processing device cleanup will be provided as a sample to start from, but
extensive documentation on how to that robustly will be left to the consumer.

References
==========

The mechanism for tagging devices is nearly identical to this recent effort:

https://specs.openstack.org/openstack/nova-specs/specs/2025.1/approved/migrate-vfio-devices-using-kernel-variant-drivers.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.2 Flamingo
     - Introduced
