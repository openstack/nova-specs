..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Support for virtio-net rx/tx queue sizes
========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-virtio-set-queue-sizes

With the current multi-queue virtio-net approach, network performance
scales as the number of CPUs increase.  Large efforts are continuing
to increase the performance of network (typically DPDK applications)
in order to take advantage of the full capacity of each individual
vCPU.

Problem description
===================

vCPUs can be preempted by the hypervisor kernel thread even with a
strong partitioning in place (isolcpus, tuned). The preemption are not
frequent, few per seconds, but with 256 descriptor per virtio queue,
just one preemption of the vCPU will lead to packet drop, as the 256
slots are filled during the preemption: this is the case for NFV VMs,
where the per queue packet rate is above 1 Mpps (1 million of packets
per second).

Use Cases
---------

Larger queues sizes permit to amortizing the vCPU preemption and
avoiding packet drops, which is one of the main NFV requirements: zero
packet drop. With today's NFV VMs, 1k queues permit achieving high
performance without any packet drop, so being able to increase the
default queue size to 1k will solves today's issues. Making it
configurable, per operator choice, will also help to address future
NFV use cases (we are now shifting from 10Gbps NICs to 25Gbps NICs).

Proposed change
===============

In QEMU 2.7.0 and libvirt 2.3.0 a new tunable has been introduced to
configure RX queue size. In QEMU 2.10.0 and libvirt 3.7.0 a new
tunable has been introduced to update TX queue size of virtio NICs.

The proposed change is to add new options in "nova.conf" under the
"libvirt" section to update the default values of guest XML started on
host. So all guests that are using vif type model virtio backed to
vhost (VIF_TYPE_BRIDGE, VIF_TYPE_OVS) or backed to vhostuser
(VIF_TYPE_VHOSTUSER) will be booted with those new values.

* 'tx_queue_size'
* 'rx_queue_size'

For both options, `None` will be the default, meaning that libvirt
driver will not include any value for the queue size in the domain XML
of the guests.

The current implementation allows the size to be between 256 and 1024,
and that number should be a power of two. A warning message will be
printed for each guest started if the previous constraints are not
satisfied.

In case the values are updated while guests are running on the host,
only new guests booted will take advantage of those new
values. Meaning that the "old" guests running will remaining with the
previous values.

NOTE: Two special cases, during hard-reboot and cold-migration, the
domain XML of guests are regenerated meaning that they will take
advantage of the new values configured in "nova.conf".

NOTE: Trying to migrate guests which have queue sizes configured to
host which have libvirt or QEMU version that does not support such
configuration will not work. The migration process will rollback
letting the scheduler finding new host.

Alternatives
------------

Operators could achieve this by manually update domain XML of guests.

In Nova, configuring the tx/rx queues could also be achieved by
updating the binding profile of the ports created for an instance. But
it has been noticed that the tx/rx queues option is not related to
Networking but specific to the virtio framework, then allowing users
to update these values is not desirable since to correctly configure
them the hardware should be knowing.

In Nova, configuring the tx/rx queue sizes could also be achieved by
introducing flavor extra-specs which would have provided ability for
operators to restrict that feature to certain tenants, flexibility to
update the values and manage the hosts using aggregates. Ability to
configure different size for different flavors.

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

We are assuming that the compute nodes configured with new values for
network improvement are going to be isolated in specific aggregates. A
user who wants to take advantage of that network improvement would use
flavors that are configured to boot on those specifics aggregates.

Performance Impact
------------------

None

Other deployer impact
---------------------

Operators must configure `tx_queue_size` and/or `rx_queue_size` via
"nova.conf", then isolate the hosts on specific host aggregates and
configure flavor properties that will match properties of that
aggregate.

Alternatively, operators can avoid isolating hosts.


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
  Sahid Orentino Ferdjaoui <sahid-ferdjaoui>


Work Items
----------

* Introduce new options in nova.conf
* Update config xml to handle the new options at boot

Dependencies
============

None

Testing
=======

Unit tests are going to be added to ensure that the values of
`tx_queue_size` and/or `rx_queue_size` updated in "nova.conf" will be
take into account by guests booted on host.

Documentation Impact
====================

The documentation of the VIFs that are supporting this feature should
be updated as-well as the introduced config options in "nova.conf".

References
==========

* https://fedoraproject.org/wiki/Features/MQ_virtio_net

* https://dpdk.org/doc/guides/nics/virtio.html

* https://lists.gnu.org/archive/html/qemu-devel/2016-08/msg00730.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
