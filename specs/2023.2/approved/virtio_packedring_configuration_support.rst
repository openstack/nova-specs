..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
VirtIO PackedRing Configuration support
==========================================

https://blueprints.launchpad.net/nova/+spec/virtio-packedring-configuration-support

This blueprint proposes to expose the LibVirt `packed` option that allows a
guest to negotiate support for the VirtIO packed-ring feature. This blueprint
is used to solicit community's input.

Problem description
===================

VM using a Virtio-net paravirtual network device uses Virtual queues (virtqs)
to send and recveive data between the virtio-net driver and the virtual or
physical backed. The VirtIO standard originally defined a single type of virtq
called split-ring queue. The latest edition of the standard (v1.1) adds a
different type of the virtq, called packed-ring queue. A different layout of
queue elements allows to increase the performance in both virtual and physical
backeds.

Split-ring support is the default option in VirtIO. Backends supporting
the packed-ring virtqs advertise this by setting the `VIRTIO_F_RING_PACKED`
feature bit during the feature negotiation. A guest driver then chooses the
virtq layout based on what it supports. As both options are identical features
wise, and the packed-ring is more efficient, the latter is typically chosen.

Qemu added support for the packed virtqs in v4.2 and LibVirt in v6.3. Qemu and
LibVirt supports the packed-ring virtqs via the `packed` option. However, note
that this option *does not* force the VM to use the packed-ring virtq. It acts
as a mask, allowing the backed to advertise the support when set. The driver in
the VM is still responsible for choosing the layout of virtqs.

This blueprint proposes to add a Nova flavor extra_spec and Glance image
property, that sets the `packed` option to `true` on the node. This way all VMs
running on the node are allowed to choose the virtq layout based on what is
offered by the backed, rather than being froced to use split-ring.

Use Cases
---------

As an operator, I want to benefit from the increase in the virtio-net
performance, by using a more efficient virtq structure.

Proposed change
===============

* Add ``hw_virtio_packed_ring`` for image property and
  ``hw:virtio_packed_ring`` for flavor extra specs.
  Users will control the packed virtqueue feature, and be able to disable
  it if desired.

  hw_virtio_packed_ring=true|false  (default false)
  hw:virtio_packed_ring=true|false  (default false)

* Provide new compute ``COMPUTE_NET_VIRTIO_PACKED`` capablity trait.
  This trait can be required/forbidden by user. Nova-compute agent
  will automatically set this trait to the resource provider summary
  if libvirt version is higher than 6.3

* This spec will update scheduling process. ALL_REQUEST_FILTERS will be
  extended with new filter packed_virtqueue_filter. It will update RequestSpec
  with new trait in case if image property or flavor extra_spec is enabled to
  avoid migration to the node without packed virtqueue feature support.

.. _'libvirt format domain':
  https://libvirt.org/formatdomain.html#virtio-related-options

Alternatives
------------

Leave as-is, operator will not have additional performance impact.

Data model impact
-----------------

None

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

VMs using virtio-net will see an increase in performance. The increase can be
anywhere between 10/20% (see DPDK Intel Vhost/virtio perf. reports) and 75%
(using Napatech SmartNICs).

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

* This spec will update scheduling process. New trait
  ``COMPUTE_NET_VIRTIO_PACKED`` will be set to the resource provider trait list
  automatically if this feaure is supported on the host.

* New Functional and Unit tests will be provided.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  justas_napa on IRC and Gerrit

The feature can be implemented by the Napatech devs dvo-plv@napatech.com and
obu-plv@napatech.com.

Feature Liaison
---------------

* Sean Mooney (sean-k-mooney)

Work Items
----------

N/A at this stage.

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

Configuration options reference will require an update.

References
==========

* VirtIO standard:
  https://docs.oasis-open.org/virtio/virtio/v1.1/csprd01/virtio-v1.1-csprd01.html

* LibVirt Domain XML reference
  https://libvirt.org/formatdomain.html#virtio-related-options

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Bobcat
     - Introduced
