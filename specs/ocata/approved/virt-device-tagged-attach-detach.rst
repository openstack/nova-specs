..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Virtual guest device role tagging
=================================

https://blueprints.launchpad.net/nova/+spec/virt-device-tagged-attach-detach

This will provide a mechanism for the user to tag a device they have assigned
to their guest with a specific role. The tag will be matched to the hardware
address of the device and this mapping exposed to the guest OS via metadata
service/cloud-init.

Problem description
===================

It is common to create virtual instances which have multiple network devices or
disk drives. The tenant user creating the instance will often have a specific
role in mind for each of the devices. For example, a particular disk may be
intended for use as Oracle database storage, or as a Squid webcache storage,
etc. Similarly there may be specific network interfaces intended for use by a
network service application running in the guest.

The tenant user who is creating the instance does not have an explicit way to
communicate the intended usage of each device to the application running inside
the guest OS.

It may appear possible to identify a device via some aspect that the tenant
user knows, and then use the cloud-init / metadata service to provide a mapping
to the guest. For example, a MAC address could potentially be used to identify
NICs, or a disk device name string could be used to identify disks. The user
would then set a metadata tag. For example:

.. code-block:: console

  # nova boot \
      --image mywebappimage \
      --flavor m1.large \
      --meta oracledata=vda \
      --meta apachefrontend=02:10:22:32:33:22 \
      mywebapp

The problem is that, because Nova tries to hide as much detail of the guest
hardware setup as possible, it is not easy for the tenant user to know what the
unique identifiers for each device are. For example, while with emulated NICs,
it is possible to know the MAC address before booting the instance, when using
PCI assigned devices, this is not available.

Another approach might appear to be to identify devices based on the order in
which they appear to guests. eg the application in the guest could be set to
use the 3rd PCI NIC, or the 2nd disk on the SCSI bus. The problem with this is
that neither Nova nor the underlying hypervisor is able to provide a strong
guarantee around the device ordering in the guest. By good fortune, the order
in which disks are listed on the nova boot command line, often matches the
order in which device letters are assigned by Linux, but nothing guarantees
this to be the case long term.

Use Cases
----------

The tenant user needs to provide information to the guest instance to identify
which device to use for a desired guest application role.

For example, the tenant user wishes to instruct the Oracle database to use a
particular SCSI disk for its data storage, because they have configured that
disk to use a particular cinder volume that is built for high throughput. Or
they may wish to instruct an NFV application that it should process data from a
particular  network interface, because that interface is connected to an
interface in a second guest which is sending the required network traffic.

The tenant needs to be able to provide this identification information to the
guest OS, without knowing about how the particular hypervisor will configure
the virtual hardware.


Proposed change
===============

The proposal is to extend the REST API so that when adding disks or network
interfaces to a guest instance, it is possible to pass an opaque string "tag".

When booting a guest, Nova will determine what PCI, USB, SCSI address
corresponds to the device the user asked for, and create a metadata file that
maps the user provided tag to the hypervisor assigned device address.

This metadata file will be provided via either cloud-init or the metadata
service.

When the guest OS image boots up, it will read this metadata file to determine
which devices need to be used for particular application services running in
the instance. How the guest OS does this is outside the scope of this spec.
Nova is merely defining a file format and a set of information it will contain,
which the guest OS and/or applications can consume in a manner which they
prefer. There are no current standards in this area, so it is a greenfield
design for the file format.

For example, consider that the user created a new instance with a number of
NICs and block devices attached. These devices could be tagged, as shown
below:

.. code-block:: console

   nova boot \
       --image mywebappimage \
       --flavor m1.large \
       --nic net-id=12345,tag=nfvfunc1 \
       --nic net-id=56789,tag=nfvfunc2 \
       --block-device volume_id=12345,bus=scsi,tag=oracledb \
       --block-device volume_id=56789,bus=virtio,tag=squidcache \
       mynfvapp

Then Nova could auto-generate a metadata file that contained the following,
based on information reported by the Nova libvirt driver for the guest
instance:

.. code-block:: json

  {
    "devices": [
      {
        "type": "nic",
        "bus": "pci",
        "address": "0000:00:02.0",
        "mac": "01:22:22:42:22:21",
        "tags": ["nfvfunc1"]
      },
      {
        "type": "nic",
        "bus": "pci",
        "address": "0000:00:03.0",
        "mac": "01:22:22:42:22:21",
        "tags": ["nfvfunc2"]
      },
      {
        "type": "disk",
        "bus": "scsi",
        "address": "1:0:2:0",
        "serial": "disk-vol-2352423",
        "tags": ["oracledb"]
      },
      {
        "type": "disk",
        "bus": "pci",
        "address": "0000:00:07.0",
        "serial": "disk-vol-24235252",
        "tags": ["squidcache"]
      }
    ]
  }

