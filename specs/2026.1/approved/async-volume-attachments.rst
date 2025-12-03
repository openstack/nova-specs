..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Asynchronous Volume Attachments
===============================

https://blueprints.launchpad.net/nova/+spec/async-volume-attachments

Nova currently provides an attach-volume API call that blocks on multiple RPC
calls to the compute service. The reasons for these blocking calls is mostly
historical, relating to hypervisors we used to support that involve more direct
interaction with the guest and thus can predict/reserve/identify the block
device name that will be used.

Problem description
===================

In eventlet (or any greenthreading scheme), blocking requests are not as
expensive because the request handler is able to service other connections
while waiting. However, in an environment like WSGI where each request is
handled in a real thread or process, blocking requests are much more expensive.

The attach volume API is one of those blocking APIs that currently involves
the API waiting for the reserve-block-device RPC call to complete. This
round-trip to the compute service can be slow if the compute service is busy in
general or if there's a running action on the to-be-attaching instance, as
reserving the block device name takes an instance-wide lock.

This is unfortunately somewhat pointless for the two main hypervisor drivers we
currently support (libvirt and vmware) as they are unable to predict or report
the block device that will be used in the guest anyway. As such, we are waiting
in the API, consuming a thread and connection, for information that isn't
useful anyway.

In WSGI mode (which we are trying to get users to move to in order to deprecate
and remove eventlet mode), this has been reported to be quite problematic as
slow (or multiple parallel) volume attach requests can consume all the
available request workers, thus causing a DoS type situation. Further, a
malicious user could presumably leverage this behavior to deny or degrade
service intentionally.

Use Cases
---------

As an operator, I want to be able to deploy nova-api in WSGI mode without
slow volume operations causing resource consumption issues.

As an operator, I want issues with the backend storage to not cause the
nova-api service to exhaust request resources.

Proposed change
===============

This spec proposes to introduce a new microversion in which the attach-volume
call will be asynchronous and return 202 instead of 200. We will delegate the
current attach-volume workflow to the conductor task api and cast or call based
on the microversion used. In the async case, the user can retrieve the expected
block device name the synchronous API call would have returned by retrieving it
from the instance's volume-attachments.
Like before, the user needs to poll for completion of the attachment by waiting
for the volume's state in Cinder to change to `in-use`.

The `_attach_volume()` method in the current `compute/api.py` will be moved to
the conductor task API, reachable over RPC. The API will make this delegating
call to conductor for the older microversion and cast for the new one,
returning the appropriate content and response code in each case.

.. note:: There is also an attach workflow for shelved_offloaded state which
  must be considered. It talks to cinder, so it may be a candidate for moving
  along with the main workflow, but it happens all in the API today, so it
  may also make sense to just leave it.

Alternatives
------------

There was an alternative approach (see `previous spec`_) proposed in the past
which redesigns more of the attach workflow and uses traits advertised in
placement to control which behavior is used. This seems overly complicated to
me, while also requiring a new microversion and RPC behavior.

Data model impact
-----------------

None.

REST API impact
---------------

This will introduce a new microversion, making the attach-volume API
asynchronous.

Security impact
---------------

The current behavior offers somewhat of a DoS opportunity, especially when the
API is running in WSGI mode. This will eliminate that possibility.

Notifications impact
--------------------

None, other than the notification is currently emitted before the API call
returns, and it will happen afterwards as part of this change. Since the user
making the attach call is normally not a consumer of notifications, this is not
likely to be noticed or cause any problems.

Other end user impact
---------------------

End users who currently rely on the attach-volume API to return the expected
device name in the guest will have to retrieve that information separately from
the os-volume_attachments API. This might require polling or waiting for the
volume-attachment to complete, because the information will not be immediately
available after the attach-volume API call finishes.

Performance Impact
------------------

This work is being done to address a performance impact of exhausting resources
when in WSGI mode. This work will address that, but also generally improve
performance as async operations require fewer resources for the duration.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

One benefit of this approach is that the compute service and RPC API need not
change.  Thus, the conductor being upgraded alongside the API which uses the
new task API (already required in lockstep) means that older computes will not
perceive any change if the new API is used before the upgrade is complete.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jkulik

Other contributors:
  danms

Feature Liaison
---------------

This work is related to the eventlet deprecation effort, and thus should be
considered a parallel effort to address issues that are being created by
changing the only available deployment model we allow.

Work Items
----------

- Move the `_attach_volume()` method to the task API where it can be called
- Add a new cast/call RPC interface for the conductor task API to perform the
  attach workflow
- Add a new microversion to the API which controls whether the attach workflow
  is asynchronous or not
- Add tempest coverage for the new microversion

Dependencies
============

No direct dependencies for this work, although it may have some impact or
relation to the eventlet deprecation effort.

Testing
=======

Typical functional and unit tests should be sufficient for this work. Existing
tempest tests for volume attachment should be trivially updatable to call the
new microversion, validate the return code, and poll for completion.

Documentation Impact
====================

The typical api-ref documentation should be sufficient for this work, as well
as a release note as this is likely of interest to operators currently
suffering from resource exhaustion.

References
==========

.. _`previous spec`: https://review.opendev.org/c/openstack/nova-specs/+/765097/2/specs/wallaby/approved/api-remove-device_name-from-attach_volume-response.rst
.. _`existing bug`: https://bugs.launchpad.net/nova/+bug/1930406

History
=======

Optional section intended to be used each time the spec is updated to describe
new design, API or any database schema updated. Useful to let reader understand
what's happened along the time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.1 G
     - Introduced
