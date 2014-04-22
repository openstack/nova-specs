..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================================================
Allow controlled shutdown of GuestOS for operations which power off the VM
==========================================================================

https://blueprints.launchpad.net/nova/+spec/user-defined-shutdown

The current behavior of powering off a VM without giving the Guest Operating
system a chance to perform a controlled shutdown can lead to data corruption.


Problem description
===================

Currently in libvirt operations which power off the VM (stop, rescue, shelve,
resize) do so without giving the GuestOS a chance to shutdown gracefully.
Some GuestOS's (for example Windows) do not react well to this type of virtual
power failure, and so it would be better if these operations follow the
same approach as soft_reboot and give the GuestOS a chance to shutdown
gracefully.


Proposed change
===============

The proposed changes will make the default behavior for stop, rescue, resize,
and shelve to give the GuestOS a chance to perform a controlled shutdown
before the VM is powered off.

The change will encapsulate the complexity of signaling to and waiting for
the GuestOS in the hypervisor, and allow image owners the ability to tune
the associated timing via image metadata to take account of GuestOSs that
require an extended period to shutdown (such as Windows).

Users will be able to specify the shutdown behavior on a per operation basis
via a new shutdown_type parameter where, in keeping with the current reboot
operation, a "soft" shutdown will give the GuestOS a chance to perform a
clean shutdown, and a "hard" shutdown will cause an immediate power off.  The
default behavior will be a "soft" shutdown.

An example of a user wanting to override the default behavior is Tempest
which does not generally care if a GuestOS becomes corrupted and may
prefer speed of execution over data integrity.

At the hypervisor layer the shutdown behavior will be controlled by two
values:

* A timeout value specifying in seconds how long the hypervisor should
  wait for the GuestOS to shutdown. If the GuestOS does not shutdown
  within this period then the VM will be powered off anyway. A value of 0
  will power off the VM without signaling the Guest to shutdown.

* A retry interval specifying in seconds how frequently within that period the
  hypervisor should signal the guest to shutdown.  This is a protection
  against guests that may not be ready to process the shutdown signal
  when it is first issued - a common problem if an instance is deleted
  just after it has been created and the GuestOS is booting.

For example if the overall timeout is set to 60 seconds and the retry interval
is set to 10 seconds then the guest will be signaled up to six times before
being powered off.

These values will be passed into the virt driver by the compute manager,
allowing the same values to be used for all hypervisors.

The timeout value will be a Nova configuration parameter as different
operators may want a different default.  The retry value will be implemented
as a constent in the Nova code.  The timeout value can be overridden
on a per image basis via image metadata settings.

Alternatives
------------

An alternative approach would be to expose a new operation that only shuts
down the GuestOS (with used defined timing parameters), expose the status of
that operation via the API, and rely on the client for all retry logic.
However we believe that a clean shutdown should be the default behavior in
Nova and not have to be managed as a separate activity (which would have to
be replicated in all API bindings).

An alternative using a simpler single parameter to specify how long the
hypervisor should wait was previously merged but had to be reverted
because it added around 25 minutes to the tempest runs:
https://review.openstack.org/#/c/35303/

This was due to Tempest frequently stopping an instance immediately after
it is created, in which case the ACPI signal is delivered before the GuestOS
is in a state to process it.  This results in the shutdown waiting for the
full duration of the timeout.

The revised approach described above avoids this issue by periodically
resending the shutdown signal to the GuestOS.

Once this change has been merged Tempest could be optimized to avoid this delay
(for example by setting the timeout to zero via image metadata or nova.conf).

It could be argued that the delete operation should allow the same
controlled shutdown schematics so that instances using and/or booting
from volumes can also leave those file systems in a safe state.  However
if the stop operation is modified to provide a controlled shutdown then
users can achieve the required sequence by performing a stop prior to
the delete.  This also avoids an issue of the http delete request not
normally accepting a body.


Data model impact
-----------------

None, the change is contained mainly within the interaction between the compute
manager and the virt driver.

REST API impact
---------------

The following API methods will be extended to accept an optional shutdown_type
parameter:

* Stop       POST servers/{server_id}/action
                        {"os-stop": {"shutdown_type": "HARD|SOFT"}}

* Rescue     POST servers/{server_id}/action
                        {"rescue": {"shutdown_type": "HARD|SOFT"}}

* Resize     POST servers/{server_id}/action
                        {"resize": {"shutdown_type": "HARD|SOFT",
                                    "flavor_id": <id>}}

* Shelve     POST servers/{server_id}/action
                        {"shelve": {"shutdown_type: "HARD|SOFT"}}

* Migrate    POST servers/{server_id}/action
                        {"migrate": {"shutdown_type: "HARD|SOFT"}}


Security impact
---------------

None, the change doesn't change the set of operations that a user can perform.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users will be able to provide additional options to the stop, rescue, and
delete.  These will be exposed in the python-novaclient:

nova stop [--hard-shutdown]
nova rescue [--hard-shutdown]
nova resize [--hard-shutdown]
nova shelve [--hard-shutdown]

Note that "--hard-shutdown" is preferred here over the "--hard" option used
for reboot since a "soft resize" might be interpreted to mean a soft change
in allocated resources (such as disabling a cpu).

To make the novaclient CLI reboot command consistent it will be also modified
to accept --hard-shutdown as an alias for --hard.

Performance Impact
------------------

The performance impact is limited to the changes in the processing path of the
stop, rescue, and delete operations. When performing a clean shutdown
these will take longer than before as the system waits for the GuestOS to
shutdown. The overhead of polling to observe this change in state is
negligible and the calling thread will sleep (yield) between each poll.

Other deployer impact
---------------------

Once this set of changes has been merged the system will by default be
configured to wait for instances to shutdown gracefully for stop, shelve,
rescue, and resize operations.

Deployers will need to consider if they want to modify the default timeout
parameters, and/or to add override values to the metadata of existing images.

The configuration parameters will be common to all hypervisors, but this
BP will only deliver a libvirt implementation.


Developer impact
----------------

Only the first stage of the implementation is hypervisor dependent, once
that has merged other hypervisor implementations can be added.

The remaining stages will apply to any hypervisor that implements the revised
power_off options.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  philip-day

Work Items
----------

* Add timeout parameters to virt power_off method of virt driver and provide
  the libvirt implementation.   Implement clean_shutdown for stop() within
  the compute manager as an initial example.
* Add clean_shutdown option to compute manager Rescue, Resize, and Shelve
  operations
* Use image properties to override the timeout values
* Expose clean shutdown via rpcapi
* Expose clean shutdown via API


Dependencies
============

None


Testing
=======

The methods that are being modified are already extensively tested by Tempest
which will ensure no functional regression.

The default behavior will be to perform a clean shutdown, although it's not
easy to see how this can be verified by Tempest, since it needs specific
support within the Guest, and the behavior of any GuestOS is generally
considered outside the scope of Nova.  Likewise the ability to stop without a
clean shutdown could be exercised from Tempest (it's possible that Tempest
would want to make this its normal case), but its hard to see how that could
be verified.  Input will be sought from the Tempest community to see what can
be done to address these issues.


Documentation Impact
====================

* The API specs will need to be updated.
* The change in default behavior for stop, rescue, resize, and shelve (to wait
  for the GuestOS to shutdown) will need to be documented.
* The ability to override the shutdown timeouts on a per image basis will need
  to be documented.

References
==========

The code for the first work item is available for review
https://review.openstack.org/#q,I432b0b0c09db82797f28deb5617f02ee45a4278c,n,z

