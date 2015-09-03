..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
Robustify Evacuate
==================

https://blueprints.launchpad.net/nova/+spec/robustify-evacuate

Evacuate provides the ability for a deployer to relocate and rebuild
instances when a compute host goes down for an extended period of
time. It does this by simply rebuilding the instance elsewhere. When
the initial compute host comes back up, some logic on startup looks at
instances that appear to have been relocated and deletes them from the
local machine. This is problematic in practice, as we have very little
information on which to base a decision to destroy data -- making it
effectively a guess.

This spec proposes to improve the robustness of this process by
explicitly recording the event of an instance evacuation such that the
recovering host has a very clear indication that it should delete the
local copy of an instance.


Problem description
===================

The evacuate cleanup logic in Nova guesses about whether to destroy
data. It shouldn't guess, as it's relatively easy to cause Nova to
guess poorly, which results in data loss.

As an example of this: right now if you have a libvirt-based system, an
accidental hostname change will destroy data. Imagine a deployer that
has a compute node with a failed CPU. The easy fix is to swap the
disks into an identical machine and reboot. If the new machine causes
the host to get a different hostname (because it has a different MAC
on the NIC, or is in a different place in the rack), as soon as
nova-compute boots up, it will assume all the instances have moved and
will destroy them.

Another example is a vmware deployer that has multiple vcenters. When
bringing up vcenter03.foo.com, the config file contains a typo which
points nova-compute at vcenter02.foo.com. When nova starts, it will
assume that all the instances have been evacuated and will destroy all
their data (on shared storage, even).

Use Cases
----------

A developer wants to enable evacuation on their cloud and have Nova
only destroy data when it has been safely moved to another host.

Project Priority
-----------------

Robustness? Tech debt?

Proposed change
===============

I propose that we make the evacuation code record the action using the
existing migration data structure. That structure contains a
timestamped record of a source host and destination host, and
currently provides a small state machine for confirming or reverting
user-initiated migration requests. We need the exact same thing, but
for evacuation actions, which are confirmed by the source host when it
comes back up when it destroys the data.

When a host starts up, it should:

 1. Check for unconfirmed evacuation migrations where it is the source
    host
 2. Delete the local data, if still present
 3. Mark the migration as completed

This means that we need to add a "type" or "reason" field to the
current migration object so that we can keep user/admin-initiated
migration records separate from evacuation-initiated ones (when and
where appropriate).

Since we keep migration entries in the database, this becomes a sort
of log of actions, including the tombstones left for compute nodes to
clean up when they return. Even if there are multiple evacuations
before recovery begins, each host can make an informed decision about
what to do for recovery.

Alternatives
------------

One alternative is to do what we have now, which is that we guess
about whether we need to delete things based on the host field of an
instance having apparently changed since we last started up. That
means that you can trigger the deletion code by changing your
hypervisor hostname.

A permutation of the above is to use a globally-unique hypervisor
identifier provided by the virt driver attached to an instance. This
functions just like the host field, where we try to guess whether we
should delete something based on the current and expected values for
those fields. However, both of these approaches suffer from the fact
that they're guessing based on circumstantial data instead of a record
that tells us an evacuation was performed.

Data model impact
-----------------

This would re-use our existing migration data structure, so data model
impact would be minor. We would need to add at least one field to
track the method of the migration. This would be something like
"resize", "migrate", or "evacuate". This will let us extend the
migration log model to live migration as well as any other methods of
moving instances around so that the log becomes accurate enough to
make proper decisions.

REST API impact
---------------

No impact to the REST API is necessary as we would continue to only
show user-initiated migrations through the existing API interfaces (as
keyed by the type or reason field added above).

If it is desirable to expose these evacuation-related migrations to
the user/admin then we could either extend the existing os-migrations
API or create a new evacuation-specific interface.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users will not have their data deleted based on a guess. Otherwise
they will not notice this change.

Performance Impact
------------------

There will be additional database traffic on compute node startup to
look up the evacuation records. Since we already look up all
instances, usually for no reason, this could actually reduce the
overall traffic and improve performance at startup.

Other deployer impact
---------------------

No real deployer impact, other than safer operation of the evacuation
recovery code.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Extend the existing migration object to support a reason/type field
* Make the current evacuation code create a migration record when
  instances are evacuated
* Make the compute node startup code use and confirm these records on
  startup instead of guessing based on hostname.
* Mark the destroy_after_evacuate workaround config option as
  deprecated

Dependencies
============

None.

Testing
=======

Testing this in tempest is tricky because it effectively requires
downing a running compute node. Thus, functional tests will be used to
spin up a reasonably full environment with multiple computes in order
to test the feature.

Documentation Impact
====================

No real impact to users or deployers is expected, and thus no
documentation changes are expected.

References
==========

