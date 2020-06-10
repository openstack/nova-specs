..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
support virtual persistent memory
=================================

https://blueprints.launchpad.net/nova/+spec/virtual-persistent-memory

Virtual persistent memory is now supported in both QEMU and
libvirt. This spec seeks to enable this support in OpenStack Nova.

Problem description
===================

For many years computer applications organized their data between
two tiers: memory and storage. Emerging `persistent memory`_
technologies introduce a third tier. Persistent memory
(or ``pmem`` for short) is accessed like volatile memory, using processor
load and store instructions, but it retains its contents across power
loss like storage.

Virtualization layer has already supported virtual persistent memory
which means virtual machines now can have physical persistent memory
as the backend of virtual persistent memory. As far as Nova is concerned,
several problems need to be addressed:

* How is the physical persistent memory managed and presented as
  virtual persistent memory
* The discovery and resource tracking of persistent memory
* How does the user specify the desired amount of virtual persistent
  memory
* What is the life cycle of virtual persistent memory

Use Cases
---------
Provide applications with the ability to load large contiguous segments
of memory that retain their data across power cycles.

Besides data persistence, persistent memory is less expensive than DRAM
and comes with much larger capacities. This is an appealing feature for
scenarios that request huge amounts of memory such as high performance
computing (HPC).

There has been some exploration by applications which heavily use memory
devices such as in memory databases. To name a few: redis_, rocksdb_,
oracle_, `SAP HANA`_ and Aerospike_.

.. note::
    This spec only intends to enable virtual persistent memory
    for the libvirt KVM driver.

Proposed change
===============

Background
----------
The most efficient way for an applications to use persistent memory is
to memory map (mmap()) a portion of persistent memory into the address
space of the application. Once the mapping is done, the application
accesses the persistent memory ``directly`` (also called ``direct access``),
meaning without going through kernel or whatever other software in the
middle. Persistent memory has two types of hardware interfaces --
"PMEM" and "BLK". Since "BLK" adopts an aperture model to access
persistent memory, it does not support ``direct access``.
For the sake of efficiency, this spec only proposes to use persistent
memory accessed by "PMEM" interface as the backend for QEMU virtualized
persistent memory.

Persistent memory must be partitioned into `pmem namespaces`_ for
applications to use. There are several modes of pmem namespaces for
different use scenarios. Mode ``devdax`` and mode ``fsdax`` both
support ``direct access``. Mode ``devdax`` gives out a character
device for a namespace, thus applications can mmap() the entire
namespace into their address spaces. Whereas mode ``fsdax`` gives
out a block device. It is recommended to use mode ``devdax`` to
assign persistent memory to virtual machines.
Please refer to `virtual NVDIMM backends`_ and
`NVDIMM Linux kernel document`_ for details.

.. important ::
    So this spec only proposes to use persistent memory namespaces in
    ``devdax`` mode as QEMU virtual persistent memory backends.

The ``devdax`` persistent memory namespaces require contiguous physical
space and are not managed in pages as ordinary system memory.
This introduces a fragmentation issue with regard to multiple namespaces
are created and used by multiple applications. As shown in below diagram,
four applications are using four namespaces each of size 100GB::

   +-----+   +-----+   +-----+    +-----+
   |app1 |   |app2 |   |app3 |    |app4 |
   +--+--+   +--+--+   +--+--+    +--+--+
      |         |         |          |
      |         |         |          |
 +----v----+----v----+----v----+-----v---+
 |         |         |         |         |
 |  100GB  |  100GB  |  100GB  |  100GB  |
 |         |         |         |         |
 +---------+---------+---------+---------+

After the termination of app2 and app4, it turns out to be::

    +-----+             +-----+
    |app1 |             |app3 |
    +--+--+             +--+--+
       |                   |
       |                   |
  +----v----+---------+----v----+---------+
  |         |         |         |         |
  |  100GB  |  100GB  |  100GB  |  100GB  |
  |         |         |         |         |
  +---------+---------+---------+---------+

The total size of free space is 200GB. However a ``devdax`` mode
namespace of 200GB size can not be created.

