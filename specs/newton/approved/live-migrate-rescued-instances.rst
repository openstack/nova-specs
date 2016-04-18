..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================

============================================================

Blueprint:https://blueprints.launchpad.net/nova/+spec/live-migrate-rescued-instances

When an instance is rescued the libvirt driver creates a file in the
instance directory that contains the original instance xml. This file
is used when unrescuing the instance to revert to the original disk
configuration. However, this file is not necessary to restore the
instance's original configuration. Furthermore the reliance on this
file means we currently cannot live migrate a rescued instance.  Thus
it is proposed that we do not create this file during the rescue
operation and rebuild the instance's original xml file from the
database when we unrescue it.

Problem description
===================

At present operators cannot live migrate rescued instances.

Use Cases
----------

As an operator of an OpenStack cloud, I like to live migrate all
active instances on a node in order to perform maintenance.

Proposed change
===============

The Live migration method in the compute manager will be amended to
permit migration of instances in a rescued state. The implementation
of rescue and live migration operations are different for each driver.

Hyper-V

Have recently added support for rescue and live migration of rescued
instances is supported.

VMware

Does not currently support live migration of instances across compute
nodes but proposed patch https://review.openstack.org/#/c/270116/ will
address this. When this is implemented live migration of rescued
instances will be supported.

XenAPI and Libvirt

Do not currently support the live migration of rescued instances due
to information stored locally on the compute node when an instance is
rescued. Live migration does not copy this information to the target
compute node so a subsequent unrescue operation would fail.

The proposal is to amend how rescue and unrescue are implemented in
the XenAPI and Libvirt drivers.

In the libvirt driver rescue method  saves the current domain xml in a
local file and the unrescue method uses this to revert the instance to
its previous setup, i.e. booting from instance primary disk again
rather than rescueimage. However saving the previous state in the
domain xml file is unnecessary since during unrescue the domain is
destroyed and restarted. This is effectively a hard reboot so I just
call hard reboot during the unrescue operation.  Hard reboot rebuilds
the domain xml from the nova database so the domain xml file is not
needed.

A similar approach is proposed for XenAPI.

in order to support drivers that do not support live migration of
instances in a rescued state a new driver capabilities flag will be
added called code:`supports_live_migrate_rescued`. This will be set to
False for drivers that do not support the migration of rescued
instances.

If the driver supports live migration of instances in a rescued state
the os-migrateLive action API call will return a response code of 202
instead of 409 when an attempt is made to perform a live migration of
an instance in a rescued state so a new API microversion will be
introduced.

If the driver does not support live migration of instances in a rescued
state then a 400 response will be returned with a message indicating
that the driver does not support live migration of instances in a
rescued state. The response message will identify the compute node
that does not support live migration of rescued instances, i.e.
source or destination and compute node name. This is useful during
upgrade when some compute nodes may not yet have been upgraded to
the version that supports the migration of rescued instances.

Live migration already preserves the current instance status whether
the migration successful or rolled back.

Alternatives
------------

One alternative is not doing this, leaving it up to operators to ask
the user to unrescue their instance so it can be migrated.

Another option is to write the original instance state to the database
during the rescue operation so that it can be retrieved by the target
compute node during unrescue. However this is unnecessary and would
require a database schema change to add a table to store this
information.

Data model impact
-----------------

None.

REST API impact
---------------

To be added in a new microversion.

This is required because a live migration operation on an instance in
a rescued state will return 202 instead of the current 409 response.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

User attemting to unrescue an instance whilst a migration was in
progress would be prevented from doing so until the migration was
complete.

Performance Impact
------------------

None

Other deployer impact
---------------------

During upgrade live migrations of rescued instances may fail with a
400 response due to one of the source or destination nodes not yet
being upgraded.

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
None

Work Items
----------

* Change compute API live migration methods to allow migration of
  rescued instances.
* Bump python-novaclient API version.
* Change libvirt driver rescue and unrescue functions.
* Change compute manager unrescue to pass context object to virt/driver
  unrescue method and change implementations of virt/driver unrescue to
  accept context parameter (This is required by libvirt driver unrescue
  in order to utilize the driver's hard_reboot method)
* Change XenAPI driver rescue and unrescue methods to remove the use of
  information held locally on the compute node.
* Implement a driver capability check to if the driver supports live
  migration of rescued instances.

Dependencies
============

None

Testing
=======

Unit tests will be added as required.
Also tempest tests to verify the use of live migration of an instance
in a rescued state and subsequent unrescuing of the instance.

Documentation Impact
====================

New API needs to be documented:

* Compute API extensions documentation
  http://developer.openstack.org/api-ref-compute-v2.1.html

* nova.compute.api documentation
  http://docs.openstack.org/developer/nova/api/nova.compute.api.html

References
==========

https://review.openstack.org/#/c/308198

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced

