..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Expose auto converge and post copy
==================================

https://blueprints.launchpad.net/nova/+spec/expose-auto-converge-post-copy

Problem description
===================

Currently auto converge and post copy can only be enabled/disabled via
configuration, which is somewhat inflexible. If an application sensitive to
reduced performance (some scientific computing applications may be more
sensitive to memory access latency) is on a host with these options enabled,
live migration may cause the application to raise an error. Therefore, the user
wants to control whether to enable/disable auto converge or post copy during
live migration.

Use Cases
---------

* Some applications do not want increased risk of being rebooted due to a
  network failure or memory page access failure during post-copy
  live-migration.

* Some applications are performance sensitive (such as some scientific
  computing applications); such applications do not want performance throttled
  back by the auto-converge feature during live-migration.

* Some applications would like to avoid reboot risk and performance
  throttling. If the network between two compute nodes is interrupted during
  post-copy live-migration, the live-migration will fail and the user will need
  to reset the instance to make it available. Therefore such applications do
  not want use both features during live-migration.

* For the above problems, the operator wants to control whether a single
  instance enables auto converge or post copy during live migration. But
  currently the minimum unit that can be controlled is the compute node.

Proposed change
===============

Support for auto converge and post copy requires QEMU version >= 2.5.0. Since
the Rocky release, the minimum required version of QEMU is 2.5.0 [1]_.
Therefore, all compute nodes using the libvirt driver should support these
features. There are flags from the libvirt ``virDomainMigrateFlags`` enum
[2]_::

  ...
  VIR_MIGRATE_AUTO_CONVERGE = 8192
  VIR_MIGRATE_POSTCOPY = 32768
  ...

The configurations ``live_migration_permit_auto_converge`` and
``live_migration_permit_post_copy`` can only affect the hypervisor by
modifying the configuration, but traits can affect a single instance.

In order to request the feature (scheduling an instance to nodes that provide
the feature) we propose defining two new traits. The traits are reported by the
libvirt driver, regardless of the conf:

*  ``COMPUTE_MIGRATE_AUTO_CONVERGE``
*  ``COMPUTE_MIGRATE_POST_COPY``

Introduce two new flavor extra specs:

* ``compute:live_migration_auto_converge=true/false``
* ``compute:live_migration_post_copy=true/false``

And introduce two new image properties:

* ``compute_live_migration_auto_converge=true/false``
* ``compute_live_migration_post_copy=true/false``

Use these properties, instead of asking the operator to set
``required``/``forbidden`` on the traits. Before calling placement, when
``compute:live_migration_auto_converge=true`` or
``compute:live_migration_post_copy=true``, we add required traits
for the corresponding feature to the placement request. When
``compute:live_migration_auto_converge=false`` and
``compute:live_migration_post_copy=false``, we just add nothing to
the placement request. Thus we still can schedule an instance on a host with
the features but we disable these two features for that instance. We use these
keys in the scheduler to optionally add required traits to ensure that the
instance can land on a host that is capable of the requested behavior. The
libvirt driver will then interpret the values to decide whether to use the
features during live migration. For example, if the flavor says "false":

* We don't add the trait to the scheduling request, so the instance can land
  anywhere.
* The driver will **not** use the feature for live-migrate, regardless of what
  the compute's config says.

By default, when the operator creates an instance without any related metadata,
the scheduler will not care whether the host supports auto-converge or
post-copy.  If the configurations ``live_migration_permit_auto_converge`` or
``live_migration_permit_post_copy`` are True, the libvirt driver will prefer to
use auto-converge or post-copy. These can be used when the operator wants **all
instances** on a given compute node to use auto-converge/post-copy.  For
example:

* If an instance that has not requested related metadata is scheduled to a host
  that enabled ``live_migration_permit_auto_converge`` or
  ``live_migration_permit_post_copy``, then libvirt will try to use
  auto-converge or post-copy during live migration.

If the operator creates instance with
``compute:live_migration_auto_converge`=true/false`` or
``compute:live_migration_post_copy=true/false``,
these metadata will override the configurations:
``live_migration_permit_auto_converge`` or
``live_migration_permit_post_copy``.

When ``compute:live_migration_auto_converge`` and
``compute_live_migration_post_copy`` are both true or flavor extra specs
is in conflict with image properties, the 'create' API call will raise an
exception.

When using auto-converge during live migration, if the operator calls the force
complete API, libvirt will not be converted to use post-copy because it's not
required in flavor extra specs or image properties.

According to this spec [3]_, if post-copy is enabled during live migration, the
abort API call will be rejected by libvirt driver. Now we can reject the
request in the API by checking ``hw_live_migration_permit_reboot_risk``
properties.

Alternatives
------------
Another method is to use traits in flavor extra_specs/image properties. This
could work well when the operators need auto-converge/post-copy. But it can't
be used to disable auto-converge/post-copy.
Since the Rocky release, all libvirt hypervisor hosts support
auto-converge/post-copy, which means every libvirt hypervisor host would have
traits ``COMPUTE_MIGRATE_AUTO_CONVERGE`` and ``COMPUTE_MIGRATE_POST_COPY``.
If operators want to not use auto-converge or post-copy, they would use
forbidden traits: ``traits:COMPUTE_MIGRATE_AUTO_CONVERGE=forbidden`` or
``traits:COMPUTE_MIGRATE_POST_COPY=forbidden``. Which means **don't** schedule
my vm to the hosts who support auto-converge/post-copy, as the above says, this
means that all libvirt compute nodes will be ignored. The result will be that
the vm creation failed because the compute node can't be scheduled.

Data model impact
-----------------

Add the two image properties to the ImageMeta object:

* compute_live_migration_auto_converge
* compute_live_migration_post_copy

The ImageMeta is stored in table instance_system_metadata, no schema
modification is needed.

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

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

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Ya Wang

Work Items
----------

* Support for new placement traits.

* Libvirt driver changes to report traits to placement, the traits will be
  reported by the libvirt driver as part of ``update_provider_tree``. This will
  *not* be added to the generic compute capabilities dict inherited by all the
  virt drivers because these traits are libvirt-specific.

* Scheduler changes to translate metadata to traits.

* Recalculate ``_live_migration_flags`` before live migration start in
  the libvirt driver.

* Add functional tests and unit tests.


Dependencies
============

None


Testing
=======

Unit tests and functional tests will be included to test the new functionality.


Documentation Impact
====================

* The live migration document should be changed to introduce this new feature.

References
==========

.. [1] https://wiki.openstack.org/wiki/LibvirtDistroSupportMatrix
.. [2] https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainMigrateFlags
.. [3] https://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/auto-live-migration-completion.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