Persistent memory namespace management and resource tracking
------------------------------------------------------------
Due to the aforementioned fragmentation issue, persistent memory can not
be managed in the similar way as system memory. In other words,
dynamically creating and deleting persistent memory namespaces upon
VM creation and deletion will result in fragmentation and also a challenge
to track persistent memory resource.
The proposed approach is to use pre-created fix sized namespaces.
In other words, the cloud admin creates persistent memory of the desired
sizes before Nova is deployed on a certain host. And the cloud admin puts
the namespace information into nova config file (details below).
Nova compute agent discovers the namespaces by parsing the config file
to determine what namespaces it can allocate to a guest. The discovered
persistent memory namespaces will be reported to the placement service
as inventories of a custom resource class associated with the ROOT
resource provider.

Custom Resource Classes are used to represent persistent memory namespace
resource. The naming convention of the custom resource classes being used is::

 CUSTOM_PMEM_NAMESPACE_$LABEL

``$LABEL`` is variable part of the resource class name defined by the admin
to be associated with a certain number of persistent memory namespaces.
It normally is the size of namespaces in any desired units.
It can also be a string describing the capacities -- such as 'SMALL',
'MEDIUM' or 'LARGE'. Admin shall properly define the value of '$LABEL'
for each namespace.

The association between ``$LABEL`` and persistent memory namespaces
is defined by a new configuration option 'CONF.libvirt.pmem_namespaces'.
This config option is of string type in below format::

    "$LABEL:$NSNAME[|$NSNAME][,$LABEL:$NSNAME[|$NSNAME]]"

``$NSNAME`` is the name of the persistent memory namespace that falls
into the resource class named ``CUSTOM_PMEM_NAMESPACE_$LABEL``.
A name can be given to a persitent memory namespace upon creation by
the "-n/--name" option to the `ndctl`_ command.

To give an example, on a certain host, there might be a below configuration::

    "128G:ns0|ns1|ns2|ns3,262144MB:ns4|ns5,MEDIUM:ns6|ns7"

The interpretation of the above configuration is that this host has 4
persistent memory namespaces (ns0, ns1, ns2, ns3) of resource class
``CUSTOM_PMEM_NAMESPACE_128G``, 2 namespaces (ns4, ns5) of resource class
``CUSTOM_PMEM_NAMESPACE_262144MB``, and 2 namespaces (ns6, ns7) of resource
class ``CUSTOM_PMEM_NAMESPACE_MEDIUM``.

The 'total' value of the inventory is the *number* of the
persistent memory namespaces belong to this resource class.

The 'max_unit' is set to the same value as 'total' since it is possible
to attach all of the persistent memory namespaces in a certain resource
class to one instance.

The values of 'min_unit' and 'step_size' are 1.

The value of 'allocation_ratio' is 1.0.

In case of the above example, the response to a `GET` request to this
resource provider inventories is::

 "inventories": {
         ...
         "CUSTOM_PMEM_NAMESPACE_128GB": {
             "allocation_ratio": 1.0,
             "max_unit": 4,
             "min_unit": 1,
             "reserved": 0,
             "step_size":1,
             "total": 4
         },
         "CUSTOM_PMEM_NAMESPACE_262144MB": {
             "allocation_ratio": 1.0,
             "max_unit": 2,
             "min_unit": 1,
             "reserved": 0,
             "step_size": 1,
             "total": 2
         },
         "CUSTOM_PMEM_NAMESPACE_MEDIUM": {
             "allocation_ratio": 1.0,
             "max_unit": 2,
             "min_unit": 1,
             "reserved": 0,
             "step_size": 1,
             "total":2
         },
         ...
 }

Please note, this is just an example to show different ways to configure
persistent memory namespaces and how they are tracked. There are certainly
some flexibility in the naming of the resource class name. It is up to
the admin to configure the namespaces properly.

.. note::
    Resource class names are opaque. For example, a request
    for CUSTOM_PMEM_NAMESPACE_128GB cannot be fulfilled by a
    CUSTOM_PMEM_NAMESPACE_131072MB resource even though they are
    (presumably) the same size.

Different units do not convert freely from one to another while embeded
in custom resource class names. Meaning a request for a 128GB persistent
memory namespace can be fulfilled by a CUSTOM_PMEM_NAMESPACE_128GB
resource, but can not be fulfilled by a CUSTOM_PMEM_NAMESPACE_131072MB
resource even though they are of the same quantity.

Persistent memory is by nature NUMA sensitive. However for the initial
iteration, the resource inventories are put directly under ROOT resource
provider of the compute host. Persistent memory NUMA affinity will be
adddressed by a seperate follow-on spec.

A change in the configuration will stop the nova compute agent from
(re)starting if that change removes any namespaces in use by guests
from the configuration.

