..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Libvirt hardware policy from libosinfo
======================================

https://blueprints.launchpad.net/nova/+spec/libvirt-hardware-policy-from-libosinfo

When launching an instance Nova needs to make decisions about how to configure
the virtual hardware. Currently these decisions are often hardcoded, or driven
by nova.conf settings, and sometimes by Glance image properties. The goal of
this feature is to allow the user to specify the guest OS type and then drive
decisions from this fact, using the libosinfo database.

Problem description
===================

When launching an instance Nova needs to make decisions about how to configure
the virtual hardware in order to optimize operation of the guest OS. The right
decision inevitably varies depending on the type of operating system being
run. The right decision for a Linux guest, might be the wrong decision for a
Windows guest or vica-verca. The most important example is the choice of the
disk and network device models. All Linux guests want to use virtio, since it
offers by far the best performance, but this is not available out of the box in
Windows images so is a poor default for them. A second example is whether the
BIOS clock is initialized with UTC (preferred by UNIX) or localtime (preferred
by Windows). Related to the clock are various timer policy settings which
control behaviour when the hypervisor cannot keep up with the required
interrupt injection rate. The Nova defaults work for Linux and Windows, but
are not suitable for some other proprietary operating systems.

While it is possible to continue to allow overrides of config via glance
image properties this is not an particularly appealing approach. A number of
the settings are pretty low level and so not the kind of thing that a cloud
application should directly expose to users. The more hypervisor specific
settings are placed on a glance image, the harder it is for one image to be
used to boot VMs across multiple different hypervisors. It also creates a
burden on the user to remember a long list of settings they must place on the
images to obtain optimal operation.

Historically most virtualization applications have gone down the route of
creating a database of hardware defaults for each operating system. Typically
though, each project has tried to reinvent the wheel each time duplicating
each others work leading to a plethora of incomplete & inconsistent databases.
The libosinfo project started as an attempt to provide a common solution for
virtualization applications to use when configuring virtual machines. It
provides a user extendible database of information about operating systems,
including facts such as the supported device types, minimum resource level
requirements, installation media and more. Around this database is a C API for
querying information, made accessible to non-C languages (including python) via
the magic of GObject Introspection. This is in use by the virt-manager and
GNOME Boxes applications for configuring KVM and Xen guests and is easily
consumable from Nova's libvirt driver.

Use Cases
----------

The core goal is to make it simpler for an end user to boot a disk image with
the optimal virtual hardware configuration for the guest operating system.

Consider that Nova is configured to use virtio disk & network devices by
default, so optimize performance for the common Linux guests. In modern
Linux though, there is the option of using a better virtio SCSI driver.
Currently the user has to set properties like

  # glance image-update \
     --property hw_disk_bus=scsi \
     --property hw_scsi_model=virtio-scsi \
     ...other properties...
     name-of-my-fedora21-image

There's a similar issue if the user wants to run guests which do not
support virtio drivers at all:

  # glance image-update \
     --property hw_disk_bus=ide \
     --property hw_nic_model=e1000 \
     ...other properties...
     name-of-my-windows-xp-image

We also wish to support per-OS timer drift policy settings and do not
wish to expose them as properties, since it would be even more onerous
on the user. eg

  # glance image-update \
     --property hw_rtc_policy=catchup \
     --property hw_pit_policy=delay \
     ...other properties...
     name-of-my-random-os-image

With this feature, in the common case it will be sufficient to just inform
Nova of the operating system name

  # glance image-update \
     --property os_name=fedora21 \
     name-of-my-fedora-image

Project Priority
-----------------

None.

Proposed change
===============

There is an existing 'os_type' glance property that can be used to indicate
the overall operating system family (windows vs linux vs freebsd). This is too
coarse to be able to correctly configure all the different versions of these
operating systems. ie the right settings for Windows XP are not the same as the
right settings for Windows 2008. The intention is to declare support for a
new standard property 'os_name'. The acceptable values for this property will
be taken from the libosinfo database, either of these attributes:

* 'short-id' - the short name of the OS
  eg fedora21, winxp, freebsd9.3

* 'id' - the unique URI identifier of the OS
  eg http://fedoraproject.org/fedora/21, http://microsoft.com/win/xp,
  http://freebsd.org/freebsd/9.3

For example the user can set one of:

'''

  # glance image-update \
     --property os_name=fedora21 \
     name-of-my-fedora-image

  # glance image-update \
     --property os_name=http://fedoraproject.org/fedora/21 \
     name-of-my-fedora-image

When building the guest configuration, the Nova libvirt driver will look
for this 'os_name' property and query the libosinfo database to locate
the operating system records. It will then use this to choose the default
disk bus and network model. If available it will also lookup clock and
timer settings, but this requires further development in libosinfo before
it can be used.

In the case that libosinfo is not installed on the compute host, the
current Nova libvirt driver functionality will be unchanged.

It may be desirable to add a new nova.conf setting in the '[libvirt]'
section to turn on/off the use of libosinfo for hardware configuration.
This would make it easier for the cloud admin to control behaviour
without having to change which RPMs/packages are installed. eg

'''
  [libvirt]
  hardware_config=default|fixed|libosinfo

