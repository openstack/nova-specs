.. _queens-priorities:

=========================
Queens Project Priorities
=========================

List of efforts the Nova development team is prioritizing for reviews in the
Queens release (in no particular order).

Cells v2
--------

In Pike, the control plane was made multi-cell aware. However, there are some
`limitations`_. Priorities in Queens are related to removing some of those
limitations.

* `Efficient multi-cell instance listing`_: Improve the performance of listing
  instances across multiple cells and merge sort the results. This is achieved
  by concurrently querying the cells and then sorting the results as they are
  processed.
* `Alternate hosts`_: Support rescheduling across compute hosts within a cell
  during the initial create or migration of an instance by having the scheduler
  provide a primary selected host and a list of alternate hosts. The alternate
  hosts will be used within the cell to reschedule in case the primary selected
  host fails to build / migrate the instance. This avoids the need for the
  cell conductor service to need to communicate back up to the scheduler
  service.

.. _limitations: https://docs.openstack.org/nova/pike/user/cellsv2_layout.html#caveats-of-a-multi-cell-deployment
.. _Efficient multi-cell instance listing: https://blueprints.launchpad.net/nova/+spec/efficient-multi-cell-instance-list-and-sort
.. _Alternate hosts: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/return-alternate-hosts.html

Placement
---------

* `Migration allocations`_: Remove technical debt introduced in the Pike
  release with how resource allocations are tracked in the Placement service
  during a move operation (cold and live migrate). Rather than "double"
  allocations for an instance on both the source and destination compute node
  resource providers, the instance allocation will be created on the
  destination node and the current source node allocation will be temporarily
  tracked against the migration record until the operation completes, at which
  point the migration allocation against the source node is deleted.
* `Nested resource providers`_: Add the ability to model a tree of resource
  providers within the Placement service such that more complicated resource
  relationships can be tracked and used during scheduling, such as a compute
  node resource provider with child physical functions which in turn have
  child virtual functions for modeling SR-IOV capabilities.

.. _Migration allocations: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/migration-allocations.html
.. _Nested resource providers: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html

Volume multi-attach
-------------------

This is a two-part effort.

* `Use the Cinder volume attachments API`_: Introduced with the block storage
  `3.27 API microversion`_, Cinder can accurately track multiple attachments
  for a single volume, including storing the storage backend
  ``connection_info`` and compute host ``connector``, which historically is
  stored in the Nova ``block_device_mappings`` database table. This is an
  internal plumbing change to Nova and will be transparent to end users of the
  compute API. This will improve the separation of duties between the compute
  and block storage services, reduce technical debt in the compute service
  long-term, and build a foundation on which volume multi-attach support can
  be added.
* `Support multi-attachable volumes`_: Once Nova can support new-style volume
  attachments we can work on adding the changes to the API and at least the
  libvirt driver to attach a volume to more than one instance. There will be
  some changes needed to the block storage API for modeling volume storage
  backends that use shared targets, and Cinder will introduce policy rules so
  operators can configure if and how you can use multi-attach volumes, but
  basic support should be available, including boot from a multi-attach volume.

.. _Use the Cinder volume attachments API: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/cinder-new-attach-apis.html
.. _3.27 API microversion: https://developer.openstack.org/api-ref/block-storage/v3/#attachments
.. _Support multi-attachable volumes: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/cinder-volume-multi-attach.html
