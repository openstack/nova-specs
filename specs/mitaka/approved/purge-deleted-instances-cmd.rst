..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add nova-manage db purge-deleted-instances
==========================================

https://blueprints.launchpad.net/nova/+spec/purge-deleted-instances-cmd

Until we have automated `DB archival <https://review.openstack.org/#/c/137669/>`_
or `Purge soft deleted rows <https://review.openstack.org/#/c/184637/>`_ we
should have a way to purge soft deleted instances from the database along with
their related meta tables like instance_metadata, instance_system_metadata,
instance_info_cache, instance_extra, tags, etc. basically whatever shows up
in nova.objects.Instance.INSTANCE_OPTIONAL_ATTRS where there is a backref
to instances in the data model.


Problem description
===================

Lots of deployments already have a set of tools/scripts that already do
something like this but they have to go directly into the nova database to do
it. With a nova-manage db command we can at least ship it with the code and
test it until better solutions are implemented, like the aforementioned archive
or no more soft delete specs.

Use Cases
----------

As a cloud operator, I want to manage the size of my database by purging
soft deleted instances - and I don't care about archiving to shadow tables.


Proposed change
===============

Write a command which would be similar to the
`nova-manage db null-instance-uuid-scan command` [#f1]_ which finds all
instances records where deleted != 0 along with those related backref table
records (foreign keys back to the instances table) and deletes them all
(the purge). The list of tables would be via whitelist.

.. note::

  The command is scanning for instances.deleted != 0, not the actual
  SOFT_DELETED vm_state which is checked with the reclaim_instance_interval
  configuration option in the _reclaim_queued_deletes periodic task. [#f2]_

There will be a ``--dry`` option for just dumping what is found but does not
actually delete anything.

There will be an ``--older-than`` option for limiting how far back, in days, a
deleted instance was deleted (based on the deleted_at column) before it's
removed. By default this would be 90 days.

The help text on the command will have a warning mentioning the risks of
running the command and actually deleting data so people should be aware of
what they are doing.

Until we have alternatives for better archive capability with the option to
hard-delete *and/or* we remove support for the
`SoftDeleteMixin <http://docs.openstack.org/developer/oslo.db/api/sqlalchemy/models.html#module-oslo_db.sqlalchemy.models>`_
from the data model so that delete actually does a hard-delete, this is meant
to be a temporary command. Having said that, depending on how useful this is
and what comes in the future, this may live in the tree for a long time.

**Whitelist of impacted tables:**

* block_device_mapping
* consoles
* instances
* instance_actions_events
* instance_actions
* instance_extra
* instance_faults
* instance_info_cache
* instance_metadata
* instance_system_metadata
* migrations
* pci_devices
* security_group_instance_association
* tags
* virtual_interfaces

.. note::

  * The fixed_ips table is not included since instances are associated to
    fixed_ips based on lease/release operations with nova-network and the
    ForeignKeyConstraint should only hold up while the instance is not (soft)
    deleted. [#f3]_
  * The security_groups table is not included since a security group can apply
    to multiple instances.

Alternatives
------------

* Do nothing and let operators handle this on their own.

* Wait for the `DB archival framework <https://review.openstack.org/#/c/137669/>`_.

* Wait for us to address `the SoftDeleteMixin in the data model <https://review.openstack.org/#/c/184645/>`_.

* Wait for a `periodic task to purge deleted rows <https://review.openstack.org/#/c/184637/>`_.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The nova-manage command is only available to admins. Obviously any entry point
to deleting data permanently is dangerous but this spec assumes the deployer
has taken the necessary security precautions to lock down access to the
nova-manage command already.

Purging deleted rows also impacts the ability to perform audits.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

There could be some impact when doing a large purge, so as part of the command
implementation there will be a ``--max-number`` option like the
`nova-manage db migrate_flavor_data` command. [#f4]_

Other deployer impact
---------------------

None

Developer impact
----------------

If new tables are added which have a backref to the instances table and use
the SoftDeleteMixin in the data model, they should consider registering
with the `nova-manage db purge-delete-instances` command.


Implementation
==============

Assignee(s)
-----------

Primary assignee:

* Cale Rath <ctrath@us.ibm.com>

Other contributors:

* Matt Riedemann <mriedem@us.ibm.com>
* Dan Smith <dms@danplanet.com>

Work Items
----------

* Add the command to nova.cmd.manage.DbCommands.
* ?
* Profit!


Dependencies
============

None


Testing
=======

* Functional testing within the nova code tree should be sufficient.
* Test scenarios would include:

  * Create an instance record with related backref tables (metadata,
    system_metadata, info_cache, tags, etc), delete the instance
    (instances.deleted != 0), run the purge command, verify that the record is
    gone from the instances table and the related backref table records are
    also deleted.
  * Set an instance.vm_state to 'SOFT_DELETED' and instance.deleted=0, run the
    purge command, verify that the record is still in the instances table.


Documentation Impact
====================

* Release notes and nova-manage db command ``--help`` text as usual.


References
==========

* Previous/other attempts in Nova:

  * https://blueprints.launchpad.net/nova/+spec/db-purge-engine
  * https://blueprints.launchpad.net/nova/+spec/purge-soft-deleted-rows

* Related mailing list: http://lists.openstack.org/pipermail/openstack-operators/2014-October/005257.html

* WIP change: https://review.openstack.org/#/c/203751/

.. [#f1] http://git.openstack.org/cgit/openstack/nova/tree/nova/cmd/manage.py?id=12.0.0.0b1#n954
.. [#f2] http://git.openstack.org/cgit/openstack/nova/tree/nova/compute/manager.py?id=12.0.0.0b1#n5840
.. [#f3] http://git.openstack.org/cgit/openstack/nova/tree/nova/db/sqlalchemy/models.py?id=12.0.0.0b1#n867
.. [#f4] http://git.openstack.org/cgit/openstack/nova/tree/nova/cmd/manage.py?id=12.0.0.0b1#n983


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
