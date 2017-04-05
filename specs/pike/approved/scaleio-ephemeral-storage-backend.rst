..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Dell EMC ScaleIO as ephemeral storage backend
=============================================

https://blueprints.launchpad.net/nova/+spec/scaleio-ephemeral-storage-backend

Add support for ScaleIO as an ephemeral storage backend.

Problem description
===================

Nova does not support Dell EMC ScaleIO - another type of software-defined
storage [1]_ - as an ephemeral storage backend. ScaleIO is already supported
by Cinder (and os-brick) for volume hosting. It is reasonable (and asked by
customers) to let Nova use ScaleIO for ephemeral disks.

The required set of supported features should be the same as the one
implemented for Ceph, including live migration, except features related to
optimized interaction with Glance, like clone or direct snapshot, because
Glance does not support ScaleIO yet. The target virtual driver should be
libvirt.

Main ScaleIO traits which have to be considered in a special way during
development are:

* ScaleIO devices must be explicitly connected to a compute host before usage,
  and disconnected after that.

* ScaleIO can provide volumes which sizes are multiples of 8 Gb only.

Use Cases
---------

* A cloud operator selects ScaleIO as the ephemeral backend for certain
  compute nodes. He/she ensures that no instance is running on the nodes.
  He/she ensures that SDC (ScaleIO Data Client) is properly installed on the
  nodes, and makes appropriate changes to nova-compute configuration files to
  setup them to use ScaleIO cluster. After restart nova-compute services on
  the nodes new instances will use ScaleIO for all ephemeral disks.

There is no other use case specific for ScaleIO in addition to existing ones to
manage instances by end user and/or cloud operator. Most valuable existing use
cases are: create/delete, live migrate, resize/revert resize, create snapshot,
host evacuation.

Proposed change
===============

* A new images type, a new image backend class, and a new image model class
  will be introduced and will be used throughout all *nova.virt.libvirt*
  package as it is done for rbd and lvm image types.

* Required operations to connect/disconnect instance's disks will be called in
  several appropriate places of *nova.virt.libvirt.driver*. These calls will
  be wrapped by *if* clause to perform them for the new backend explicitly,
  as it is done for rbd and other backends.

* ScaleIO image backend will fail to create disks with sizes differ from
  multiples of 8 Gb. The only exception is rescue disk, which is created with
  no size specified. In this case the backend will approximate the rescue image
  size up to 8 Gb multiple.

* Config drive will not be hosted on ScaleIO, but will be placed in instance
  local directory, as it happens by default. With iso9660 format this will not
  require much space (vfat format is supported by Nova for legacy only).

Alternatives
------------

Instead of to implement the separate ephemeral storage backend for ScaleIO,
it is possible to develop Cinder ephemeral storage backend, which obviously
may serve any kind of physical storage supported by Cinder
(including ScaleIO). Although the previous attempt [2]_ to get such backend
was stopped, recently this idea was discussed in the community again. However
there is even no new spec for this task at the moment. Also the
implementation seems to be much more complex, probably needing additional
refactoring, because the backend is intended particularly to replace Ceph
backend, which implementation (explicit and implicit) is very distributed
throughout whole libvirt driver. But Ceph backend is used widely, so it is
important for the task to be completed to support in Cinder backend each
feature of Ceph backend. Because that it looks that Cinder backend cannot be
implemented pretty soon, but requires 2-3 release cycles.
On the other hand we have ScaleIO backend which is already implemented for
previous OpenStack releases (since Juno), and also available for various
deployment tools [3]_.
Another question in this theme is if ScaleIO backend brings much complexity
to a seamless transition system from volume based ephemeral backends to Cinder
backend. Since there are more than one such backends (LVM, Ceph), and Cinder
is able to acquire unmanaged volumes, the transition system probably will have
much common code with small backend-related parts. So it will not be a big
extra work to add support for ScaleIO there as well.

Instead of failing to run instances on flavors with wrong disk sizes it is
possible:

#. Approximate disk size to the closest multiple of 8 Gb. Write a
   recommendation for cloud operators into Nova documentation to use multiples
   of 8 Gb for disk sizes.

   Instances will get disks bigger than it is requested. This makes usage of
   statistics gathered by Nova, Ceilometer, etc. nonsense. Also snapshots size
   will be bigger than it is expected.

#. The same as previous but also fix instance properties (like root_gb).

   Nova is not designed to have flavor and instance properties different
   at the moment.

#. Create a partition with requested size on ScaleIO volume with
   approximated size and pass the partition to libvirt as the device.

   This solution can work with thin provisioning type only. Additional
   investigations are required to proof that this idea can work, including
   resize feature.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

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

ScaleIO cluster must be installed and configured. A protection domain and a
storage pool to store ephemeral disks must be created in the cluster. ScaleIO
SDC component must be installed on affected compute nodes. These SDCs must be
registered with the cluster.

Nova's compute config file must contain these options to let ScaleIO image
backend work::

  [libvirt]
  images_type = sio

  [scaleio]
  rest_server_ip = <ScaleIO Gateway IP>
  rest_server_username = <ScaleIO Gateway user>
  rest_server_password = <ScaleIO Gateway user password>
  default_protection_domain_name = <ScaleIO protection domain>
  default_storage_pool_name = <ScaleIO pool name>