Where

* default - try to use libosinfo, otherwise fallback to fixed defaults
* fixed - always use fixed defaults even if libosinfo is installed
* libosinfo - always use libosinfo and abort if not installed

In the future it might be possible to automatically detect what operating
system is present inside a disk image using libguestfs. This would remove
the need to even set the 'os_name' image property, and thus allow people to
obtain optimal guest performance out of the box with no special config tasks
required. Such auto-detection is out of scope for this blueprint though.

Alternatives
------------

A 1st alternative would be for Nova to maintain its own database of preferred
hardware settings for each operating system. This is the trap most previous
virtualization applications have fallen into. This has a significant burden
because of the huge variety of operating systems in existence. It is
undesirable to attempt to try to reinvent the libosinfo wheel which is already
mostly round in shape.

An 2nd alternative would be for Nova to expose glance image properties for
every single virtual hardware configuration aspect that needs to vary per
guest operating system type. This would mean the user is required to have a
lot of knowledge about low level hardware configuration which goes against
the general cloud paradigm. It is also a significant burden to remember to
set so many values.

Data model impact
-----------------

There will be no database schema changes.

There will be a new standard glance image property defined which will be stored
in the existing database tables, and should be considered a long term supported
setting.

REST API impact
---------------

There are no API changes required. The existing glance image property support
is sufficient to achieve the goals of this blueprint.

Security impact
---------------

Since this is simply about tuning the choice of virtual hardware settings there
should not be any impact on security of the host / cloud system.

Notifications impact
--------------------

No change.

Other end user impact
---------------------

The end user will need to know about the 'os_name' glance property and the list
of permissible values, as defined by the libosinfo project. This is primarily a
documentation task.

Performance Impact
------------------

Broadly speaking there should be no performance impact on the operation of the
OpenStack services themselves. Some choices of guest hardware, however, might
impose extra CPU overhead on the hypervisors. Since users already have the
ability to choose different disk/net models directly, this potential
performance impact is not a new (or significant) concern. It falls under the
general problem space of achieving strong separation between guest virtual
machines via resource utilization limits.

Other deployer impact
---------------------

There is likely to be a new configuration option in the nova.conf file under
the libvirt group. Most deployers can ignore this and leave it on its default
value which should just "do the right thing" in normal operation. It is there
as a override to force a specific usage policy.

Deployers may wish to install the libosinfo library on their compute nodes, in
order to allow Nova libvirt driver to use this new feature. If they do not
install the libosinfo library, operation of Nova will be unchanged vs previous
releases. Installation can be done with the normal distribution package
management tools. It is expected that OpenStack specific provisioning tools
will eventually choose to automate this during cloud deployment.

In the case of private cloud deployments, the cloud administrator may wish to
provide additional libosinfo database configuration files, to optimize any
custom operating systems their organization uses.

Developer impact
----------------

Maintainers of other virtualization drivers may wish to engage with the
libosinfo project to collaborate on extending its database to be suitable for
use with more virtualization technologies beyond KVM and Xen. This would
potentially enable its use with other virt drivers within Nova. It is none the
less expected that the non-libvirt virt drivers will simply ignore this new
feature in the short-to-medium term at least.

The new 'os_name' property might be useful for VMWare which has a mechanism for
telling the VMWare hypervisor what guest operating system is installed in a VM.
This would entail defining some mapping between libosinfo values and the VMWare
required values, which is a fairly straightforward task.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vladikr

Other contributors:
  berrange

Work Items
----------

* Integrate with libosinfo for setup of default disk/network device
  models in the Nova libvirt driver

* Extend devstack to install the libosinfo & object introspection packages

* Work with libosinfo community to define metadata for clock and timer
  preferences per OS type

* Extend Nova libvirt driver to configure clock/timer base on libosinfo
  database

Dependencies
============

The Nova libvirt driver will gain an optional dependency on the libosinfo
project/library. This will be accessed by the GObject introspection Python
bindings. On Fedora / RHEL systems this will entail installation of the
'libosinfo' packages and either the 'pyobject2' or 'python3-gobject' packages
(yes, both Python 2 and 3 are supported). Other modern Linux distros also
have these packages commonly available.

Note that although the GObject Introspection framework was developed under the
umbrella of the GNOME project, it does not have any direct requirements for the
graphical desktop infrastructure. It is part of their low level gobject library
which is a reusable component leveraged by many non-desktop related projects
now.

Testing
=======

The unit tests will of course cover the new code.

To test in Tempest would need a gate job which has the suitable packages
installed. This can be achieved by updating devstack to install the necessary
bits. Some new tests would need to be created to set the new glance image
property and then verify that the guest virtual machine has received the
expected configuration changes.

Documentation Impact
====================

The new glance image property will need to be documented. It is also likely
that we will want to document the list of valid values for this property.
Alternatively document how the user can go about learning the valid values
defined by libosinfo.

References
==========

* http://libosinfo.org
* https://wiki.gnome.org/action/show/Projects/GObjectIntrospection
* https://live.gnome.org/PyGObject