Virtual persistent memory specification
---------------------------------------
Virtual persistent memory information is added to guest hardware flavor
extra specs in the form of::

 hw:pmem=$LABEL[,$LABEL]

``$LABEL`` is the variable part of a resource class name as defined
in the `Persistent memory namespace management and resource tracking`_
section. Each appearence of a '$LABEL' means a requirement to one
persistent memory namespace of ``CUSTOM_PMEM_NAMESPACE_$LABEL``
resource class. So there can be multiple appearences of the same
$LABEL in one specification. To give an example::

    hw:pmem=128GB,128GB

It means a resource requirement of two 128GB persisent memory
namespaces.

Libvirt domain specification requires each virtual persistent memory
to be associated with one guest NUMA node. If guest NUMA topology
is specified in the flavor, the guest virtual persistent memory
devices are put under guest NUMA node 0. If guest NUMA topology is not
specified in the flavor, a guest NUMA node 0 is constructed implicitly
and all guest virutal persistent memory devices are put under it.
Please note, under the second circumstance (implicitly constructing
a guest NUMA node 0), the construction of guest NUMA node 0 happens
at the Nova API, which means the NUMA topology logic in the scheduler
is applied. And from the perspective of any other parts of Nova, this
guest is a NUMA guest.

Examples::

 One NUMA node, one 512GB virtual persistent memory:
     hw:numa_nodes=1
     hw:pmem=512GB

 One NUMA node, two 512GB virtual persistent memory:
     hw:numa_nodes=1
     hw:pmem=512GB,512GB

 Two NUMA nodes, two 512GB virtual persistent memory:
     hw:numa_nodes=2
     hw:pmem=512GB,512GB

     Both of the two virtual persistent memory devices
     are put under NUMA node 0.

 No NUMA node, two 512GB virtual persistent memory:
     hw:pmem = 512GB,512GB

     A guest NUMA node 0 is constructed implicitly.
     Both virtual persistent memory devices are put under it.

.. important ::
    Qemu does not support backing one virtual persistent memory device
    by multiple physical persistent memory namespaces, no matter whether
    they are contiguous or not. So any virtual persistent memory device
    requested by guests is backed by one physical persistent memory
    namespace of the exact same resource class.

The extra specs are translated to placement API requests accordingly.

Virtual persistent memory disposal
----------------------------------
Due to the persistent nature of host PMEM namespaces, the content
of virtual persistent memory in guests shall be zeroed out immediately
once the virtual persisent memory is no longer associated with any VM
instance (cases like VM deletion, cold/live migration, shelve, evacuate
and etc.). Otherwise there will be security concerns.
Since persistent memory devices are typically of large size, this may
introduce a performance penalty to guest deletion or any other actions
involving erasing PMEM namespaces.
The standard I/O APIs (read/write) cannot be used with DAX (direct access)
devices. The nova compute libvirt driver uses `daxio`_ utility (wrapped
by privsep library functions) for this purpose.

VM rebuild
----------
The persisent memory namespaces are zeroed out during VM rebuild to
get to the initial state of the VM.

VM resize
---------
Resizing to new flavor with arbitrary virtual persistent memory devices
is allowed. The content of the original virtual persistent memory will not
be copied to the new virtual persistent memory (if there is).

Live migration
--------------
Live migration with virtual persistent memory is supported by QEMU.
Qemu treats virtual persistent memory as volatile memory in case of
live migration. It just takes longer time due to the typical large
capacity of virtual persistent memory.

Virtual persistent memory hotplug
---------------------------------
This spec does not address the hot plugging of virtual persistent memory.

VM snapshot
-----------
The current VM snapshots do not include memory images. For the current
phase the virtual persistent images are not included in the VM snapshots.
In future, virtual persistent images could be stored in Glance as a separate
image format. And flavor extra specs can be used to specify whether
to save virtual persistent memory image during VM snapshot.

VM shelve/unshelve
------------------
Shelving a VM is to upload the VM snapshot to Glance service. Since the
virtual persistent memory image is not included in the VM snapshot,
VM shelve/unshelve does not automatically save/restore the virtual
persistent memory for the current iteration.
As snapshot, saving/restoring virtual persistent memory images could be
supported after the persistent memory images can be stored in Glance.
The persistent memory namespaces belong to a shelved VM are zeored out
after VM being shelve-offloaded.

Alternatives
------------
Persisent memory namespaces can be created/destroyed on the fly as VM
creation/deletion. This ways is more flexible than the fix sized
approach, however it will result in fragmentation as detailed in the
`Background`_ section.

