..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================================
Provide nova-manage commands to refresh block device mapping connection_info
============================================================================

https://blueprints.launchpad.net/nova/+spec/nova-manage-refresh-connection-info

The connection_info associated with a Cinder volume attachment stashed within
Nova's block device mappings can often become stale. Previously operators have
had to query the database directly for an understanding of the current state of
the connection_info and could only migrate or shelve the instance to force a
refresh of this.

This spec aims to outline some basic and potentially backportable
``nova-manage`` commands that will allow operators to both view and refresh the
connection_info of a specific block device mapping within Nova.

Problem description
===================

As suggested above the connection_info of a given volume attachment is stashed
within the block device mapping record associated with an attached volume
within Nova. Over time this connection_info can become stale if changes are
made in the environment, the most common example of which being the changing of
MON IP addresses when using Ceph as the backing store for the Cinder volume
service.

There have also been various migration rollback issues over the years where the
connection_info associated with the block device mapping can actually refer to
that used by another compute host.

In both cases until now the only way to force a refresh of the connection_info
was through another migration or shelve/unshelve that could also fail during
the initial disconnect of the volume.

As such providing operators with a reliable means with which to refresh this
connection_info would be extremely useful.

Use Cases
---------

* As an operator I want to view the current connection_info associated with a
  block device mapping.

* As an operator I want to refresh the connection_info of block device mappings
  attached to a user's STOPPED instance without shelving and unshelving.

Proposed change
===============

Introduce a set of backportable ``nova-manage`` commands to manage the
connection_info associated with a given volume attachment.

.. note::

   ``$bdm_uuid`` below refers to the UUID of the block device mapping record
    within Nova and not the volume attachment UUID within Cinder. Block device
    mapping UUIDs for attached volumes can be obtained using the ``openstack
    server volume list $instance_uuid`` command with openstackclient >= 5.5.0
    or ``nova volume-attachments $instance_uuid`` novaclient command.

Add a command to show the connection_info of a given block device mapping
-------------------------------------------------------------------------

``$ nova-manage bdm show $bdm_uuid``

This command will simply show *all* attributes of the volume attachment as
currently stored within the Nova database.

.. note::

   This should also be accomplished within the ``os-volume_attachments``
   API under a microversion but for the sake of this spec we will only focus on
   the above backportable ``nova-manage`` command.

Add a command to refresh the connection_info of a given block device mapping
----------------------------------------------------------------------------

``$ nova-manage bdm refresh $bdm_uuid``

This command will refresh the connection_info of a given volume based
block device mapping record within Nova.

Prerequisites
~~~~~~~~~~~~~

- The block device mapping refers to an attached volume.

- The instance the block device mapping is attached to must be in a STOPPED
  vm_state.

- The libvirt virt driver is used by the compute hosting the instance.

When these prerequisites are met the command will start by locking the instance
to ensure no user requests will be accepted and potentially race the refresh
of the connection_info.

Then the command will make an RPC call to ``remove_volume_connection`` on the
compute hosting the instance disconnecting the original volume connection from
the compute host using the existing logic within the libvirt virt driver volume
drivers.

The call to ``remove_volume_connection`` will also unmap the volume from the
compute host via Cinder by either calling the ``terminate_connection`` API for
volumes attached using the cinderv2 attachment flow or by deleting the volume
attachment for volumes using the cinderv3 attachment flow.

.. note::

   We cannot precreate a fresh volume attachment for the cinderv3
   attachment flow as the provided connector would conflict with the existing
   attachment and thus result in a failure. This differs to the live migration
   case where the source and destination connectors differ allowing us to have
   two active volume attachments at once within Cinder.

Once the RPC call returns the command we create a fresh cinderv3 volume
attachment using the compute connector with the resulting attachment_id and
connection_info being stashed in the block device mapping record within Nova.

This has the added benefit of migrating some volume attachments from the
cinderv2 to cinderv3 flow. While much more work is required outside of this
spec for Nova to migrate every volume attachment to the newer flow this is at
least a start on that journey.

Finally, the instance will be unlocked allowing the user to now power on the
instance that will in turn connect the volume to the compute host using the
newly updated connection_info.

.. note::

   As with the earlier command this should also be accomplished within the
   ``os-volume_attachments`` API under a new microversion but again for the
   sake of the spec we will only focus on the above backportable command.

Alternatives
------------

Continue to only allow connection_info to be updated by migrating or shelving
an instance. This doesn't scale well and can often lead to more issues when
connection_info has become stale and out dated within an environment.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None, the connection_info for a given attachment is already available to the
owner of said attachment via Cinder. There is a case to make this an admin only
API under a microversion within Cinder in the future, using service credentials
within Nova to facilitate the passing of sensitive attributes like passwords,
tokens and keyrings but for now having a nova-manage command expose what is
stored in our database shouldn't have an impact on our security model.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lyarwood

Other contributors:

Feature Liaison
---------------

Feature liaison:
  lyarwood

Work Items
----------

* Introduce a command to show the attributes of a block device mapping,
  including the volume attachment id and connection_info.

* Introduce a command to refresh the connection_info of a block device mapping.

Dependencies
============

None

Testing
=======

Functional and unit tests will be written to validate these commands. We could
also include integration tests in the form of some post-run playbooks and runs
but this isn't required for these commands to land.

Documentation Impact
====================

As with all nova-manage commands extensive operator facing documentation will
be written detailing commands.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
