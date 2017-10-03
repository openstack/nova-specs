..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Return Alternate Hosts
======================

https://blueprints.launchpad.net/nova/+spec/return-alternate-hosts

Sometimes when a request to build a VM is attempted, the build can fail for a
variety of different reasons. At recent PTGs and Forums we discussed a request
from operators to have the scheduler return some alternate hosts along with the
selected host. This was desired because in the event of a failed build, another
host could be tried without having to go through the entire scheduling process
again.


Problem description
===================

When a request to build a VM is received, a suitable host must be found. This
selection process can take a non-trivial amount of time. Occasionally the build
of an instance on a host fails, for any of a number of reasons. When that
happens, the process has to start all over again, and because this happens in
the cell, and cells cannot call back up to the api layer where the scheduler
lives, we run into a problem. Operators stated that they wanted to preserve the
ability to retry a failed build, but the design of the current retry system
doesn't work in a cells V2 world, as it would require an up call from the cell
conductor to the superconductor to request a retry.

Similarly, resize operations currently also need to call up to the
superconductor in order to retry a failed resize.


Use Cases
---------

As an operator of an OpenStack deployment, I want to ensure that both VM and
Ironic builds and resizes are successful as often as possible, and take as
little time as possible.


Proposed change
===============

We propose to have the scheduler's select_destinations() return N hosts per
requested instance, where N is the value in CONF.scheduler.max_attempts.

When all the hosts for a request are successfully claimed, the scheduler will
scan the remaining sorted list of hosts to find additional hosts in the same
cell as each of the selected hosts, until the total number of hosts for each
requested instance equals the configured amount, or the list of hosts is
exhausted. This means that even if an operator configures their deployment for,
say, 5 max_attempts, fewer than that may be returned if there are not a
sufficient number of qualified hosts.

The RPC interfaces between conductor, scheduler, and the cell computes will
have to be changed to reflect this modification.

After calling the scheduler's select_destinations(), the superconductor will
have a list of one or more Selection objects for each requested instance. It
will process each instance in turn, as it does today. The difference is that
for each instance, it will pop the first Selection object from the list, and
use that to determine the host to which it will cast the call to
build_and_run_instance(). This RPC cast will have to be changed to add the list
of remaining Selection objects as an additional parameter.

The compute will not use the list of Selection objects in any way; all the
information it needs to build the instance is contained in the current
paramters. If the build succeeds, the process ends. If, however, the build
fails, compute will call its delete_allocation_for_instance() as it currently
does, and then call the ComputeTaskAPI's build_instances() to perform the
retry. This call will be modified to pass the Selection object list back to
the conductor. The conductor will then inspect the list of Selection objects:
if it is empty, then all possible retries have been exhausted, and the process
stops. Otherwise, the conductor pops the first Selection object, and the
process repeats until either the build is successful, or all hosts have failed.

The only difference during the retries is that the conductor will first have to
verify that the host a Selection object represents still has sufficient
resources for the instance by calling Placement to attempt to claim them, using
the value in the Selection object's `allocation` field. If that field is empty,
that represents the initial selected host, whose resources have already been
claimed. If there is a value there, that means that we are in a retry, so the
conductor will first attempt to claim the resources using that value. If that
fails, that Selection object is discarded, and the next is popped from the
list.

The logic flow for resize operations can be similarly modified to allow for
retries within the cell, too. Live migrations, in contrast, have a retry
process that is handled in the superconductor, so it will only need to be
modified to work with the new values returned from select_destinations().

Note that in the event of a burst of requests for similarly-sized instances,
the list of alternates returned for each request will likely have some overlap.
If retries become necessary, the earlier retry may allocate resources that
would make that host unsuitable for a slightly later retry. This claiming code
will ensure that we don't attempt to build on a host that doesn't have
sufficient resources, but that also means that we might run out of alternates
for the later requests. Operators will need to increase
CONF.scheduler.max_attempts if they find that exhausting the pool of alternates
is happening often in their deployment.

As this proposal will change the structure of what is returned from the call to
select_destinations(), any method, such as evacuate, unshelve, or a migration,
will have to be modified to accept the new data structure. They will not be
required to change how they work with this information. In other words, while
the build and resize processes in a cell will be changed as noted above to
retry failed builds using these alternates, these other consumers of
select_destinations() will not change how they use the result, because they do
not handle retries from within the cell conductor. We may decide to change them
at a later date, but that is not in the scope of this spec.

Alternatives
------------

Continue returning a single host per instance. This is simpler from the
scheduler/conductor side of things, but will make failed builds more common
than with this change, since retries won't be possible. Since we are now
pre-claiming in the scheduler, resource races, which was a major contributor to
failed builds, should no longer happen, making the number of failed builds much
lower even without this change.

Instead of passing these Selection objects around, store this information,
keyed by instance_uuid, in a distributed datastore like etcd, and have the
conductor access that information as needed. The calls involved in building
instances already contain nearly a dozen parameters, and it feels like more
tech debt to continue to add more.

Allow the cell conductor to call back up to the superconductor when a build
fails to initiate a retry. We have already decided that such callups will not
be allowed, making this option not possible without abandoning that design
tenet.

Data model impact
-----------------

None, because none of this alternate host information will be persisted.

REST API impact
---------------

None

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

This will slightly increase the amount of data sent between the scheduler,
superconductor, cell conductor, and compute, but not to any degree that should
be impactful. It will have a positive performance impact when an instance build
fails, as the cell conductor can retry on a different host right away.

Other deployer impact
---------------------

None

Developer impact
----------------

This change will not make the workflow for the whole scheduling/building
process any more complex, but it will make the data being sent among the
services a little more complex.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ed-leafe

Other contributors:
  None

Work Items
----------

* Modify the scheduler's select_destinations() method to find additional hosts
  in the same cell as the selected host, and return these as a list of
  Selection objects to the superconductor.

* Modify the superconductor to pass this new data to the selected compute host.

* Modify all the calls that comprise the retry pathway in compute and conductor
  to properly handle the list of Selection objects.

* Modify all other methods that call select_destinations() to properly handle
  the lsit of Selection objects.


Dependencies
============

This depends on the work to implement Selection objects being completed. The
spec for Selection objects is at https://review.openstack.org/#/c/498830/.


Testing
=======

Each of the modified RPC interfaces will have to be tested to verify that the
new data structures are being correctly passed. Tests will have to be added to
ensure that the retry loop in the cell conductor properly handles build
failures.


Documentation Impact
====================

The documentation for CONF.scheduler.max_attempts will need to be updated to
let operators know that if they are seeing cases where a burst of requests have
led to builds failing because none of the alternates has enough resources left,
they should increase that value to provide a larger pool of alternates to
retry.

Any of the documentation of the scheduler workflow will need to be updated to
reflect these changes.

References
==========

None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