Another model of fix sized appoach other than the proposed one could
be evenly partitioning the entire persistent memory space into namespaces
of the same size and setting the ``step_size`` of the persistent
memory resource provider to the size of each namespace. However this
model assumes a larger namespace can be assembled from multiple smaller
namespaces (a 256GB persistent memory requirement may land on 2x128GB
namespaces) which is not the case.

Persistent memory demonstrates certain similarity with block devices
in its non-volatile nature and life cycle management. It is possible
to stick it into block device mapping (BDM) interface. However, NUMA
affinity support is in the future of persistent memory and BDM is not
the ideal interface to decribe NUMA.

Data model impact
-----------------
A new LibvirtVPMEMDevice object is introduced to track the virtual PMEM
information of an instance, it stands for a virtual persistent memory
device backed by a physical persistent memory namespace:

.. code-block:: python

 class LibvirtVPMEMDevice(ResourceMetadata):
     # Version 1.0: Initial version
     VERSION = "1.0"

     fields = {
        'label': fields.StringField(),
        'name': fields.StringField(),
        'size': fields.IntegerField(),
        'devpath': fields.StringField(),
        'align': fields.IntegerField(),
     }


The 'resources' deferred-load column in class InstanceExtra stores a serialized
ResourceList object for a given instance, each Resource object contain a
specific resource information, it has a object field 'metadata', which can be
subclass of ResourceMetadata object. Since LibvirtVPMEMDevice is introduced,
virtual persistent memory information can be stored in 'resources' field of
objects.Instance and persistent in database table InstanceExtra.


REST API impact
---------------
Flavor extra specs already accept arbitrary data.
No new micro version introduced.

Security impact
---------------
Host persistent memory namespaces needs to be erased (zeroed) to be reused.

Notifications impact
--------------------
None.

Other end user impact
---------------------
End users choose flavors with desired virtual persistent memory sizes.

Performance Impact
------------------
PMEM namespaces tend to be large. Zeroing out a persistent memory
namespace requires a considerable amount of time. This may introduce
a negative performance impact when deleting a guest with large
virtual persistent memories.

Other deployer impact
---------------------
The deployer needs to create persistent memory namespaces of the desired
sizes before nova is deployed on a certain host.

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
  xuhj

Other contributors:
  luyaozhong
  rui-zang

Work Items
----------
* Object: add DB model and Nova object.
* Compute: virtual persistent memory life cycle management.
* Scheduler: translate virtual persistent memory request to
             placement requests.
* API: parse virtual persistent memory flavor extra specs.

Dependencies
============
* Kernel version >= 4.2
* QEMU version >= 2.9.0
* Libvirt version >= 5.0.0
* ndctl version >= 4.7
* daxio version >= 1.6


Testing
=======
Unit tests.
Third party CI is required for testing on real hardware.
Persistent memory nested virtualization works for QEMU/KVM.
For the third party CI, tempest tests are executed in a VM with
virtual persisent memory backed by physical persistent memory.

Documentation Impact
====================

The cloud administrator docs need to describe how to create
and configure persistent memory namespaces. Add a persitent
memory section into the Nova "advanced configuration" document.

The end user needs to be make aware of this feature. Add the
flavor extra spec details into the Nova flavors document.

References
==========

.. _`persistent memory`: http://pmem.io/
.. _redis: https://redislabs.com/blog/persistent-memory-and-redis-enterprise/
.. _rocksdb:  http://istc-bigdata.org/index.php/nvmrocks-rocksdb-on-non-volatile-memory-systems/
.. _oracle: https://blogs.vmware.com/apps/2018/09/accelerating-oracle-performance-using-vsphere-persistent-memory-pmem.html
.. _`SAP HANA`: https://blogs.sap.com/2018/12/03/sap-hana-persistent-memory/
.. _Aerospike: https://www.aerospike.com/resources/videos/aerospike-intel-persistent-memory-2/
.. _`pmem namespaces`: http://pmem.io/ndctl/ndctl-create-namespace.html
.. _`virtual NVDIMM backends`: https://github.com/qemu/qemu/blob/19b599f7664b2ebfd0f405fb79c14dd241557452/docs/nvdimm.txt#L145
.. _`NVDIMM Linux kernel document`: https://www.kernel.org/doc/Documentation/nvdimm/nvdimm.txt
.. _ndctl: http://pmem.io/ndctl/
.. _daxio: http://pmem.io/pmdk/daxio/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced

