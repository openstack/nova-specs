..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Virt Driver Objects Support (Juno Work)
==========================================

https://blueprints.launchpad.net/nova/+spec/virt-objects-juno

This blueprint represents the remaining work to be done in Juno around
moving the virt drivers to using objects instead of raw conductor
methods. This is important because objects provide versioning of the
actual data, which supports our upgrade goals.

Problem description
===================

Nova virt drivers still send and receive unversioned bundles of data
using conductor methods, which is problematic during an upgrade where
the format of the data has changed across releases.

Proposed change
===============

Migrate uses of raw conductor methods in the virt drivers to
objects. For example, consider this::

  instance = conductor.instance_get_by_uuid(context, uuid)
  conductor.instance_update(context, instance['uuid'],
                            host='foo')

would become::

  instance = instance_obj.Instance.get_by_uuid(context, uuid)
  instance.host = 'foo'
  instance.save()

Using the objects mechanism allows older code to interact with newer
code, backleveling the format of the instance object as necessary.

Alternatives
------------

This is the accepted direction of the project to solve this
problem. However, alternatives would be:

1. Don't solve the problem and continue using unversioned data
2. Attempt to enforce version bumps of individual methods when any
   data (including nested downstream data) has changed

Data model impact
-----------------

None.

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

The following virt driver methods still need attention:

* attach_volume
* check_can_live_migrate_destination
* check_can_live_migrate_source
* check_instance_shared_storage_local
* cleanup
* default_device_names_for_instance
* default_root_device_name
* destroy
* detach_volume
* dhcp_options_for_instance
* ensure_filtering_rules_for_instance
* get_diagnostics
* get_info
* get_volume_connector
* inject_file
* inject_network_info
* live_migration
* macs_for_instance
* post_live_migration
* pre_live_migration
* refresh_instance_security_rules
* reset_network
* rollback_live_migration_at_destination
* unfilter_instance
* unplug_vifs


Dependencies
============

There is a cross-dependency between this blueprint and the following:

  https://blueprints.launchpad.net/nova/+spec/compute-manager-objects-juno

At times, a virt driver will need to be passed an object by the
compute manager, and thus finishing the conversion of a virt driver
method requires the calling compute manager method to be converted as
well.


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

* https://blueprints.launchpad.net/nova/+spec/virt-objects
* https://blueprints.launchpad.net/nova/+spec/compute-manager-objects
* https://blueprints.launchpad.net/nova/+spec/unified-object-model
