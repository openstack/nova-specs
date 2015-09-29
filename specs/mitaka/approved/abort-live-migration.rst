..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Provide a way to abort an ongoing live migration
================================================

Blueprint:
https://blueprints.launchpad.net/nova/+spec/abort-live-migration

At present, intervention at the hypervisor level is required to cancel
a live migration. This spec proposes adding a new operation on the
instance object to cancel a live migration of that instance.

Problem description
===================

It may be that an operator decides, after starting a live migration,
that they would like to cancel it. Effectively this would mean
rolling-back any partial migration that has happened and leaving the
instance on the source node. It may be that the migration is taking too
long, or some operational problem is discovered with the target node.
As the set of operations that can be performed on an instance during
live migration is restricted (only delete is currently allowed), it may
be that an instance owner has requested that their instance be
made available urgently.

Currently aborting a live migration requires intervention at the
hypervisor level, which Nova recognises and resets the instance state.

Use Cases
----------

As an operator of an OpenStack cloud, I would like the ability to
query, stop and roll back an ongoing live migration.  This is required
for a number of reasons.

1. The migration may be failing to complete due to the instance's
   workload. In some cases the solution to this issue may be to pause
   the instance but in other cases the migration may need to be
   abandoned or at least postponed.
2. The migration may be having an adverse impact on the instance,
   i.e. the instance owner may be observing degraded performance of
   their application and be requesting that the cloud operator address
   this issue.
3. The instance migration may be taking too long due to the large
   amount of data to be copied (i.e. the instance's ephemeral disk is
   very full) and the cloud operator may have consulted with the
   instance owner and decided to abandon the live migration and employ
   a different strategy. For example, stop the instance, perform the
   hypervisor maintenance, then restart the instance.

Proposed change
===============

New API operations on the instance object are proposed which can be used
to obtain details of migration operations on the instance and abort
an active operation.  This will include a GET to obtain details of
migration operations.  If the instance does not exist (or is not
visible to the tenant id being used) or has not been the subject of any
migrations the GET will return a 404 response code.  If the GET
returns details of an active migration, a DELETE can be used to abort
the migration operation.  Again, if the instance does not exist (as in
the case where it has been deleted since the GET call) or no migration
is in progress (i.e. it is ended since the GET call) the DELETE will
return a 404 response code.  Otherwise it will return a 202 response
code.

Rolling back a live migration should be very quick, as the source host
is still active until the migration finishes.  However this depends on
the approach implemented by the virtualization driver. For example Qemu
is planning to implement a 'post copy' feature -
https://www.redhat.com/archives/libvir-list/2014-December/msg00093.html
In this situation a cancellation request should be declined because
rolling back to the source node would be more work than completing the
migration. In fact it is probably impossible!  Nova would need to be
involved in the switch from pre-copy to post-copy so that it could
switch the networking to the target host. Thus nova would know that the
instance has switched and decline any cancellation requests.  If the
instance migration were to encounter difficulties completing during the
post copy the instance would need to be paused to allow the migration
to complete.

The GET /servers/{id}/migrations operation will entail the API server
verifying the existence and task state of the instance.  If the
instance does not exist (or is not visible to the user invoking this
operation) a 404 response code will be returned. Otherwise the API
server will return details of all the running migration operations for
the instance. It will use an new method on the migration class called
get_by_instance_and_status specifying the instance uuid and status of
running. If no migration objects are returned an empty list will be
returned in the API response. If one or more migration object is
returned then the new_instance_type_id and old_instance_type_id fields
will be used to retrieve flavor objects for the relevant flavors to
obtain the falvor id.  These values will be included in the response
as new_flavor_id and old_flavor_id. This will mean that a user will be
able to use this information to obtain details of the flavors.

The DELETE /servers/{id}/migrations/{id} operation will entail the API
server calling the migration_get method on the migration class to
verify the existence of an ongoing live migration operation on the
instance. It will then call a method on the ServersController class
called live_migrate_abort

If the invoking user does not have authority to perform the operation
(as defined in the policy.json file) then a 403 response code will be
returned. The policy.json file will be updated to define the
live_migrate_abort as accessible to cloud admin users only.

If the API server determines that the operation can proceed it will
send an async message to the compute manager and return a 202
response code to the user.

The compute manager will emit a notification message indicating that
the live_migrate_abort operation has started.  It will then invoke a
method on the driver to abort the migration.  If the driver is unable
to perform this operation a new exception called
'AbortMigrationNotSupported' will be returned.

