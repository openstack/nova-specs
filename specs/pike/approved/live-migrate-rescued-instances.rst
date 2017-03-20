..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Live Migration of Rescued Instances
==========================================

https://blueprints.launchpad.net/nova/+spec/live-migrate-rescued-instances

Add support to live migrate rescued instances. Currently instances in rescued
state cannot be live migrated. This might be an issue during upgrades as all
the active instances in the host needs to be migrated using live-migrate.

Problem description
===================

Currently if an operator wants to upgrade a host with rescued instance, it
needs to be unrescued and live migrated before proceeding with maintenance
operation.

During rescue operation, libvirt driver creates set of files in the instance
directory. These files are used when unrescuing the instance to revert to the
original disk configuration. During live migration of rescued instance, libvirt
only moves files to destination host that it knows of, leaving behind the
files created by libvirt driver in source host. This causes unrescue to fail
on destination node.

This implementation will allow live migration of rescued instances for
libvirt driver and add driver capabilities flag to check if the driver
supports live migration of rescued instances.

Use Cases
---------

* Operators would like to live migrate all running instances including VM's
  that are currently in rescued state before performing any maintenance
  activities on the host and ensuring 100% uptime for all VM's in running
  state.

* Operators prefer to live migrate rescued instance without the hassle of
  unrescuing them before live migration. This creates better user experience
  to the operator and reduces any service interruptions to the end user.

Proposed change
===============

A new API microversion will be introduced to allow live migration of
instances in rescued state. In the new microversion, minimum nova-compute
service version in the deployment is checked for the support of live
migration of rescued instances else the requests fails at the API level.
This is useful during upgrade when some compute nodes may not have been
upgraded to the version that supports the migration of rescued instances.

A new driver capability flag called `supports_live_migrate_rescued` will
be added to all drivers and set to True or False depending on their ability
to live migrate rescued instance. This spec will only enable this for libvirt
driver. All other drivers will fail to live-migrate if you attempt to
live-migrate an instance in the rescued state. Driver's support to
live migrate rescued instance is checked at pre-live migration phase which
is an async operation. Any failures due to driver's capability to support
live migration of rescued instance, will be updated in instance-actions
with the error message, just as we do for any other pre-live migration errors.

Presently in live migration, files that are created by libvirt driver while
rescuing instance are not copied to the target compute node. The proposal is
to copy unrescue.xml from source to destination host, download kernel.rescue
and ramdisk.rescue if they exist on image service else fallback to copy those
files from source host. These operations are carried out during pre-live
migration phase.

Alternatives
------------

* One alternative is, leaving it up to operators to ask the user to unrescue
  their instance so it can be migrated.

* Another option is to write the original instance state to the database during
  the rescue operation so that it can be retrieved by the target compute node
  during unrescue. We are considering this idea separately to this spec around
  live-migration.

Data model impact
-----------------

None

REST API impact
---------------

A new microversion is required because os-migrateLive action API call will
return a response code of 202 instead of the current 409 response.

When not all compute nodes are upgraded to minimum compute version that
supports this functionality 409 response is returned.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Bump python-novaclient API version.

Performance Impact
------------------

None

Other deployer impact
---------------------

This features is available only when all compute nodes are upgraded.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sivasathurappan Radhakrishnan(siva_krishnan)

Other contributors:
  Raj Singh(raj_singh)


Work Items
----------

* Implement driver capability check to verify if the driver supports live
  migration of rescued instances and copy the rescued instance files created
  by libvirt driver to the destination host prior to migration

* Change compute API live migration methods to allow migration of
  rescued instances and check for minimum compute version across deployments.

* Bump python-novaclient API version.

Dependencies
============

None

Testing
=======

* Unit tests will be added as required.

* Add tempest tests to verify the use of live migration of an instance in a
  rescued state and subsequent unrescuing of the instance.


Documentation Impact
====================

Need to document API changes in api-ref:

* Compute API extensions documentation
  http://developer.openstack.org/api-ref-compute-v2.1.html

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
   * - Pike
     - Reproposed and Updated