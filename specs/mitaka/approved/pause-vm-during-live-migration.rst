..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Provide a way to pause VM during live migration
===============================================

Blueprint:
https://blueprints.launchpad.net/nova/+spec/pause-vm-during-live-migration

When using live migrations, an operator might want to have a possibility to
increase success chance of migration even at the cost of longer VM downtime.
This spec proposes a new nova API for pausing VM during live migration.

Problem description
===================

The most common use case of live migration is host maintenance for different
purposes. It might be, e.g., OpenStack upgrade to newer version or even
hardware upgrade. Hypervisors have some features such as CPU throttling or
memory compression to make it possible to live migrate every VM to other hosts.
However, a VM might run workload that will prevent live migration from
finishing. In such case operator might want to pause VM during live migration
to stop memory writes on a VM.

Another use case is imminent host failure where live migration duration might
be crucial to keep VMs running regardless of VMs downtime during transition to
destination host.

Currently to pause VM during live migration operator needs to pause VM through
libvirt/hypervisor. This pause is transparent for Nova as this is the same that
happens during 'pause-and-copy' step during live migration.

Use Cases
----------

As an operator of an OpenStack cloud, I would like the ability to pause VM
during live migration. This operation prevents VM from dirtying memory and
therefore it forces live migration to complete.

Proposed change
===============

A new API method for pausing VM during live migration. This will make
asynchronous RPC call to compute node to pause a VM through libvirt.
Also this will introduce new instance action 'live-migration-paused-vm'.
The Migration object and MigrationList object will be used to establish which
migrations exist, with additional optional data provided by the compute driver.

This will need an increment to the rpcapi version too.

Alternatives
------------

Alternative is not doing this and let operator pause VM manually through
hypervisor.

Another alternative is to reuse existing pause operation in nova. However, it
might bring some confusion to operators. Libvirt preserves VM state that was
in effect when live migration started. When live migration completes
libvirt reverts VM state to preserved one. Example workflow:

* VM is active
* Operator starts live migration
* Libvirt preserves active state of a VM
* Operator pauses VM during transition (e.g., nova pause VM)
* LM finishes
* Libvirt reverts VM state to preserved one - in this case to active.

Because of such behavior it is not recommended to reuse existing pause
operation. It might be confusing for operators that single operation is used
for two different purposes.

Also in the future there might be multiple methods to force end of live
migration. This API can be extended to give hints to do things other than
pause the VM during live migration.

This also will be suitable for Tasks API.

Data model impact
-----------------

None. The Migration objects used are already created and tracked by nova.


REST API impact
---------------

To be added in a new microversion.

* Pause VM during live migration

  `POST /servers/{server_id}/{action}`

Body::

  {
    "live-migrate-force-end": null
  }

  Normal http response code: `202 Accepted`
  No response body is needed

  Expected error http response code: `403 Forbidden`
  - the migration exists but the user is not authorized to pause VM during
  live migration. For instance, non admin user has management authority over
  the instance, but has not been granted the authority to pause their
  instances during live migrations.

  Expected error http response code: `404 Not Found`
  - the instance does not exist

  Expected error http response code: `409 Conflict`
  - the instance state is invalid for pausing vm, e.g., instance is
  not currently being live migrated.

Because this is async call there might be an error that will not be exposed
through API. For instance, hypervisor does not support pausing VM during live
migration. Such error will be logged by compute service.

Security impact
---------------

None

Notifications impact
--------------------

There will be new notification to indicate start and outcome of pausing VM
during ongoing live migration.

Other end user impact
---------------------

python-novaclient will be extended by new operation to pause a VM during live
migration.

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
Pawel Koniszewski (irc: pkoniszewski)

Work Items
----------

* Pausing VM during live migration through libvirt
* python-novaclient 'nova live-migration-force-end'

Dependencies
============

None

Testing
=======

* Unit and Functional tests in Nova
* Tempest tests if possible to slow down live migration or start never-ending
  live migration

Documentation Impact
====================

New API needs to be documented:

* Compute API extensions documentation
  http://developer.openstack.org/api-ref-compute-v2.1.html

* nova.compute.api documentation
  http://docs.openstack.org/developer/nova/api/nova.compute.api.html

References
==========

None