Optional parameters::

  [scaleio]
  default_provisioning_type = <thick (default) or thin>
  verify_server_certificate = <True or False (default)>
  server_certificate_path = <Path to the certificate>
  default_sdcguid = <ScaleIO SDC guid of compute host>
  rest_server_port = <ScaleIO Gateway port, 443 by default>

To get more flexibility, extra_spec of flavors can contain:

====================== =========================
Key                    Value
====================== =========================
disk:domain            ScaleIO protection domain
disk:pool              ScaleIO pool name
disk:provisioning_type *thick* or *thin*
====================== =========================

If a key is not set in a flavor, default value is used from config file.

Each flavor intended to be used with ScaleIO image backend must have disk sizes
in multiples of 8 Gb. A flavor with zero root disk size may be used to create
volume backed instances only, because that it is not recommended to create such
flavor. At the same time zero ephemeral/swap size is processed by usual way.

If an OpenStack deployment has compute nodes, which use any other image
backend, and there is necessary to have ScaleIO-incompatible flavors there, it
is possible to get this with scheduler filtering using flavor extra specs and
host aggregates.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Feodor Tersin <ftersin@hotmail.com>

Work Items
----------

* Implement all proposed changes at once.


Dependencies
============

A new library *siolib* [4]_ is used to communicate with ScaleIO via REST API.

Testing
=======

* Unit tests.

* Will be tested with a new thirdparty ScaleIO CI, using the same or similar
  infrastructure as ScaleIO Cinder CI does.

No new Tempest test will be introduced.


Documentation Impact
====================

Documentation about usage of ScaleIO for ephemeral storage backend will be
added.

There is a list of potentially touched doc pages with required changes.

+----------------------------------------------+------------------------------+
| Document page                                | Changes                      |
+----------------------------------------------+------------------------------+
| `Operations Guide - Architecture Compute     | Mention Shared Block Storage |
| Nodes - Instance Storage Solutions`__        | as a ComputeNode Storage,    |
|                                              | and mention ScaleIO there    |
| __ http://docs.openstack.org/ops-guide/arch- |                              |
|    compute-nodes.html#instance-storage-      |                              |
|    solutions                                 |                              |
+----------------------------------------------+------------------------------+
| `High Availability Guide - Configuring       | Mention ScaleIO there as an  |
| Storage for high availability - Storage back | option for ephemeral storage |
| end`__                                       |                              |
|                                              |                              |
| __ http://docs.openstack.org/ha-guide/       |                              |
|    storage-ha-backend.html                   |                              |
+----------------------------------------------+------------------------------+
| `Administrator Guide - Compute - System      | Add a section which explains |
| administration - Advanced configuration`__   | how to configure Compute to  |
|                                              | use ScaleIO, what to tune in |
| __ http://docs.openstack.org/admin-guide/    | flavors, how to isolate      |
|    compute-adv-config.html                   | ScaleIO hosts from other     |
|                                              | flavors                      |
+----------------------------------------------+------------------------------+
| `Configuration Reference - Compute service - | Mention *scaleio* section    |
| Overview of nova.conf`__                     |                              |
|                                              |                              |
| __ http://docs.openstack.org/newton/config-  |                              |
|    reference/compute/nova-conf.html          |                              |
+----------------------------------------------+------------------------------+
| `Configuration Reference - Compute service - | Describe full *scaleio*      |
| The full set of available options`__         | section                      |
|                                              |                              |
| __ http://docs.openstack.org/newton/config-  |                              |
|    reference/compute/config-options.html     |                              |
+----------------------------------------------+------------------------------+
| `Configuration Reference - Compute service - | Add *sio* to the list of     |
| Hypervisors - KVM - Configure Compute        | available *images_type*      |
| backing storage`__                           | option values                |
|                                              |                              |
| __ http://docs.openstack.org/newton/config-  |                              |
|    reference/compute/hypervisor-kvm.html     |                              |
|   #configure-compute-backing-storage         |                              |
+----------------------------------------------+------------------------------+

References
==========

.. [1] `Dell EMC ScaleIO portal <http://www.emc.com/storage/scaleio/
   index.htm>`_, see also `ScaleIO vs Ceph comparison
   <https://cloudscaling.com/blog/cloud-computing/killing-the-storage-unicorn-
   purpose-built-scaleio-spanks-multi-purpose-ceph-on-performance>`_.

.. [2] See blueprints `nova-ephemeral-cinder <https://blueprints.launchpad.net/
   nova/+spec/nova-ephemeral-cinder>`_, `nova-ephemeral-storage-with-cinder
   <https://blueprints.launchpad.net/nova/+spec/
   nova-ephemeral-storage-with-cinder>`_.

.. [3] `Puppet <https://forge.puppet.com/cloudscaling/scaleio_openstack>`_,
   `JuJu charm <https://jujucharms.com/u/cloudscaling/scaleio-openstack>`_,
   `Fuel plugin <https://github.com/openstack/fuel-plugin-scaleio>`_.

.. [4] `Python ScaleIO client <https://pypi.python.org/pypi/siolib>`_.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
