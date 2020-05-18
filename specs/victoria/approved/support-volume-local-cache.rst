..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Support volume local cache
==========================

https://blueprints.launchpad.net/nova/+spec/support-volume-local-cache

This blueprint proposes to add support of volume local cache in nova. Cache
software such as open-cas [4]_ can use fast NVME SSD or persistent memory to
cache for the slow remote volume.

Problem description
===================

Currently there are different types of fast NVME SSDs, such as Intel Optane
SSD, with latency as low as 10 us. What's more, persistent memory which aim to
be SSD size but DRAM speed gets popupar now. Typical latency of persistent
memory would be as low as hundreds of nanoseconds. While typical latency of
remote volume for a VM can be at the millisecond level (iscsi / rbd). So these
fast SSDs or persistent memory can be mounted locally on compute nodes and used
as a cache for remote volumes.

In order to do the cache, there're some cache software, such as open-cas.
open-cas is very easy to use, you just need to specify a block device as the
cache device, and then can use this device to cache for other block devices.
This is transparent to upper layer and lower layer. Regarding upper layer,
guest don't know it is using an emulated block device. Regarding lower layer,
backend volume don't know it is cached, and the data in backend volume will not
have extra change because of cache. That means even if the cache is lost for
some reason, the backend volume can be mounted to other places and available
immediately. This spec is trying to add volume local cache using such cache
software.

Like all the local cache solution, multi-attach cannot work. This is because
cache on node1 don't know the changes made to backend volume by node2.

This feature requires the cache mode "Write-Through", which makes sure the
cache is fully synced with backend volume all the time. Given this, it is
transparent to live migration. "Write-Through" is also the default cache mode
for open-cas.

This feature can only cache for backend volumes that would be mounted on host
OS first as block device. So volumes (LibvirtNetVolumeDriver is used) mounted
by QEMU, such as rbd and sheepdog, cannot be cached. Details can be found in
list libvirt_volume_drivers in [5]_.

In some high performance environments, RDMA may be chosen. RDMA effectively
shorten the latency gap between local volume and remote volume. In experimental
environment, without network switch, without read/write io to real volume, the
point to point RDMA network link latency would be even 3 us in best case. This
is the pure network link latency, and this also don't mean it is faster than
local PCIe, because RDMA NIC card itself in host and target machines also are
PCIe devices. For RDMA scenario, persistent memory is recommended to be
selected as cache device, otherwise may no performance gain.

Use Cases
---------

User wants to use fast NVME SSD to cache for remote slow volumes. This is
extremely useful for clouds where operators want to boost disk io performance
for specific volumes.

Proposed change
===============

All volumes cached by the same cache instance share same cache mode. The
operator can change cache mode dynamically, using cache software management
tool. os-brick just accepts the cache name and cache IDs from Nova. Cache name
identifies which cache software to use, currently it only supports 'opencas'.
It is allowed that more than one cache instance in one compute node. Cache IDs
identifies cache instances that can be used. Cache mode is transparent to
os-brick.

A compute capability is mapped to the trait (e.g. COMPUTE_SUPPORT_VOLUME_CACHE)
and the libvirt driver can set this capability to true if there is cache
instance id is configured in the nove conf. If want the volume be cached,
firstly the volume should belongs to a volume type with "cacheable" property.
Then select the flavor with extra spec containing this trait, so the guest
would be landed at the host machine with cache capability. If don't want the
volume be cached, just select a flavor without this trait.

If there's failure happened during setting up caching, e.g. cache device
broken, then re-schedule the request.

