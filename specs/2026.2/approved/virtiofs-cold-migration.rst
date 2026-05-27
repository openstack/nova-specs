..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Virtiofs Cold Migration
=======================

https://blueprints.launchpad.net/nova/+spec/virtiofs-cold-migration

When Nova added virtiofs share attachments in Epoxy (2025.1), the
original spec__ explicitly deferred all move operations. Cold
migration (resize/migrate) does not depend on the upstream
virtiofsd/QEMU/libvirt changes needed for live migration because the
instance is stopped during the move. However, Nova's cold migration
code path does not handle shares. This spec describes the
Nova changes needed to lift the cold migration restriction. Live
migration is addressed by a companion spec__.

.. __: https://specs.openstack.org/openstack/nova-specs/specs/2025.1/implemented/libvirt-virtiofs-attach-manila-shares.html

.. __: https://blueprints.launchpad.net/nova/+spec/virtiofs-live-migration

.. _virtiofs-cold-migration-problem-description:

Problem description
===================

Nova blocks cold migration (resize/migrate) for any instance with a
``ShareMapping`` record. The ``resize()`` method in
``nova/compute/api.py`` is decorated with
``@block_shares_not_supported()``, which raises
``ForbiddenWithShare`` (HTTP 409) unconditionally.

Unlike live migration, cold migration has no upstream software
version requirements: the instance is powered off before the move,
so virtiofsd state transfer is not needed. The block exists because
Nova's cold migration code path has two gaps:

1. ``_finish_resize()`` does not mount shares on the destination
   before spawning the instance.
2. ``driver.finish_migration()`` does not pass ``share_info`` to
   ``_get_guest_xml()``, so the domain XML omits ``<filesystem>``
   elements.

Use Cases
---------

As a cloud operator, I want to cold migrate (resize/migrate)
instances with virtiofs share attachments so that I can rebalance
host load or resize flavors without requiring users to detach and
reattach Manila shares.

As an end user, I want my instances with virtiofs mounts to survive
resize operations so that I can change my instance's flavor without
losing access to shared filesystems.

Proposed change
===============

Evacuate, rebuild, shelve, suspend, and cross-cell resize remain
blocked for instances with share attachments. Cross-cell resize
uses a separate conductor-orchestrated code path that has no share
handling; supporting it is left to a future iteration. Concurrent
share attach/detach during migration is prevented by the
``vm_state`` check in the shares API.

Remove the API block
---------------------

Remove ``@block_shares_not_supported()`` from ``resize()`` in
``nova/compute/api.py``. Replace with an inline check via
``objects.Service.get_minimum_version_all_cells()``. The other
decorated methods (``live_migrate``, ``rebuild``, ``shelve``,
``suspend``, ``evacuate``) keep their decorators. The
``live_migrate`` decorator is removed by the live migration spec.

Lazy cleanup strategy
----------------------

The cold migration path (``resize_instance()`` on the source)
calls ``driver.migrate_disk_and_power_off()``, which powers off
the VM and copies disks. It has no share handling. This spec uses
a lazy cleanup strategy: shares stay mounted on the source until
the resize is confirmed. The destination grants access and mounts
shares in ``_finish_resize()``. This makes revert simple: the
source still has shares mounted, so ``_finish_revert_resize()``
only needs to pass ``share_info`` to regenerate domain XML.

Cold migration flow with shares::

  API: resize()                  [version check, all cells]
    -> Conductor
      -> Source: resize_instance()
          power off, copy disks (shares stay mounted)
      -> Dest: _finish_resize()
          grant Manila access, mount shares
          driver.finish_migration(share_info=...)
          spawn instance
    -> User: confirm_resize()
      -> Source: confirm_resize()
          unmount shares, revoke source Manila access,
          unlock shares (Manila deletion/visibility locks)
    -> User: revert_resize()
      -> Dest: revert_resize()
          destroy instance, unmount shares,
          revoke dest Manila access,
          unlock shares (Manila deletion/visibility locks)
      -> Source: _finish_revert_resize()
          driver.finish_revert_migration(share_info=...)
          spawn instance (source still has shares mounted)

