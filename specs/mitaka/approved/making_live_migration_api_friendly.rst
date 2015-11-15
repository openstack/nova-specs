..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Making the live-migration API friendly
======================================

https://blueprints.launchpad.net/nova/+spec/making-live-migration-api-friendly

The current live-migration API is difficult to use, so we need to make the API
more user-friendly and external system friendly.

Problem description
===================

The current live-migration API requires the user to specify whether block
migration should be used with `block_migration` flag. Block migration requires
that the  source and destination hosts aren't on a piece of shared storage.
Live migration without block migration requires the source and destination
hosts are on the same shared storage.

There are two problems for this flag:

* For external systems and cloud operators, it is hard to know which value
  should be used for specific destination host. Before the user specifies the
  value of `block_migration` flag, the user needs to figure out whether the
  source and destination host on the same shared storage.
* When user passes the `host` flag with value None, the scheduler will choose a
  host for user. If the scheduler selects a destination host which is on the
  same shared storage with the source host, and user specifies
  `block_migration` as True, the request will fail. That means scheduler didn't
  know the topology of storage, so it can't select a reasonable host.

For the `host` flag, a value of None means the scheduler should choose a host.
For ease of use, the 'host' flag can be optional.

The `disk_over_commit` flag is libvirt driver specific. If the value is True,
libvirt virt driver will check the image's virtual size with disk usable size.
If the value is False, libvirt virt driver will check the image's actual size
with disk usable size. Nova API shouldn't expose any specific hypervisor
detail. This flag confuses user as well, as normally the user only wants to use
same policy of resource usage as scheduler already does.

Use Cases
---------

* API Users and external systems can use the live-migration API without
  having to manually determine the storage topology of the Nova deployment.
* API Users should be able to have the scheduler select the destination host.
* Users don't want to know whether disk overcommit is needed, Nova shoud just
  do the right thing.

Proposed change
===============

Make the `block_migration` flag optional, with a default value of None. When
the value is None, Nova will detect whether source and destination hosts on
shared storage. If they are on shared storage, the live-migration won't do
block migration. If they aren't on shared storage, the block migration will be
executed.

Make the `host` flag optional, and the default value is None. The behaviour
won't change.

Remove the `disk_over_commit` flag and remove the disk usage check from libvirt
virt driver.

Alternatives
------------

Ideally the Live-migration API will be improved continuously. For the flag
`block_migration`, there are two opinions on this:

* When `block_migration` flag is False, the scheduler will choose a host
  which is on the shared storage with original host. When the value is True,
  the scheduler will choose a host which isn't on the shared storage with
  original host. This need some work for Nova to tracking the shared storage
  to make scheduler choice right host.
* Remove `block_migration` flag totally, the API behaviour is always migrating
  instance in one storage pool, this is people's choice in most of cases.

Anyway the shared storage can be tracked when this BP is implemented:
https://blueprints.launchpad.net/nova/+spec/resource-providers
So that will be future work.

The logic for `disk_over_commit` does not match how the ResourceTracker does
resource counting. Ideally we should have the ResourceTracker consume disk
usage, that will be done by another bug fix or proposal.

Data model impact
-----------------

None

REST API impact
---------------


The block_migration and host flag will be optional, disk_over_commit flag will
be removed, the json-schema as below::

  boolean = {
    'type': ['boolean', 'string', 'null'],
    'enum': [True, 'True', 'TRUE', 'true', '1', 'ON', 'On', 'on',
             'YES', 'Yes', 'yes',
             False, 'False', 'FALSE', 'false', '0', 'OFF', 'Off', 'off',
             'NO', 'No', 'no'],
  }

  {
    'type': 'object',
    'properties': {
        'os-migrateLive': {
            'type': 'object',
            'properties': {
                'block_migration': boolean,
                'host': host,
            },
            'additionalProperties': False,
        },
    },
    'required': ['os-migrateLive'],
    'additionalProperties': False,
  }

This change will need a new microversion, and the old version API will keep the
same behaviour as before.