The compute manager method invoked will be wrapped with the decorators
that cause it to generate instance action and notification events. The
exception generated here would be processed by those wrappers and thus
the user would be able to query the instance actions to discover the
outcome of the cancellation operation.

Note the instance task state will not be updated by the
live_migrate_abort operation.  If the operator were to execute the
operation multiple times the subsequent invocations would simply fail.

In the case of the libvirt driver it will obtain the domain object for
the target instance and invoke job abort on it.  If there is no job
active an error will be returned.  This could occur if the instance
migration has recently finished or has completed the libvirt migration
and is executing the post migration phase.  It could also occur if the
migration is still executing the pre migration phase.  Finally, if it
could mean the libvirt job has failed but nova has not updated the
task state.  In all of these cases an exception will be returned to the
compute manager to indicate that the operation was unsuccessful.

If the libvirt job abort operation succeeds then the thread performing
the live migration will receive an error from the libvirt driver and
perform the live migration rollback steps, including reseting the
instance's task state to none.

Alternatives
------------

One alternative is not doing this, leaving it up to operators to roll
up their sleeves and get to work on the hypervisor.

The topic of cancelling an ongoing live migration has been mooted
before in Nova, and has been thought of as being suitable for a
"Tasks API" for managing long-running tasks [#]_. There is not
currently any Tasks API, but if one were to be added to Nova, it would
be suitable.

Data model impact
-----------------

None

REST API impact
---------------

To be added in a new microversion.

* Obtain details of live migration operations on an instance that have
  a status of running.  There should only be one migration per instance
  in this state but the API call supports returning more than one.

  The operation will return the id of the active migration operation
  for the instance.

  `GET /servers/{id}/migrations`

Body::

  None

  Normal http response code: `200 OK`

  Body::

  {
   "migrations": [
      {
        "created_at": "2013-10-29T13:42:02.000000",
        "dest_compute": "compute3",
        "id": 6789,
        "instance_uuid": "instance_id_123",
        "new_flavor_id": 2,
        "old_flavor_id": 1,
        "source_compute": "compute2",
        "status": "running",
        "updated_at": "2013-10-29T14:42:02.000000",
      }
    ]
  }

  Expected error http response code: `404 Not Found`
  - the instance does not exist

  Expected error http response code: `403 Forbidden`
  - Policy violation if the caller is not granted access to
  'os_compute_api:servers:migrations:index' in policy.json

* Stop an in-progress live migration

  The operation will return the instance task state to none.

  `DELETE /servers/{id}/migrations/{id}`

Body::

  None

  Normal http response code: `202 Accepted`
  No response body is needed

  Expected error http response code: `404 Not Found`
  - the instance does not exist

  Expected error http response code: `403 Forbidden`
  - Policy violation if the caller is not granted access to
  'os_compute_api:servers:migrations:delete' in policy.json

  Expected error http response code: `400 Bad Request`
  - the instance state is invalid for cancellation, i.e. the task
  state is not 'migrating' or the migration is not in a running
  state and the type is 'live-migration'

Security impact
---------------

None

Notifications impact
--------------------

Emit notification messages indicating the start and outcome of the
migration cancellation operation.

Other end user impact
---------------------

A new python-novaclient command will be available, e.g.

nova live-migration-abort <instance>

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
Paul Carlton (irc: paul-carlton2)

Other assignees:
Claudiu Belu

Work Items
----------

* python-novaclient 'nova live-migration-abort'
* Cancel live migration API operation
* Cancelling a live migration per hypervisor
  * libvirt
  * hyper-v
  * vmware

Dependencies
============

None

Testing
=======

Unit tests will be added using fake virt driver to simulate a live
migration.  The fake driver implementation will simply wait for the
cancelation.  We also want to test attempts to cancel a migration
during pre or post migration, which can be done using a fake
implementation of those steps that will also wait for an indication
that the cancel attempt has been performed.

The functional testing will utilize the new live migration CI job.
An instance with memory activity and a large disk will be used so we
can test all aspects of live migration, including aborting the live
migration.

Documentation Impact
====================

New API needs to be documented:

* Compute API extensions documentation
  http://developer.openstack.org/api-ref-compute-v2.1.html

* nova.compute.api documentation
  http://docs.openstack.org/developer/nova/api/nova.compute.api.html

References
==========

Some details of how this can be done with libvirt:
https://www.redhat.com/archives/libvirt-users/2014-January/msg00008.html

.. [#] http://lists.openstack.org/pipermail/openstack-dev/2015-February/055751.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