The five changes follow the flow above. ``_finish_resize()``
grants Manila access and mounts shares before calling
``driver.finish_migration(share_info=...)``. On partial failure,
already-processed shares are cleaned up before re-raising.
``revert_resize()`` on the destination unmounts and revokes.
``_finish_revert_resize()`` on the source passes ``share_info``
to regenerate domain XML; no re-mount needed because the source
retained both throughout the resize. ``confirm_resize()`` on the
source unmounts and revokes. ``finish_migration()`` and
``finish_revert_migration()`` gain an optional ``share_info``
parameter (default ``None``).

.. _cold-migration-same-host-resize:

Same-host resize
~~~~~~~~~~~~~~~~~

When ``allow_resize_to_same_host=True``, a resize may land on the
same host. In this case shares are already mounted and Manila
access is already granted. ``_finish_resize()`` detects the
same-host case and skips the grant and mount steps.

.. _cold-migration-manila-access-helpers:

Compute manager access helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The existing ``allow_share()`` and ``deny_share()`` RPC methods in
the compute manager carry side effects that are wrong for
migration:

- ``allow_share()`` transitions the ``ShareMapping`` status to
  INACTIVE and sends ``SHARE_ATTACH`` notifications.
- ``deny_share()`` deletes the ``ShareMapping`` database record
  and sends ``SHARE_DETACH`` notifications.

During migration the share remains attached to the instance, so
none of these side effects are appropriate: the ``ShareMapping``
must not change status or be deleted, and attach/detach
notifications must not be sent.

Two new private methods are factored out of the existing RPC
methods, retaining only the Manila API calls:

- ``_grant_share_access(context, share_mapping)``: calls
  ``manila_api.allow()`` and polls until the access rule is active.
- ``_revoke_share_access(context, share_mapping)``: calls
  ``manila_api.deny()`` to remove the access rule.

.. _cold-migration-mount-path-compatibility:

Mount path compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~

The mount path is computed deterministically by
``_get_share_mount_path()``:
``<mount_point_base>/<hash(export_location)>``. All compute hosts
in a migration-eligible pool must use the same mount point base
(``nfs_mount_point_base`` for NFS, ``ceph_mount_point_base`` for
CephFS).

.. _cold-migration-cephfs-access:

CephFS access management
~~~~~~~~~~~~~~~~~~~~~~~~~~

CephFS uses user-based access rules (not IP-based like NFS), so
all hosts share the same credentials. Manila deduplicates on grant.
``_revoke_share_access()`` checks cross-instance usage via
``ShareMappingList.get_by_share_id()`` and preserves the access
rule if any instance still uses the share.

Manila access rule window
~~~~~~~~~~~~~~~~~~~~~~~~~~

During cold migration both hosts have Manila access. The window
opens at ``_finish_resize()`` and closes at ``confirm_resize()``
or ``revert_resize()``. This matches the volume live migration
pattern. Stale rules leaked by error scenarios can be cleaned by
a periodic task in a follow-up patch.

Alternatives
------------

**Do nothing.** Users cannot cold migrate instances with shares.
Operators must ask users to detach shares, migrate, and reattach.

**Eager source cleanup.** Unmount and revoke on the source in
``resize_instance()`` immediately after power off. This avoids the
dual-access window but complicates revert: the source must
re-grant and re-mount. The lazy strategy is simpler.

Data model impact
-----------------

None

REST API impact
---------------

A new microversion lifts the ``ForbiddenWithShare`` block on
``resize()`` for instances with share attachments. The
microversion signals that the deployment's API supports the
operation; the actual compute service version check happens
server-side at request time. Ideally a single microversion would
cover both cold and live migration, but if the implementations
land in separate releases, each will introduce its own
microversion.

Security impact
---------------

The dual Manila access window is the primary consideration. The
risk profile matches volume live migration.

Notifications impact
--------------------