For upgrades, if the user specifies a host which is using an old version node
with new API version, the API will return `HTTP BadRequest 400` when
`block_migration` or `disk_over_commit` is None. If user didn't specify host
and the old version node selected by host, the scheduler will retry to find
another host until there is new compute node found or reach the max number of
reties.

Currently the response body is empty. But user needs to know whether nova
decided to do block migration. The response body was proposed::

  {
    'type': 'object',
    'properties': {
      'block_migration': parameter_types.boolean,
      'host': host
    }
    'required': ['block_migration', 'host'],
    'additionalProperties': False
  }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

User needn't figure out whether the destination host is on the same shared
storage or not as the source host anymore before invoking the live-migration
API. But this may cause a block migration which will incur more load on the
live-migration network, which may be unexpected to the user. If user clearly
didn't want to block-migration, user may set specify block_migration to False
explicitly. This will be improved in the future.

Performance Impact
------------------

None

Other deployer impact
---------------------

The new REST API version won't work for old compute nodes when doing a rolling
upgrade. This is because `disk_over_commit` was removed, there isn't valid
value provided from API anymore. User only can use old version live-migration
API with old compute node.

Developer impact
----------------

None

Implementation
==============

The detection of block_migration
--------------------------------

For the virt driver interface, there are two interfaces to check if the
destination and source hosts satisfy the migration conditions. They are
`check_can_live_migrate_destination` and `check_can_live_migrate_source`. After
the check, the virt driver will return `migrate_data` to nova conductor.

We proposal that when is made with `block_migration` set to None, those two
driver interfaces will calculate out the new value for `block_migration` based
on the shared storage checksimplemented in the virt driver. The new value of
`block_migration` will be returned in the `migrate_data`.

Currently only three virt drivers implement live-migration. They are
libvirt driver, xenapi driver, and hyperv driver:

For libvirt driver, it already implements the detection of shared storage. The
result of the checks are in the dict `dest_check_data`, in values
`is_shared_block_storage` and `is_shared_instance_path`. So when the
`block_migration` is None, the driver will set `block_migration` to True if
`is_shared_block_storage` or `is_shared_instance_path` is True. Otherwise the
driver will set `block_migration` to False. Finally the new value of
`block_migration` will be returned in `migrate_data`.

For xenapi driver, the shared storage check is based on aggregate. It is
required that the destination host must be in the same aggregate /
hypervisor_pool as the source host. So the `block_migration` will be True when
the host in that aggregate. Otherwise the `block_migration` is False. Also pass
the new value back with `migrate_data`.

For hyperv driver, although it supports the live-migration, but there isn't any
code implementing the `block_migration` flag. So we won't implement it until
hyperv support that flag.

Remove the check of disk_over_commit
------------------------------------

The `disk_over_commit` flag still needs to work with older microversions. For
this proposal, we add a None value when the request with a newer microversion.
In the libvirt driver, if the value of `disk_over_commit` is None, the driver
won't doing any disk usage check, otherwise the check will do the same thing as
before.

The upgrade concern
-------------------

This propose will add  new value of `None` for `block_migration` and
`disk_over_commit`. When openstack cluster is in the progress of rolling
upgrade, the old version compute nodes don't know this new value. So
there is a check added in the Compute RPC API. If client can't send the new
version Compute RPC API, a fault will be returned.

Assignee(s)
-----------

Primary assignee:
  Alex Xu <hejie.xu@intel.com>

Work Items
----------

* Implement the value detection of `block_migration` in the libvirt and xenapi
  driver.
* Implement skip the check of disk usage when the `disk_over_commit` value is
  None
* Make `block_migration`, `host` flags optional, and remove `disk_over_commit`
  flag in the API.

Dependencies
============

None

Testing
=======

Unit tests and functional tests in Nova

Documentation Impact
====================

Doc the API change in the API Reference:
http://developer.openstack.org/api-ref-compute-v2.1.html

References
==========

None

History
=======

Mitaka: Introduced