Final architecture would be something like::

                        Compute Node

 +---------------------------------------------------------+
 |                                                         |
 |                        +-----+    +-----+    +-----+    |
 |                        | VM1 |    | VM2 |    | VMn |    |
 |                        +--+--+    +--+--+    +-----+    |
 |                           |          |                  |
 +---------------------------------------------------------+
 |                           |          |                  |
 | +---------+         +-----+----------+-------------+    |
 | |  Nova   |         |          QEMU Virtio         |    |
 | +-+-------+         +-----+----------+----------+--+    |
 |   |                       |          |          |       |
 |   | attach/detach         |          |          |       |
 |   |                 +-----+----------+------+   |       |
 | +-+-------+         | /dev/cas1  /dev/cas2  |   |       |
 | | osbrick +---------+                       |   |       |
 | +---------+ casadm  |        open cas       |   |       |
 |                     +-+---+----------+------+   |       |
 |                       |   |          |          |       |
 |                       |   |          |          |       |         Storage
 |              +--------+   |          |    +-----+----+  | rbd   +---------+
 |              |            |          |    | /dev/sdd +----------+  Vol1   |
 |              |            |          |    +----------+  |       +---------+
 |        +-----+-----+      |          |                  |       |  Vol2   |
 |        | Fast SSD  |      |    +-----+----+   iscsi/fc/...      +---------+
 |        +-----------+      |    | /dev/sdc +-------------+-------+  Vol3   |
 |                           |    +----------+             |       +---------+
 |                           |                             |       |  Vol4   |
 |                     +-----+----+    iscsi/fc/...        |       +---------+
 |                     | /dev/sdb +--------------------------------+  Vol5   |
 |                     +----------+                        |       +---------+
 |                                                         |       |  .....  |
 +---------------------------------------------------------+       +---------+


Changes would include:

* Cache the volume during connecting volume

  In function _connect_volume():

  - Check if the volume should be cached or not. Cinder would set the cacheable
    property for the volume if caching is allowed. If cacheable is set and
    volume_local_cache_driver in CONF is not empty, then do caching. Otherwise
    just ignore caching.

  - attach_cache before attach_encryptor, cache lays under encryptor. It is to
    keep encrypted volume secure. No decrypted data would be written to cache
    device.

  - Call os-brick to cache the volume [2]_. os-brick will call cache software
    to setup the cache. Then replace the path of original volume with the
    emulated volume

  - Nova goes ahead to _connect_volume with the newly emulated volume path

  - If any failure happens during setting up caching, just ignore the failure
    and continue the rest code of _connect_volume().

* Release cache during disconnecting volume

  In function _disconnect_volume():

  - Call os-brick to release the cache for the volume. os-brick will retrieve
    the path of original volume from emulated volume, and then replace the path
    in connection_info with the original volume path

  - Nova goes ahead to _disconnect_volume with the original volume path

* Add switch in nova-cpu.conf to enable/disable local cache

  Suggested switch names:

  - volume_local_cache_driver: Specifies which cache software to use. Currently
    only support 'opencas'. If it is empty, then local cache is disabled.

  - volume_local_cache_instance_ids: Specifies cache instances that can be
    used. Typically opencas has only one cache instance in a single server, but
    it has the ability to have more than one cache instances which bind to
    different cache device. Nova needs to pass instance IDs to os-brick and let
    os-brick to find the best one, e.g. biggest free size, less volumes cached,
    etc. All these information can be get from instance ID via cache admin
    tool, like casadm.

  Suggested section: [compute]. Configuration would be like:
  [compute]
  volume_local_cache_driver = 'opencas'
  volume_local_cache_instance_ids = 1,15,222

  Instance IDs are separated by commas.

Nova calls os-brick to set cache for the volume only when it has the property
of "cacheable" and the flavor requested such caching. Let cinder to determine
and set the property, just like the way did for volume encryption. If the
volume contains property "multiattach", cinder would not set "cacheable" for
it. Code work flow would be like::

              Nova                                        osbrick


                                               +
          +                                    |
          |                                    |
          v                                    |
    attach_volume                              |
          +                                    |
          |                                    |
          +                                    |
        attach_cache                           |
              +                                |
              |                                |
              +                                |
  +-------+ volume_with_cache_property?        |
  |               +                            |
  | No            | Yes                        |
  |               +                            |
  |     +--+Host_with_cache_capability?        |
  |     |         +                            |
  |     | No      | Yes                        |
  |     |         |                            |
  |     |         +-----------------------------> attach_volume
  |     |                                      |        +
  |     |                                      |        |
  |     |                                      |        +
  |     |                                      |      set_cache_via_casadm
  |     |                                      |        +
  |     |                                      |        |
  |     |                                      |        +
  |     |                                      |      return emulated_dev_path
  |     |                                      |        +
  |     |                                      |        |
  |     |         +-------------------------------------+
  |     |         |                            |
  |     |         v                            |
  |     |   replace_device_path                |
  |     |         +                            |
  |     |         |                            |
  v     v         v                            |
                                               |
 attach_encryptor and                          |
 rest of attach_volume                         +