In this example, we have provide a few bits of information about the devices

* The type of device info is provided for. Currently this is 'nic' or 'disk'.
  Other types will be provided in the future.
* The bus the device is attached to. This can be "pci", "scsi", "usb", "ide"
  and similar things. This is basically saying how to interpret the device
  address. The bus may be "none" in the case of containers, or where the device
  is integrated into the platform board.
* The device address. The format of the address varies based on the bus, but
  would be the PCI address, or SCSI address, of USB port, or IDE channel, etc.
* The network device MAC address, if type==nic.
* The disk drive serial string (if set & type==disk).
* The network device name, if type==nic and the hypervisor supports explicit
  device names (ie containers)
* The disk device name, if type==disk and the hypervisor supports explicit
  device names (ie containers)
* It is possible for the same tag to appear multiple times against different
  device types
* If the hypervisor provides two devices which mapo to the same backend, it is
  possible for the same tag to appear in both. This is the case with Xen HVM
  guests where a single block device is exposed via both Xen paravirt disk and
  IDE emulated disk. The guest chooses which to use.
* Although the syntax supports setting of multiple tags per device, initially
  the impl will only allow a single tag. The syntax just allows for future
  extension should there be a need.

Note that not all architectures support PCI buses, for example armv7 and s390
don't, so if a guest OS wishes to be portable it must not assume it will get
devices of a particular type. As such for device addressing, only the "bus"
attribute would be considered mandatory, the "address" attribute may be omitted
if that data is not available. Network devices would always have a "mac"
attribute present. Disk devices would have a "serial" attribute present if the
disk had an associated unique serial set. The virt drivers in Nova would
endeavour to make available as much information as possible.

The data reported to the guest OS will be considered a stable API that must be
maintained across future Nova releases in a backwards compatible manner. As
such, the data will be made to conform to a formal JSON schema, which will be
append-only to ensure future compatibility.

.. code-block:: json

   {
     "$schema": "http://json-schema.org/schema#",
     "id": "http://openstack.org/schemas/nova/metadata/device-role-tagging/1.0",
     "definitions": {
       "nonedevicebus": {
         "type": "object",
         "properties": {
           "bus": {
             "type": "string",
             "pattern": "none"
           }
         },
         "required": [ "bus" ]
       },
       "pcidevicebus": {
         "type": "object",
         "properties": {
           "bus": {
             "type": "string",
             "pattern": "pci"
           },
           "address": {
             "type": "string",
             "pattern": "[a-f0-9]{4}:[a-f0-9]{2}:[a-f0-9]{2}.[a-f0-9]"
           }
         },
         "required": [ "bus" ]
       },
       "usbdevicebus": {
         "type": "object",
         "properties": {
           "bus": {
             "type": "string",
             "pattern": "usb"
           },
           "address": {
             "type": "string",
             "pattern": "[a-f0-9]+:[a-f0-9]+"
           }
         },
         "required": [ "bus" ]
       },
       "scsidevicebus": {
         "type": "object",
         "properties": {
           "bus": {
             "type": "string",
             "pattern": "scsi"
           },
           "address": {
             "type": "string",
             "pattern": "[a-f0-9]+:[a-f0-9]+:[a-f0-9]+:[a-f0-9]+"
           }
         },
         "required": [ "bus" ]
       },
       "idedevicebus": {
         "type": "object",
         "properties": {
           "bus": {
             "type": "string",
             "pattern": "ide"
           },
           "address": {
             "type": "string",
             "pattern": "[0-1]:[0-1]"
           }
         },
         "required": [ "bus" ]
       },
       "anydevicebus": {
         "type": "object",
         "oneOf": [
           { "$ref": "#/definitions/pcidevicebus" },
           { "$ref": "#/definitions/usbdevicebus" },
           { "$ref": "#/definitions/idedevicebus" },
           { "$ref": "#/definitions/scsidevicebus" },
           { "$ref": "#/definitions/nonedevicebus" }
         ]
       },
       "nicdevice": {
         "type": "object",
         "properties": {
           "mac": {
             "type": "string"
           }
           "devname": {
             "type": "string"
           }
         },
         "required": ["mac"],
         "additionalProperties": {
           "allOf": [
             { "$ref": "#/definitions/anydevicebus" }
           ]
         }
       },
       "diskdevice": {
         "type": "object",
         "properties": {
           "serial": {
            "type": "string"
           },
           "path": {
             "type": "string"
           }
         },
         "additionalProperties": {
           "allOf": [
             { "$ref": "#/definitions/anydevicebus" }
           ]
         }
       }
     },

     "type": "object",

     "properties": {
       "devices": {
         "type": "array",
         "items": {
           "type": [
             { "$ref": "#/definitions/nicdevice" },
             { "$ref": "#/definitions/diskdevice" }
           ]
         }
       }
     }
   }

