..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Add notifications for hypervisor
================================

https://blueprints.launchpad.net/nova/+spec/hypervisor-notification

Currently, no notification will be sent for compute node state change,
so it is not possible for external system to get notifications when
there are compute nodes created, updated or deleted.

Having such notifications help external system to get the up to date compute
node status and metrics.

Problem description
===================

Use Cases
---------

The external system like Searchlight[1] wants to index the compute nodes
which makes the query for large number of compute nodes more fast and
efficient.

The maintainer wants to get the notifications when there are compute nodes
added or removed.

Proposed change
===============

Versioned notifications will be added for the following actions:

* ComputeNode.create
* ComputeNode.save
* ComputeNode.destroy

.. note:: Notification will be sent only if any of the specified fields(
          "vcpus", "memory_mb", "local_gb", "vcpus_used", "local_gb_used",
          "hypervisor_hostname", "disk_available_least", "running_vms",
          "current_workload") changed to avoid unnecessary notifications
          with the same content.

Alternatives
------------
None

Data model impact
-----------------

No database schema change is needed.

The following new objects will be added to compute_node for create and update:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class ComputeNodeNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ComputeNodePayload')
        }

    @base.NovaObjectRegistry.register
    class ComputeNodePayload(notification.NotificationPayloadBase):
        # Version 1.0: Initial version
        SCHEMA = {
            'id': ('compute_node', 'id'),
            'uuid': ('compute_node', 'uuid'),
            'host': ('compute_node', 'host'),
            'vcpus': ('compute_node', 'vcpus'),
            'memory_mb': ('compute_node', 'memory_mb'),
            'local_gb': ('compute_node', 'local_gb'),
            'vcpus_used': ('compute_node', 'vcpus_used'),
            'memory_mb_used': ('compute_node', 'memory_mb_used'),
            'local_gb_used': ('compute_node', 'local_gb_used'),
            'hypervisor_type': ('compute_node', 'hypervisor_type'),
            'hypervisor_version': ('compute_node', 'hypervisor_version'),
            'hypervisor_hostname': ('compute_node', 'hypervisor_hostname'),
            'free_ram_mb': ('compute_node', 'free_ram_mb'),
            'free_disk_gb': ('compute_node', 'free_disk_gb'),
            'current_workload': ('compute_node', 'current_workload'),
            'running_vms': ('compute_node', 'running_vms'),
            'disk_available_least': ('compute_node', 'disk_available_least'),
            'host_ip': ('compute_node', 'host_ip'),
        }
        VERSION = '1.0'
        fields = {
            'id': fields.IntegerField(),
            'uuid': fields.UUIDField(),
            'host': fields.StringField(nullable=True),
            'vcpus': fields.IntegerField(),
            'memory_mb': fields.IntegerField(),
            'local_gb': fields.IntegerField(),
            'vcpus_used': fields.IntegerField(),
            'memory_mb_used': fields.IntegerField(),
            'local_gb_used': fields.IntegerField(),
            'hypervisor_type': fields.StringField(),
            'hypervisor_version': fields.IntegerField(),
            'hypervisor_hostname': fields.StringField(nullable=True),
            'free_ram_mb': fields.IntegerField(nullable=True),
            'free_disk_gb': fields.IntegerField(nullable=True),
            'current_workload': fields.IntegerField(nullable=True),
            'running_vms': fields.IntegerField(nullable=True),
            'disk_available_least': fields.IntegerField(nullable=True),
            'host_ip': fields.IPAddressField(nullable=True),
        }
        def __init__(self, compute_node):
            super(ComputeNodePayload, self).__init__()
            self.populate_schema(compute_node=compute_node)

The following new objects will be added to compute_node for delete:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class ComputeNodeDeleteNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ComputeNodeDeletePayload')
        }

    @base.NovaObjectRegistry.register
    class ComputeNodeDeletePayload(notification.NotificationPayloadBase):
        # Version 1.0: Initial version
        SCHEMA = {
            'id': ('compute_node', 'id'),
            'uuid': ('compute_node', 'uuid'),
        }
        VERSION = '1.0'
        fields = {
            'id': fields.IntegerField(),
            'uuid': fields.UUIDField(),
        }
        def __init__(self, compute_node):
            super(ComputeNodeDeletePayload, self).__init__()
            self.populate_schema(compute_node=compute_node)

The definition of NotificationBase can be found [2].

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------

New notifications compute_node.create (will be sent after a compute node
created), compute_node.update (will be sent after the non static fields of
a compute node updated) and compute_node.delete (will be sent after a compute
node deleted) will be introduced with INFO priority and payload of the
notifications will be the serialized form of the already existing
ComputeNode versioned object.

Other end user impact
---------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  liyingjun

Work Items
----------

* Send new notifications when a compute node created, updated or deleted.

Dependencies
============
None

Testing
=======

Besides unit test new functional test cases will be added to cover the
new notifications.

Documentation Impact
====================
None

References
==========

[1]: Searchlight: http://docs.openstack.org/developer/searchlight/index.html
[2]: Versioned notification: http://docs.openstack.org/developer/nova/notifications.html#versioned-notifications

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