No new notifications. The existing resize notifications
(``resize_finish``, ``resize_confirm``, ``resize_revert``)
already cover the operations where shares are granted, mounted,
unmounted, and revoked. The refactored access helpers (see
:ref:`cold-migration-manila-access-helpers`) reuse the Manila
API call logic from share attach/detach but suppress
``SHARE_ATTACH`` and ``SHARE_DETACH`` notifications because
they would be misleading during migration. This is consistent with how
volumes are handled during migration.

Other end user impact
---------------------

None

Performance Impact
------------------

Each share adds one Manila ``allow`` API call and one mount
operation to ``_finish_resize()`` latency.

Other deployer impact
---------------------

No minimum virtiofsd, QEMU, or libvirt version requirements
beyond those already needed for virtiofs share attachments
(Ubuntu 24.04 LTS included). All compute hosts in a
migration-eligible pool must use matching mount point base
configuration values and have file-backed memory or hugepages
configured.

Developer impact
----------------

``finish_migration()`` and ``finish_revert_migration()`` in the
virt driver base class gain an optional ``share_info`` parameter
(default ``None``). Existing driver implementations (fake, ironic)
need no modification.

Upgrade impact
--------------

A compute service version bump is required. The API block on cold
migration for instances with shares is only removed once the
minimum compute service version across the deployment meets or
exceeds the new version. Operators can verify upgrade status with
``openstack compute service list`` (version column). During a
rolling upgrade, the API continues to block cold migration until
all hosts are upgraded.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gouthamr (Goutham Pacha Ravi)

Other contributors:
  - Uggla (Rene Ribaud)
  - carloss (Carlos Eduardo da Silva)

Feature Liaison
---------------

Feature liaison:
  Liaison Needed

Work Items
----------

1. Add ``_grant_share_access()`` and ``_revoke_share_access()``
   private methods to the compute manager (also used by live
   migration).
2. Add share handling in ``_finish_resize()``,
   ``revert_resize()``, ``_finish_revert_resize()``, and
   ``confirm_resize()``.
3. Extend ``driver.finish_migration()`` and
   ``driver.finish_revert_migration()`` to accept ``share_info``.
4. Add functional tests using the libvirt fixture: success,
   failure, revert, and mount path mismatch scenarios.
5. Update ``doc/source/admin/manage-shares.rst``.
6. Add the microversion, replace
   ``@block_shares_not_supported()`` on ``resize()`` with an
   inline minimum service version check, and add tempest tests.

A periodic task to clean up stale Manila access rules leaked by
error scenarios (e.g., Manila unreachable during confirm) is
desirable but not required for the core feature and will be
addressed in a follow-up patch.

Dependencies
============

* No dependency on the companion `live migration spec`_. The two
  specs share the ``_grant_share_access()`` and
  ``_revoke_share_access()`` helpers; whichever lands first defines
  them.

* No upstream virtiofsd, QEMU, or libvirt version dependencies
  beyond those already needed for virtiofs share attachments.

.. _live migration spec: https://blueprints.launchpad.net/nova/+spec/virtiofs-live-migration


Testing
=======

**Functional tests (libvirt fixture):**

- Success: shares mounted on destination, domain XML includes
  ``<filesystem>`` elements. Source cleaned up on confirm.
- Revert: destination shares cleaned up, source shares remain,
  instance restarts with shares on source.
- Partial failure in ``_finish_resize()``: shares cleaned up,
  Manila access revoked.
- Mount path mismatch: clear error when configs differ.

**Tempest tests** (two compute hosts, file-backed memory, Manila
NFS or CephFS share):

- Cold migrate with one NFS share; verify after confirm.
- Cold migrate and revert; verify on original host.
- Cold migrate with multiple shares.


Documentation Impact
====================

``doc/source/admin/manage-shares.rst`` is updated to document
cold migration support, the mount point base matching requirement,
and which operations remain blocked.

References
==========

* Original virtiofs Manila shares spec (2025.1):
  https://specs.openstack.org/openstack/nova-specs/specs/2025.1/implemented/libvirt-virtiofs-attach-manila-shares.html

* Companion live migration spec:
  https://blueprints.launchpad.net/nova/+spec/virtiofs-live-migration


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.2 Hibiscus
     - Introduced