The implementation will consist of several parts. There will be a set of python
classes defined in nova/virt/metadata.py that are capable of representing the
data described by the JSON schema above, and generating a compliant JSON
document.

The virt drivers will be extended to populate instances of these classes with
the data associated with each instance.  The initial implementation will be
done for the Libvirt driver, however, other virt driver maintainers are
encouraged to provide the same functionality.

The metadata API will be extended to be capable of reporting this data
associated with a guest instance. This has a chicken and egg scenario for
network configuration. Guests relying on the metadata service will need to do a
minimal network configuration to reach the metadata service and obtain the info
from Nova.  They can then re-configure networking based on the device tag
information.

The config driver generator will be extended to be capable of including this
JSON data associated with a guest instance.  This is the preferred method where
guests need to rely on tags to confgure networking, as it has no chicken & egg
scenario.

In the future QEMU will be able export metadata directly via the firmware so it
will be available directly from the very earliest stages of boot. It is
expected this will be used as an additional optional transport in the future.

Outside the scope of the Nova work, a simple tool will be created that can
parse this metadata file and set tags against devices in the udev database. It
is anticipated that cloud-init would trigger this tool. Thus (Linux)
applications / OS images would not need to directly understand this Nova JSON
format.  Instead they could just query udev to ask for details of the device
with a particular tag. This avoids the applications needing to deal with the
countless different device bus types or addressing formats.

Example for Xen HVM with dual-disk devices

.. code-block:: json

   {
     "devices": [
       {
         "type": "nic",
         "bus": "xen",
         "address": "0",
         "mac": "01:22:22:42:22:21",
         "tags": ["nfvfunc1"]
       },
       {
         "type": "nic",
         "bus": "xen",
         "address": "1",
         "mac": "01:22:22:42:22:21",
         "tags": ["nfvfunc2"]
       },
       {
         "type": "disk",
         "bus": "ide",
         "address": "0:0",
         "serial": "disk-vol-123456",
         "tags": ["oracledb"]
       },
       {
         "type": "disk",
         "bus": "xen",
         "address": "0",
         "path": "/dev/xvda",
         "serial": "disk-vol-123456",
         "tags": ["oracledb"]
       }
       {
         "type": "disk",
         "bus": "ide",
         "address": "0:1",
         "serial": "disk-vol-789321",
         "tags": ["squidcache"]
       },
       {
         "type": "disk",
         "bus": "xen",
         "address": "1",
         "path": "/dev/xvdb",
         "serial": "disk-vol-789321",
         "tags": ["squidcache"]
       }
     ]
   }

Some things to note about this Xen example.

* There are two logical disks here, which Xen has exposed as *both* IDE and
  Xen paravirt.
* For the Xen paravirt disks, Xen can also provide a fixed guest path.
* The address for devices on Xen bus is just an integer which maps into the
  XenBus namespace.

Example for LXC container

.. code-block:: json

   {
     "devices": [
       {
         "type": "nic",
         "bus": "none",
         "mac": "01:22:22:42:22:21",
         "devname": "eth0",
         "tags": ["nfvfunc1"]
       },
       {
         "type": "nic",
         "bus": "none",
         "mac": "01:22:22:42:22:21",
         "devname": "eth1",
         "tags": ["nfvfunc2"]
       },
       {
         "type": "disk",
         "bus": "none",
         "serial": "disk-vol-2352423",
         "path": "/dev/sda",
         "tags": ["oracledb"]
       },
       {
         "type": "disk",
         "bus": "none",
         "serial": "disk-vol-24235252",
         "path": "/dev/sdb",
         "tags": ["squidcache"]
       }
     ]
   }

Some things to note about this LXC example:

* Containers do not export device buses to guests, as they don't emulate
  hardware. Thus the 'bus' is 'none' and there is no corresponding 'address'
* Containers are able to provide fixed disk paths and NIC device names

Alternatives
------------

