..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Use Cinder's new Attach/Dettach APIs
=====================================

https://blueprints.launchpad.net/nova/+spec/cinder-new-attach-apis

Make Nova use Cinder's new attach/dettach APIs.

Problem description
===================

In attempting to implement Cinder multi-attach and trying to get live
migration working with all drivers, it has become clear Cinder and Nova
interaction is not well understood, and that is leading to both bugs
and issues when trying to evolve the interaction between the two projects.

Lets create a new clean interface between Nova and Cinder.

You can see details on the new Cinder API here:
http://specs.openstack.org/openstack/cinder-specs/specs/ocata/add-new-attach-apis.html

Use Cases
---------

The main API actions to consider are:

* Attach a volume to an instance, including during spawning an instance,
  and calling os-brick to (optionally) connect the volume backend to the
  hypervisor.
  The connect is optional because when there is a shared connection from the
  host to the volume backend, the backend may already be attached.
* Detach volume from an instance, including (optionally) calling os-brick to
  disconnect the volume from the hypervisor host.
* Live-migrate an instance, involves setting up the volume connection on the
  destination host, before kicking off the live-migrate, then removing source
  host connections once the live-migrate has completed. If there is a rollback
  the destination host connection is removed.
* Migrate and resize are very similar to live-migrate, from this new view of
  the world.
* Evacuate, we know the old host is no longer running, and we need to attach
  the volume to a new host.
* Shelve, we want the volume to stay logically attached to the instance, but
  we also need to detach it from the host when the instance is offloaded.
* Attach/Detach a volume attached to a shelved instance
* Use swap volume to migrate a volume between two different Cinder backends.

In particular, please note:

* Volume attachment is specific to a host uuid, instance uuid, and volume uuid
* You can have multiple attachments to the same volume, to different instances
  (on the same host or different hosts), when the volume is marked
  multi_attach=True
* For the same instance uuid and volume uuid, you can have connections on two
  different hosts, even when multi_attach=False. This is generally used when
  moving a VM.
* Volume connections on a host can be shared with other volumes that are
  connected to the same volume backend, depending on the chosen driver.
  As such, need to take care when removing that connection, and not adding two
  connections by mistake and not removing an in use connection too early.
  Cinder needs to provide extra information to Nova, in particular, for each
  attachment, if the connection is shared, and if so, who that connection is
  currently shared with.

Proposed change
===============

Cinder now has two different API flows for attach/detach. We need a way to
switch from the old API to the new API without affecting any existing
instances.

Firstly, we need to decide when it is safe to use the new API. We need to have
the Cinder v3 API configured, and that endpoint should have the micro-version
v3.27 available. In addition we should only use the new API when all of the
nova-compute nodes have been upgraded. We can detect that by looking up the
minimum service version relating to when we add the support for the new
Cinder API. Note, this means we will probably need to increment the service
version so we can explicitly detect the support for the new Cinder API.

If we allow the use of the new API, we can use that for all new attachments.
When adding a new attachments we:

* (api) call attachment_create, with no connector, before API call returns.
  BDM record is updated with attachment_id.
  Note, if the volume is not multi_attach=True, it will only allow one
  instance_uuid to be associated with each volume. While the long term aim
  is to enable multi-attach, this spec will not attach to any volume that has
  multi-attach=True. While we could still make a single attachment to the
  volume, as we rely on cinder to restrict the number of attachments to the
  volume, for safety we shouldn't allow any attachments if multi_attach=True
  until we have that support fully implemented in Nova.
* (compute) get connector info and use that to call attachment_update.
  The API now returns with all the information that needs to be given to
  os-brick to attach the volume backend, and how to attach the VM to that
  connection to the volume backend.
* (compute) Before we can actually connect to the volume we need to wait for
  the volume to be ready and fully provisioned. If we timeout waiting for the
  volume to be ready, we fail here and delete the attachment. If this is the
  first boot of the instance, that will put the instance into the ERROR state.
  If the volume is ready, we can continue with the attach process.
* (compute) use os-brick to connect to the volume backend.
  If there are any errors, attempt to call os-brick disconnect
  (to double check it is fully cleaned up) and then remove the attachment
  in Cinder. If there are any issues in the rollback, put instance into the
  ERROR state.
* (compute) now the backend is connected, and the volume is ready, we can
  attach the backend connection to the VM in the usual way.

For a detach:

* (compute) if attachment_id is set in the BDM, we use the new detach flow,
  otherwise we fall back to the old detach flow. The new flow is...
* (api) usual checks to see if request is valid
* (compute) detach volume from VM, if fails stop request here
* (compute) call os-brick to disconnect from the volume backend
* (compute) if success, attachment_remove is called.
  If there was an error, we add an instance fault
  and set the instance into the error state.

