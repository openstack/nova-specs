..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Allowing target state for evacuate
==================================

https://blueprints.launchpad.net/nova/+spec/allowing-target-state-for-evacuate

In certain circumstances the operator may desire to evacuate running
instances to stopped state regardless of the current state of the
instance.

Problem description
===================

The current evacuate instance API does not allow operators to set a
desired target state to the evacuated instances. Restoring the
original state of the instance when it was active on the source host
may result in issues if the guest required a valid token to be started
or prevent evacuation when using encrypted volumes.

Use Cases
---------

- As an operator, I would like to be able to evacuate instances to a
  shut-off state because my tenant workloads may have specific
  security requirements, that do not allow them to be started by the
  administrator.
- As an operator, I would like to be able to evacuate VMs with
  encrypted volumes without making the barbican secret readable by
  admins and reducing the security.
- As a user, if my instance is offline due to a host outage, I don't
  necessarily want an admin evacuating it and bringing it back online
  without my knowledge as I may have already replaced it and the
  zombie coming back may cause a conflict.

Proposed change
===============

As of the bumped version, the API will force the stopped state for
evacuated instances. It is expected that before the bumped version the
behavior stay the same, instances with state active or stopped will
keep their state at destination.

1) With the new microversion nova will *always* evacuate the instance
   to SHUTOFF state.
2) The only way to keep the instance state after the evacuation is to
   use an older microversion.

Alternatives
------------

- It may be possible to enhance the API resetState to accept RUNNING and
  SHUTOFF.
- It may be possible to allow `stop`'s action working with compute
  node down, But that would have created incoherence between the
  database and the real state of the instance.

Data model impact
-----------------

None.

REST API impact
---------------

A microversion bump is expected. But no changes in the schema will appear.

``POST /servers/{server_id}/action``

  .. code-block::

    {
        "evacuate": {
             "host": "b419863b7d814906a68fb31703c0dbd6",
        }
    }


Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

- The nova api-ref will be updated to reflect the changes.
- Related to openstack client, nothing is expected to change instead
  of a noop bump.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

It has been agreed that this spec would not resolve the design issue
whereby the `evacuate server` action starts the virtual machines and
then stops it when the target state is stopped. An issue has been
reported at:

  https://bugs.launchpad.net/nova/+bug/1994967


Upgrade impact
--------------

- Upgrade note will be added describing new behavior.
- An RPC change is expected to make the compute manager handle the new
  target state, resulting in the version being incremented.
- At API level, a min version check will ensure that all services are
  new enough to accept the request, if not the request will be
  rejected with a NotSupported exception.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid-ferdjaoui

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

- API changes with microversion
- Testing for the changes.

Dependencies
============

None.

Testing
=======

- Unit and functional testing for API change.

Documentation Impact
====================

The api-ref will be updated to reflect the changes.

References
==========

* https://docs.openstack.org/api-ref/compute/?expanded=evacuate-server-evacuate-action-detail

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 - Antelope
     - First introduction
