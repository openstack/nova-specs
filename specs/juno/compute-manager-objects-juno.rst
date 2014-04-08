..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Compute Manager Objects Support (Juno Work)
===========================================

https://blueprints.launchpad.net/nova/+spec/compute-manager-objects-juno

This blueprint represents the remaining work to be done in Juno around
moving the compute manager (and associated modules, like
nova.compute.utils) to using objects instead of raw conductor
methods. This is important because objects provide versioning of the
actual data, which supports our upgrade goals.

Problem description
===================

The nova compute manager still sends unversioned bundles of data using
conductor and compute RPC methods, which is problematic during an
upgrade where the format of the data has changed across releases.
This is especially important for compute manager, because it is likely
that it will be speaking to a newer conductor and compute node at
times. During an upgrade, migrate and live-migrate operations are
expected, and by nature will involve compute nodes running different
versions of the code to communicate.

Proposed change
===============

Migrate uses of raw condutor methods in the compute manager to
objects. For example consider this::

  service_ref = self.conductor_api.service_get_by_compute_host(
          context, self.host)
  self.conductor_api.compute_node_delete(context, service_ref['compute_node'])

would become::

  service = service_obj.Service.get_by_compute_host(context,
                                                    self.host)
  service.compute_node.destroy()

Alternatives
------------

This is the accepted direction of the project to solve this
problem. However, alternatives would be:

1. Don't solve the problem and continue using unversioned data
2. Attempt to enforce version bumps of individual methods when any
   data (including nested downstream data) has changed

Data model impact
-----------------

The low-level data model (i.e. the SQLAlchemy models) will not need to
change. However, additional high-level objects may be added where
necessary to provide versioned wrappers around the low-level models.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

In general, conversion of code to use objects does not affect
notifications. However, at times, emission of notifications is
embedded into an object method to achieve higher consistency about
when and how the notifications are sent. No such changes are
antitipated in this work, but it's always a possibility.


Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Moving to objects enhances the ability for deployers to incrementally
roll out new code. It is, however, largely transparent for them.

Developer impact
----------------

This is normal refactoring, so the impact is minimal. In general,
objects-based code is easier to work with, so long-term it is a win
for the developers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* check_can_live_migrate_destination
* check_can_live_migrate_source
* live_migration
* _post_live_migration
* _rollback_live_migration
* _rollback_live_migration_at_destination
* refresh_instance_security_rules
* run_instance
* detach_volume
* Remaining uses of instance[attr] in compute/manager.py

Dependencies
============

There is a cross-dependency between this blueprint and the following:

  https://blueprints.launchpad.net/nova/+spec/virt-objects-juno

At times, a virt driver will need to be modified to accept an object
from the compute manager before the manager method can be fully
converted.

Testing
=======

In general, unit tests require minimal change when this happens,
depending on how the tests are structured. Ideally, they are already
mocking out database calls, which means the change to objects is a
transparent one. In reality, this usually means minor tweaking to the
tests to return whole data models, etc.

Documentation Impact
====================

None.

References
==========

* https://blueprints.launchpad.net/nova/+spec/compute-manager-objects
* https://blueprints.launchpad.net/nova/+spec/virt-objects
* https://blueprints.launchpad.net/nova/+spec/unified-object-model
