..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
VMware OVA support
==================

https://blueprints.launchpad.net/nova/+spec/vmware-driver-ova-support

This blueprint proposes to add support of spawning an instance from the disk
embedded in an OVA (`Open Virtualization Application <http://www.dmtf.org/standards/ovf>`_) glance image.

Problem description
===================

Given that the best practice for obtaining a compact, portable template of a
virtual machine in the vSphere platform is to export it into an OVF folder or
an OVA file, a frequent customer ask is to
be able to deploy them in OpenStack as Glance images and spawn new instances
with them.

In addition, OVF/OVA contains virtual disks that are converted to the
streamOptimized format, and streamOptimized disks are the only disk type
deployable on vSAN datastores (see blueprint `vmware-vsan-support <https://blueprints.launchpad.net/nova/+spec/vmware-vsan-support>`_)
Since exporting a virtual machine to OVA/OVF remains one of the most convenient
means to obtain streamOptimized disks, providing support for spawning using OVA
glance images will streamline the process of providing images for vSAN use.

Use Cases
----------

The end user will be able to export a VM from vCenter or any system
supporting the Open Virtualization Format and import it to OpenStack
without any transformation.

Project Priority
-----------------

None

Proposed change
===============

An OVF contains additional information about the virtual machine beyond its
disks - it has an .ovf XML descriptor file that describes the virtual machine
configuration (memory, CPU settings, virtual devices, etc).  But for the
purpose of this blueprint, it is treated essential as a container of a root
disk targetted for the spawn process.

Note: An OVA is essentially a tarball of an OVF bundle.  Given the current
image-as-a-single-file nature of glance images, it is more straightforward to
support the uploading/download of OVA as a Glance image.

The blueprint propose to support spawning of an image of container format 'ova'
and disk format 'vmdk'. The driver expects the image to be an OVA tar bundle.

While much of the information in the XML descriptor file could prove useful in
the proper configuration of the spawned virtual machine in the future, the
implementation of this blueprint will only perform minimal processing of the
XML file solely for the purpose of obtaining the right disk file to use for
spawn as well as type of the virtual disk adapter that the disk should be
attached to by default. The disk adapter type used will continue to be
overridable by specifying the "vmware_adaptertype" property in the spawn
operation.

Alternatives
------------

* When implemented, the vmware-vsan-support blueprint will allow spawning of
  streamOptimized disk. An alternative is to force all users to extract the
  streamOptimized disk from any OVA/OVF they intend to deploy in OpenStack and
  have the compute driver only support spawning of a streamOptimized disk
  image. This that puts unnecesary burden on the user.

* Use the Task framework under proposal in Glance to provide on-the-fly
  conversion of a supplied OVF/OVA into some other appropriate forms. This is
  closely related to the previous alternative, as it may provide a more
  streamlined workflow in glance to degenerate an incoming OVF into a single
  streamOptimized disk.

* Add support for OVF folder as the portable vSphere VM image. Since an OVF is
  a folder with multiple files, it does not work well with existing the glance
  model.

* There are other proposals that involves using images that references data in
  the hypervisor's datastore, or storing images directly on the datastore.
  These are welcome optimizations that will reduce the amount of glance<->nova
  nova transfers, but they do not address the issue of providing portable
  image data that can be deployed in other vCenter installations.

* Continue to force customers to upload images using the flat and sparse disk
  variants. Because there is no straightforward way of obtaining disk images of
  these type while still adopting the best practice of exporting virtual
  machines first, this leads a separate, lengthier and more error-prone
  workflow for preparing images for OpenStack use.

* Add logic in the client code to extract the content of the OVA and upload the
  VMDK content rather than than the entire OVA.

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

Users will be able to use the OVA images that they have been uploading
to Glance without being able to use them.

Performance Impact
------------------

OVA and streamOptimized disks are more space efficient and streamable, this
means less storage use in glance and faster first-time deployment times (as
compared to a flat or sparse disk image).

Other deployer impact
---------------------

This change will allow deployment of existing libraries of exported OVA images,
with little or no additional transformations. Existing image using flat/sparse
disk types may be deprecated/deleted in favor of OVA (or standalone
streamOptimized disks).

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------


Primary assignee:
 arnaudleg

Other contributors:
 tflower

Work Items
----------

* Download OVA, process embedded .ovf descriptor file for the path to the
  root disk in the OVA, and spawn using data from said disk.

Dependencies
============

None.

Testing
=======

Since Tempest in general does not support driver-specific tests, the proposal
is to update the `VMware NSX CI <https://wiki.openstack.org/wiki/NovaVMware/Minesweeper>`_
with additional tests
to verify spawning of instances using OVA images uploaded to glance with the
'ova' container format.

Documentation Impact
====================

In addition, new information in the vmware driver section of the Nova
documentation will have to be added to document:

* The parameters to use when uploading an OVA image.
* The scope of the information contained in the OVA that is used in the spawn
  process (essentially information pertaining to obtaining the root disk and
  not much else)

References
==========

* http://www.dmtf.org/standards/ovf
* https://wiki.openstack.org/wiki/NovaVMware/Minesweeper
* https://bugs.launchpad.net/glance/+bug/1286375