As above, we can use the presence of the attachment_id in the BDM to decide
if the attachment was made using the new or old flow. Long term we want to
migrate all existing attachments to a new style attachment, but this is left
for a later spec.

Live-migrate
------------

During live-migration, we start the process by ensuring the volume is attached
on both the source and destination. When a volume is multi_attach=False, and
we are about to start live-migrating VM1, you get a situation like this ::

    +-------------------+   +-------------------+
    |                   |   |                   |
    | +------------+    |   | +--------------+  |
    | |VM1 (active)|    |   | |VM1 (inactive)|  |
    | +---+--------+    |   | +--+-----------+  |
    |     |             |   |    |              |
    |     | Host 1      |   |    |  Host 2      |
    +-------------------+   +-------------------+
          |                      |
          +-----------+----------+
                      |
                      |
         +---------------------------+
         |            |              |
         |  +---------+---------+    |
         |  | VolA              |    |
         |  +-------------------+    |
         |                           |
         |    Cinder Backend 1       |
         |                           |
         +---------------------------+

Note, in cinder we end up with two attachments for this multi_attach=False
volume:

* attachment 1: VolA, VM1, Host 1
* attachment 2: VolA, VM1, Host 2

Logically we have two attachments to the one non-multi-attach volume. Both
attachments are related to vm1, but there is an attachment for both the
source and destination host for the duration of the live-migration.
Note both attachments are associated with the same instance uuid,
which is why the two attachments are allowed even though multi_attach=False.

Should the live-migration succeed, we will delete attachment 1 (i.e. source
host attachment, host 1) and we are left with just attachment 2
(i.e. destination host attachment, host 2). If there are any failures with
os-brick disconnect on the source host, we put the instance into the ERROR
state and don't delete the attachment in Cinder. We do this to signal to the
operator that something needs manually fixing. We also put the migration into
the error state, as we would even if a failure had a clean rollback.

If we have any failures in the live-migration such that the instance is still
running on host 1, we do the opposite of the above. We attempt os-brick
disconnect on host 2. If success we delete attachment 2, otherwise put the
instance into the ERROR state. If the rollback succeeds we are back to one
attachment again, but in this case its attachment 1.

So for volumes that have an attachment_id in their BDM, we follow this new
flow of API calls Cinder:

* (destination) get connector, and create new attachment
* (destination) attach the volume backend
* (source) kicks off live-migration

If live-migration succeeds:

* (source) call os-brick to disconnect
* (source) if success, delete the attachment, otherwise put the
  instance into an ERROR state

If live-migration rolls back due to an abort or similar:

* (destination) call os-brick to disconnect
* (destination) if success, delete the attachment, otherwise put the
  instance into an ERROR state

Migrate
-------

Similar to live-migrate, at the start of the migration we have attachments
for both the source and destination node. On calling confirm resize we do
a detach on source, a call to revert resize and its detach on destination.

Evacuate
--------

When you call evacuate, and there is a volume that has an attachment_id in its
BDM, we follow this new flow:

* (source) Nothing happens on the source, it is assumed the administrator
  has already fenced the host, and confirmed that by calling force host down.
* (destination) Create a second attachment for this instance_uuid for
  any attached volumes
* (destination) Follow the usual volume attach flow
* (destination) Now delete the old attachment to ensure Cinder cleans up any
  resources relating to that connection. It is similar to how we call
  terminate_connection today, except we must call this after creating the
  new attachment to ensure the volume is always reserved to this instance
  during the whole of the evacuate process.
* (operator) should the source host never be started, the instances that
  have been evacuated are detected in the usual way (using the migration
  record created when evacuate is called). This may leave some things not
  cleaned up by os-brick, but that is fairly safe, and we are in a no worse
  situation than we are today.

Shelve and Unshelve
-------------------

When a volume attached to an instance has an attachment_id in the BDM, we
follow this new flow of calls to the Cinder API.
Note: it is possible to have both old flow and new flow volumes attached to
the one instance that is getting shelved.

When offloading from an old host, we first add a new attachment (with no
connector set) then perform a disconnect of the old attachment in the
usual way. This ensures the volume is still attached to the instance,
but is safely detached from the host we are offloading from. Should that
detach fail, the instance should be moved into an ERROR state.

Similarly, when it comes to unshelve, we update the existing attachments
with the connector, before continuing with the usual attach volume flow.

Swap Volume
-----------

For swap volume, we have one host, one instance, one device path, but
multiple volumes.

In this section, we talk about what happens should the volume being swapped
have the attachment_id present in the BDM, and as such we follow the new flow.

Firstly, there is the flow when cinder calls our API, secondly when a
user calls our API. Both flows are covered here:

