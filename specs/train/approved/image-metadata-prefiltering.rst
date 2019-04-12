..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
image metadata prefiltering
===========================

https://blueprints.launchpad.net/nova/+spec/image-metadata-prefiltering

Nova supports specifying hypervisor-specific device model via image properties.
Today when such properties are set on an image they are not considered when
scheduling unless the operator manually configures the ImagePropertiesFilter.
If the operator does not configure the ImagePropertiesFilter and an instance
is scheduled to a host that cannot support the requested device model, a late
check in the virt driver will fail the spawn and trigger a reschedule.
If only a subset of hosts can support the requested device model this
frequently results in a ``No valid host`` error.

This proposal suggests using standardised traits and placement to address
device model compatibility by extending existing virt drivers to declare the
device models they support as traits.

Problem description
===================

Use Cases
---------

As an operator I want the flexibility to deploy a heterogeneous cloud that has
compute nodes with different device model capabilities, either temporarily
during upgrades or permanently in a multi-architecture multi-hypervisor cloud,
without requiring explicit scheduler configuration.

As an operator, I would like to be able to communicate with my customers what
capabilities my cloud provides opaquely via standard traits instead of
revealing the specific versions of the software that is deployed so that they
can provide their own image that depends on those capabilities.

As an end user, I want to be able to succinctly specify device models or other
hypervisor-dependent capabilities requirements for my instance without needing
to be overly verbose.

Proposed change
===============

Step 1: Standard Traits
-----------------------
Well-defined image metadata properties that have a finite set of values
which represent virtualisation capabilities will be converted to standard
traits.

The current proposed set is

.. code-block:: json

   {
       "hw_vif_model": {
            "title": "Virtual Network Interface",
            "description": "Specifies the model of virtual network interface
            device to use. The valid options depend on the hypervisor
            configuration. libvirt driver options: KVM and QEMU:
            e1000, ne2k_pci, pcnet, rtl8139, spapr-vlan, and virtio.
            Xen: e1000, netfront, ne2k_pci, pcnet, and rtl8139.",
            "type": "string",
            "enum": [
                "e1000",
                "e1000e",
                "ne2k_pci",
                "netfront",
                "pcnet",
                "rtl8139",
                "spapr-vlan",
                "virtio"
            ]
        },

        "hw_video_model": {
            "title": "Video Model",
            "description": "The video image driver used.",
            "type": "string",
            "enum": [
                "vga",
                "cirrus",
                "vmvga",
                "xen",
                "qxl"
            ]
         },

        "hw_disk_bus": {
            "title": "Disk Bus",
            "description": "Specifies the type of disk controller to
            attach disk devices to.",
            "type": "string",
            "enum": [
                "scsi",
                "virtio",
                "uml",
                "xen",
                "ide",
                "usb",
                "fdc",
                "sata"
            ]
         },
   }

Note hw_cdrom_bus supports the same values as hw_disk_bus but is not
documented. hw_cdrom_bus will also be supported by this spec.
Other image properties that may also be worth considering are:

.. code-block:: json

   {
        "hypervisor_type": {
            "title": "Hypervisor Type",
            "description": "Hypervisor type required by the image."
            "type": "string",
            "enum": [
                "baremetal",
                "hyperv",
                "kvm",
                "lxc",
                "qemu",
                "uml",
                "vmware",
                "vz",
                "xen"
            ]
        },
        "vm_mode": {
            "title": "VM Mode",
            "description": "The virtual machine mode.
            This represents the host/guest ABI (application binary interface)
            used for the virtual machine."
            "type": "string",
            "enum": [
                "hvm",
                "xen",
                "uml",
                "exe"
            ]
        }
   }

While this spec primarily targets the device model specific image metadata
properties the same pattern could be applied to hypervisor_type and vm_mode.

Creation of the standard traits will be tracked using placement/os-traits
storyboard now that it is extracted from Nova so discussion of how
these traits will be named/namespaced will happen outside this spec.

Step 2: Reporting Of Capablities By Virt Drivers
------------------------------------------------

This spec primarily targets extending the libvirt driver; however as
these properties are also used by the vmware and fake drivers they will
also be extended.

To enable this feature, the virt drivers will be extended to report traits
for each device model they are capable of emulating on the compute node
resource provider. This will be done by introspection of the libvirt version,
qemu version, and Nova config such as CONF.virt_type.

To support upgrades without modifying existing images or flavors, the late
checks for device model support in the virt driver will not be removed.

Step 3: Requesting A Device Model And Scheduling
------------------------------------------------

A new scheduler prefilter will be added to automatically add the new traits
to requests. As adding new options to the device models requires a change to
Nova anyway, and these get updated infrequently, we can just have a mapping
table in a prefilter that added additional traits to the request spec by
looking up the appropriate image metadata key and appending the traits to the
request. This will not require changes to images to use the feature.

Alternatives
------------

Operators can continue to use image property filters

If the virt drivers are modified to report traits but a prefilter
is not added, the existing ability to specify required traits in an image
would be sufficient to consume the new traits, however, that would require
the image created to first specify the device model request and then also
the required traits.
e.g.
hw_vif_model=e1000 traits:compute_net_model_e1000=required
This will work but it's verbose.

As with other recent features, we could use the traits request as a
replacement for an image metadata property. If we chose this option we can
deprecate the image metadata data values in train e.g. hw_vif_model
and remove them in a later release. To use the feature and request a device
model going forward a trait would be used
e.g. traits:compute_net_model_e1000=required.
While this may seem nicer in some respects its more typing then the selected
option and has the disadvantage of requiring all image to be updated to include
the traits request. As such this is discarded due to the upgrade impact.

Operators can also achive the goals of this spec by manually creating nova host
aggregates or placement aggregates, then mapping the images to aggregates using
IsolatedHostsFilter or a aggregate member_of placement request.

Data model impact
-----------------

A new set of standard traits will be added to os-traits.
no other data model change should be required.

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

This is expected to improve boot performance in a heterogeneous cloud
by reducing reschedules. By passing a more constrained request to
placement this feautre should also reduce the resulting set of
allocation_candidates that are returned.

Other deployer impact
---------------------

A new config option will be added to enable the image metadata prefilter.
Initally this will default to disabled but that can be change in future
release after feedback on the performance impact.

Developer impact
----------------

None

Upgrade impact
--------------

No action is required on upgrade however just as with new deployments
if the operator wishes to enable this feature they will need to
update the nova config to enable it after upgrading.


Implementation
==============

Assignee(s)
-----------

sean-k-mooney

Work Items
----------

- Add new traits
- Modify libvirt virt driver to report traits
- Write prefilter
- Tests

Dependencies
============

None

Testing
=======

This can be tested entirely in the gate.
Functional and unit tests will be added.

While tempest tests could be added, since we do not have a
multinode gate job with different hyperviors tempest will
not be extended.

Documentation Impact
====================

A release note will be added and documentation of the new config option
for the prefilter will be provided. As there is no enduser impact
no user facing documentation will be required.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