Many users facing this problem have requested that Nova allow them to specify a
fixed PCI address when creating disks and/or network interfaces. In a
traditional data center virtualization world this would be an acceptable
request, but a goal of the cloud is to isolate tenant users from the specifics
of guest hardware configuration. Such configuration requires intimate knowledge
of the underlying hypervisor which is simply not available to tenant users, nor
should they be expected to learn that. In view of this, it is considered
inappropriate to allow tenant users to control the guest device addressing via
the REST API.

As noted in the problem description another approach is for the tenant user to
manually set tags via the existing mechanism for providing user metadata to
guests. This however relies on the user knowing some unique identifying
attribute for the device upfront. In some cases this is possible, but there are
a number of cases where no such information is available.

Data model impact
-----------------

The BlockDeviceMapping object (and associated table) will gain a freeform
string attribute, named "tag".

The NetworkRequest object (and associated table) will gain a freeform string
attribute, named "tag".

In future other device types, such as PCI devices or serial ports, may also
gain similar "tag" attributes. For the initial implementation only the disk and
network objects are to be dealt with.

REST API impact
---------------

The block device mapping data format will gain a new freeform string parameter,
named "tag", which can be set against each disk device. This would affect the
APIs for booting instances and hot-adding disks. In terms of the Nova client
this would be visible as a new supported key against the --block-device flag.
e.g.

.. code-block:: console

   $ nova boot --block-device id=UUID,source=image,tag=database

The volume attach API will similarly gain a new freeform string parameter in
the "volumeAttachment" data dict, named "tag". In terms of the Nova client this
would be visible as a new flag. e.g.

.. code-block:: console

   $ nova volume-attach --tag=database INSTANCE-ID VOLUME-ID

The server create API gain a new freeform string parameter in the "network"
data dict, named "tag", for each virtual interface. In terms of the Nova client
this would be visible as a new supported key against the --nic flag. e.g.

.. code-block:: console

   $ nova boot --nic net-id=UUID,port-id=UUID,tag=database

The interface attach API will similarly gain a new freeform string parameter in
the "interfaceAttachment" data dict, named "tag". In terms of the Nova client
this would be visible as a new flag. e.g.

.. code-block:: console

   $ nova interface-attach UUID --net-id UUID --port-id UUID --tag database

In all cases there will need to be validation performed to ensure that the
supplied "tag" string is unique within the scope of (instance, device-type). ie
you cannot have two NICs on the same instance with the same "tag", but you can
have a disk and a NIC with the same "tag".

If no tag is defined against a device, the corresponding device entry in the
metadata file will not have any tags listed. Since this is intended as an end
user feature, it is not considered appropriate for Nova to auto-generate tags
itself.

This will require a new API microversion

Security impact
---------------

None, this is merely providing some user metadata to the guest OS.

Notifications impact
--------------------

None

Other end user impact
---------------------

There will be new fields available when specifying disks or network interfaces
for virtual instances. The metadata service and cloud-init will have a new data
file made available containing the user tags & address information.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Artom Lifshitz

Other contributors:
  Daniel Berrange

Work Items
----------

* Define new attribute for BlockDeviceMapping object (Newton)
* Define new attribute for NetworkRequest object (Newton)
* Define new parameters for block device in REST API(s) (Newton)
* Define new parameters for network requests in REST API(s) (Newton)
* Define new parameters for network interface attachment in REST API(s)
* Define new parameters for volume attachment in REST API(s)
* Define a set of classes to represent the device metadata (Newton)
* Modify the metadata API to be able to serve the new data document (Newton)
* Modify the config drive generator to be able to include the new data
  document
* Modify the libvirt driver to populate the metadata about devices that have
  tags present (Newton)
* Modify the Nova client to allow the extra tag parameter to be provided
  (Newton)

Dependencies
============

An external GIT repository will be created that provides a tool that is capable
of parsing the Nova tag metadata and setting udev tags. This is not strictly a
dependency, but a highly desirable feature to facilite the use of this tag
information from Linux guests.

Cloud-init will be enhanced to invoke this tool when it finds the JSON tag
metadata is available from Nova.

Testing
=======

Tempest tests will create a guest with various NICs and disks, assign tags to
them, and then check the guest facing metadata file is present and contains
sensible data. NB, the actual data it contains will vary according to the
hypervisor running the tests, so care will need to be taken to ensure any test
is portable.

Documentation Impact
====================

The API documentation will need to be updated to list the new tag parameter
that is allowed against disk and network devices

The user documentation for cloud-init will need to describe the newly available
metadata file and its semantics.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - Re-proposed
   * - Newton
     - Implemented booting instances with tagged devices
   * - Ocata
     - Re-proposed to finish implementing attaching and detaching tagged devices