* The Nova swap volume API is called to swap uuid-old with uuid-new

    * The new volume may have been created by the user in cinder, and the
      user may have made the Nova API call.
    * Alternatively, the user may have called Cinder's migrate volume API.
      That means cinder has created the new volume, and calls the Nova API on
      the user's behalf.

* (api) create new attachment for the volume uuid-new, fail API call if we
  can't create that attachment
* (compute) update cinder attachment with connector for uuid-new
* (compute) os-brick connect the new volume. If there is an error we
  deal with this like a failure during attach, and delete the
  attachment to the new volume
* (compute) Nova copies content of volume uuid-old to volume uuid-new,
  in libvirt this is via a rebase operation
* (compute) once the copy is complete, we detach uuid-old from instance
* (compute) update BDM so the attachment_id now points to the attachment
  associated with uuid-new
* (compute) once the old volume is detached, we do an os-brick disconnect
* (compute) if that worked, we call cinder's migrate_volume_completion
  with (uuid-new, uuid-old). If disconnect failed, we put the instance into
  the ERROR state.
* (compute) Update the BDM with a new volume-uuid, based on what
  migrate_volume_completion has returned. Note if cinder called swap, it
  will have deleted the old volume, but renamed the new volume to have the
  same uuid as the old volume had. If someone called Nova, we get back
  uuid-new, and we update the BDM to reflect the change.
* so on success we have created a new attachment to the new volume
  and deleted the attachment to the old volume.

Note: it is assumed if a volume is multi-attach, the swap operation will fail
and not be allowed. That will be true in either the Cinder or Nova started
case. In time we will likely move to Cinder's migrate_volume_completion API
using attachment_ids instead of volume ids. This spec does not look at what is
needed to support multi-attach, but this problem seemed worth noting here.

Alternatives
------------

We could struggle on fixing bugs in a "whack a mole" way.

There are several ways we should structure the API interactions. One of the
key alternatives is to add lots of state machine complexity into the API so
the shared connection related locking is handled by Cinder in the API layer.
While it makes the clients more complex, it seemed simpler for Nova and other
clients to do the locking discussed above.

Nova could look up the attachment uuid rather than store it in the BDM, there
is a period where the host uuid is not set, so it seems safer to store the
attachment uuid to stop any possible confusion around which attachment is
associated to each BDM.

During live-migration we could store the additional attachment_ids in the
migrate data, rather than as part of the BDM.

We could continue to save the connection_info in the BDM to be used when we
detach the volume. While seems like it might help avoid issues with changes
in the connection info that Nova hasn't been notified of, this is really a
premature optimization. We should instead work with Cinder and os-brick to
properly fix any such interaction problems in a way that helps all systems
that work with Cinder.

Data model impact
-----------------

When using the new API flow, we no longer need to store the connection_info,
as we don't need to pass that back to Cinder. Instead we just store the
attachment_id for each host the volume is attached to, and any time we need
the connection_info we fetch that from Cinder.

When an attachment_id is populated, we use the new flow to do all attach or
detach operations. When not present, we use the old flow.

REST API impact
---------------

No changes to Nova's REST API.

Security impact
---------------

Nova no longer needs to store the volume connection information, however it is
now available at any time from the Cinder API.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There should be no impact to performance. The focus here is stability across
all drivers. There may slightly more API calls between Nova and Cinder, but it
is not expected to be significantly impact performance.

Other deployer impact
---------------------

To use this more stable API interaction, and the new features that will depend
on this effort, must upgrade Cinder to a version that supports the new API.

It is expected we will drop support for older versions of Cinder within
two release cycles of this work being completed.

Developer impact
----------------

Nova and Cinder interactions should be better understood.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann

Other contributors:
  Lee Yarwood
  John Griffith

Work Items
----------

To make progress this cycle we need to split this work into small patches.
The overall strategy is that we implement new style attach last, and all
the other operations depend on the attachment_id being in the BDM, that will
not be true until the attach code is merged.

* use Cinder v3 API
* detect if the microversion that includes the new BDM support is present
* detach a new style BDM/volume attach
* reboot / rebuild (get connection info from cinder using attachment_id)
* live-migration
* migration
* evacuate
* shelve and unshelve
* swap volume
* attach (this means we now expose all the previous features)

Note there are more steps before we can support multi-attach, but these are
left for future specs:

* migrate old BDMs to the new BDM flow
* add explicit support for shared backend connections

Dependencies
============

Depends on the Cinder work to add the new API.
This was completed in Ocata.

Testing
=======

We need to functionally test both old and new Cinder interactions. This will
likely require a grenade job that leaves a volume connected to an instance
before the upgrade, so it can be disconnected after the upgrade.

Documentation Impact
====================

We need to add good developer documentation around the updated
Nova and Cinder interactions.

References
==========

* Cinder API spec:
  http://specs.openstack.org/openstack/cinder-specs/specs/ocata/add-new-attach-apis.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced

