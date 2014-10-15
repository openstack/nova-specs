..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
libvirt: virtio-net multiqueue
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-virtio-net-multiqueue

This blueprint aims to enhance the libvirt driver to enable the virtio-net
multiqueue. This will allow the guest instances to increase the total network
throughput.

Problem description
===================

Today's high-end servers have more processors, and guests running on them often
have an increasing number of vCPUs. In a single virtio-net queue, the scale of
the protocol stack in a guest is restricted, as the network performance does
not scale as the number of vCPUs increases. Guests cannot transmit or
retrieve packets in parallel, as virtio-net has only one TX and RX queue.

Multiqueue virtio-net provides the greatest performance benefit when:

- Traffic packets are relatively large.
- The guest is active on many connections at the same time, with traffic
  running between guests, guest to host, or guest to an external system.
- The number of queues is equal to the number of vCPUs. This is because
  multi-queue support optimizes RX interrupt affinity and TX queue
  selection in order to make a specific queue private to a specific vCPU.

Although the virtio-net multiqueue feature provides a performance benefit,
it has some limitations and therefore should not be unconditionally enabled:

- Guest OS is limited to ~200 MSI vectors. Each NIC queue requires a MSI
  vector, as well as any virtio device or assigned PCI device.
  Defining an instance with multiple virtio NICs and vCPUs might lead to a
  possibility of hitting the guest MSI limit.
- virtio-net multiqueue works well for incoming traffic, but can
  occasionally cause a performance degradation, for outgoing traffic.
- Enabling virtio-net multiqueue increases the total network throughput,
  but in parallel it also increases the CPU consumption.
- Enabling virtio-net multiqueue in the host QEMU config, does not enable
  the functionality in the guest OS. The guest OS administrator needs to
  manually turn it on for each guest NIC that requires this feature, using
  ethtool.
- MSI vectors would still be consumed (wasted), if multiqueue was enabled
  in the host, but has not been enabled in the guest OS by the administrator.
- In case the number of vNICs in a guest instance is proportional to the
  number of vCPUs, enabling the multiqueue feature is less important.
- Each virtio-net queue consumes 64 KB of kernel memory for the vhost driver.


Use Cases
---------
Guest instance users may benefit from increased network performance and
throughput.


Project Priority
-----------------
None


Proposed change
===============

In order to address the problem, an administrator should have the control
over the paralleled packet processing by disabling the multiqueue support
for certain workloads, where this feature may lead to a
performance degradation.

Introducing a new parameter to the image properties, for the users
to control the virtio-net multiqueue feature, and be able to disable it,
if desired.

    hw_vif_multiqueue_enabled=true|false  (default false)

Currently, the number of queues will match the number of vCPUs, defined for the
instance.

NOTE: Virtio-net multiqueue should be enabled in the guest OS manually, using
ethtool. For example:

    ethtool -L <NIC> combined #num_of_queues

Alternatives
------------

Considering the limited amount of MSI vectors in the guest,
users could have the ability to create instances with vNICs operating at
various traffic rates, by controlling the use of the multiqueue feature.

For example, one NIC might be used solely for administrative traffic
and so will not need multiqueue enabled, while other NICs might be used for
high throughput traffic and will require multiple queues.

  E.g. nova boot -nic net_id=<id>,queues=#

However, currently, there is no agreement on the interface the users use to
specify the number of queues per each vNIC.

Another option would be to replace "queues=#" with "throughput=high|medium|low"
which would set the number of queues to 100%|50%|1 of vCPUs.

There will be a need for a following spec to determine the correct interface.

Finally, the administrator could set the overall number of allowed queues on
the flavor extra_specs. However, since the amount of queues affects only the
guest resources, it should be up to the user to control the amount per each
nic.


Data model impact
-----------------

None

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

None

Other deployer impact
---------------------

None

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------
Primary assignee:
vromanso@redhat.com

Work Items
----------

* Update the vif config to set the correct number of vCPUs to
  virtio-net devices
* Update the NetworkRequest object to add number of queues per port

Dependencies
============

None


Testing
=======

Unit tests
Requires Libvirt >= 1.0.5

Documentation Impact
====================

The new parameters in flavor extra specs and the new network port property
"queues" in nova boot command.
Some recommendations for an effective usage, should be mentioned as well.


References
==========

http://www.linux-kvm.org/page/Multiqueue