* Volume local cache lays upon encryptor would have better performance, but
  expose decrypted data in cache device. So based on security consideration,
  cache should lay under encryptor in Nova implementation.

Code implementation can be found in [1]_ [2]_ [3]_

Alternatives
------------

* Assign local SSD to a specific VM. VM can then use bcache internally against
  the ephemeral disk to cache their volume if they want.

  The drawbacks may include:

  - Can only accelerate one VM. The fast SSD capability cannot be shared by
    other VMs. Unlike RAM, SSD normally is in TB level and large enough to
    cache for all the VMs in one node.

  - The owner of the VM should setup cache explicitly. But not all the VM owner
    want to do this, and not all the VM owner has the knowledge to do this. But
    they for sure want the volume performance is better by default.

* Create a dedicated cache cluster. Mount all the cache (NVME SSD) in cache
  cluster as a big cache pool. Then allocate a certain ammount of cache to a
  specific volume. The allocated cache can be mounted on compute node through
  NVMEof protocol. Then still use cache software to do the same cache.

  But this would be the compete between local PCIe and remote network. The
  disadvantage if doing like these ways is: the network of the storage server
  would be bottleneck.

  - Latency) Storage cluster typically provide volume through iscsi/fc
    protocol, or through librbd if ceph is used. The latency would be
    millisecond level. Even NVME over TCP, the latency would be hundreds of
    microsecond, depends on the network topology. As a contrast, the latency of
    NVME SSD would be around 10 us, take Intel Optane SSD p4800x as example.

* Cache can be added in backend storage side, e.g. in ceph. Storage server
  normally has its own cache mechanism, e.g. using memory as cache, or using
  NVME SSD as cache.

  Similiar with above solution, latency is the disadvantage.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

* Cache software will remove the cached volume data from cache device when
  volume is detached. But normally it would not erase the related sectors in
  cache device. So in theory the volume data is still in cache device before it
  is overwritten. Volume with encryption doesn't have this security impact if
  encryption laying upon volume local cache.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

* Latency of VM volume will be decreased

Other deployer impact
---------------------

* Option volume_local_cache_driver and volume_local_cache_instance_ids should
  be set in nova-cpu.conf to enable this feature. Default value of
  volume_local_cache_driver would be empty string which means local cache is
  disabled.

Developer impact
----------------

This is only for libvirt, other drivers like VMWare, hyperv will not be
changed. This is because open-cas can only support Linux, and libvirt is the
most used one. Meanwhile this spec/implementation would only be tested with
libvirt.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Liang Fang <liang.a.fang@intel.com>

Feature Liaison
---------------

Feature liaison:
  gibi

Work Items
----------

* Add COMPUTE_SUPPORT_VOLUME_CACHE trait to os-traits

* Add a new compute capability that maps to this trait

* Enable this capability in the libvirt driver if a caches is configured

* Cache the volume during connecting volume

* Release cache during disconnecting volume

* Add switch to enable / disable this feature

* Unit test to be added

Dependencies
============

* os-brick patch: [2]_
* cinder patch: [3]_

Testing
=======

* New unit test should be added

* One of tempest jobs should be changed to enable this feature, with open-cas,
  on a vanilla worker image

  - This can use open-cas with a local file as NVME device.

  - Check if the emulated volume is created for VM or not.

  - Check if the emulated volume is released or not when deleting VM

* One of tempest jobs should be changed to enable this feature, with open-cas,
  on a vanilla worker image

Documentation Impact
====================

* Document need to be changed to describe this feature and include the new
  options - volume_local_cache_driver, volume_local_cache_instance_ids

References
==========

.. [1] https://review.opendev.org/#/c/663542/
.. [2] https://review.opendev.org/#/c/663549/
.. [3] https://review.opendev.org/#/c/700799/
.. [4] https://open-cas.github.io/
.. [5] https://github.com/openstack/nova/blob/master/nova/virt/libvirt/driver.py

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
   * - Victoria
     - Re-proposed
