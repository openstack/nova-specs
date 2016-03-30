..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Volume Operations When Shelved
==============================

https://blueprints.launchpad.net/nova/+spec/volume-ops-when-shelved

Currently attach, detach and swap volume operations are allowed when
an instance is paused, stopped and soft deleted, but are
not allowed when an instance has been shelved. These operations are
possible when an instance is shelved so we should enable them.

Problem description
===================

The attach, detach and swap volume operations are not allowed when an
instance is in the shelved or shelved_offloaded states. From a user's
perspective this is at odds with the fact these operations can be
performed on instances in other inactive states.

Use Cases
---------

As a cloud user I want to be able to detach volumes from my shelved instance
and use them elsewhere, without having to unshelve the instance first.

As a cloud user I want to be able to perform all the volume operations on
a shelved instance that I can when it is stopped, paused or soft deleted.

Proposed change
===============

Shelved instances can be in one of two possible states: shelved and
shelved_offloaded (ignoring transitions during shelving and unshelving).
When in shelved the instance is still on a host but inactive. When in
shelved_offloaded the instance has been removed from the host and the
resources it was using there are released.

Volume operations on an instance in the shelved state are similar to
any other state when on the host. The operations can be enabled by allowing
them at the compute API for this state. The existing compute manager code
does handle this case already; it is merely disabled in the API.

The shelved_offloaded state is different. In this case the instance is not
on any host, so functions to attach and detach need to be implemented in
the API in the same way that the code to detach volumes for deletion is done.
These will only perform the steps to manage the block device mappings and
register with cinder. Any actual attachment to a host will be completed
when the instance is unshelved as usual.

The compute api attach volume code makes an rpc call to the hosting compute
manager to select a name for the device, which includes a call into the virt
driver. This can not be done when the instance is offloaded
because it is not on a host.

In fact, devices names are set when an instance is booted
and there is no guarantee that a name provided by the user will be
respected. So the new attach method for the shelved_offloaded state will
defer name selection until the instance is unshelved. This avoids the need
to call a compute manager at all.

Alternatives
------------

The only clear alternative is to not allow volumes to be attached or detached
when an instance is shelved.

Data model impact
-----------------

None.

REST API impact
---------------

The attach, detach and swap operations will
be allowed when the instance is in the shelved and shelved_offloaded states.
Instead of returning the existing HTTP error 409 (Conflict)
the return values will be the same as they are for other valid states.

This change will require an API microversion increment.

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

None.

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

The following changes will be required:

#. Change the guards on the attach, detach and swap functions in the compute
   API to allow them when the instance is in the shelved state.
#. Add functions to attach, detach and swap volumes that are be executed
   locally at the API when the instance is in the shelved offloaded state.
#. Add code to handle device names on unshelve (devices attached in
   shelved_offloaded will have had name selection deferred to unshelve).
#. Change the guards on the attach, detach and swap functions to allow them
   when the instance is in the shelved_offloaded state.

Dependencies
============

This spec is a step towards allowing boot volumes to be attached and
detached when in the shelved_offloaded state (see [1]). But this spec
also provides useful functionality on its own.
This spec adds more opportunity to get race conditions due to
conflicting parallel operations, it is important to note that those races
are not introduced by this change but already exist in nova and they are
going to be addressed by a different change, please see [2] for more
information.

Testing
=======

Most of the attach and detach functionality can be tested with unit tests.
In particular the shelved state is the same as shutdown or stopped.

New unit tests will be needed for the new attach and detach functions in the
shelved offloaded state.

A tempest test will be added to check that the sequence of shelving,
detaching/attaching volumes and then unshelving leads to a running
instance with the expected volumes correctly attached.

Documentation Impact
====================

This spec will affect cloud users. They will now be able to perform volume
operations on shelved instances.

References
==========

[1] https://blueprints.launchpad.net/openstack/?searchtext=detach-boot-volume

[2] https://review.openstack.org/216578

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
