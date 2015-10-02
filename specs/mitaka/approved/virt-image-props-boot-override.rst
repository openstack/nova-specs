..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Virt image properties boot time override
========================================

https://blueprints.launchpad.net/nova/+spec/virt-image-props-boot-override

This extends the Nova boot API so that it is possible to override any
image metadata properties at instance creation time. This avoids the
need to upload the same image to glance multiple times in order to
set slightly different properties for special use cases.

Problem description
===================

Nova has the ability to use various metadata properties recorded against
images in glance, to tailor the way an instance is configured at boot time.
For example, it might customize the type of hardware devices exposed, or
set a specific NUMA topology, or specify kernel command line arguments.

This works pretty well in general, but there are a significant number of
scenarios where the same image may need to be booted with a variety of
different properties set. Currently the only way to deal with this is to
upload the same image to glance multiple times, setting different properties
against each upload. This does not scale at all well, particularly if the
properties need to be different for every single instance booted.

Use Cases
----------

A tenant user may wish to make use of Nova compute as a service for building
disk images. This will entail running an operating system installer, such as
Fedora's Anaconda, in the virtual instance. There are two ways to boot such
installers. First they can boot from CDROM, in which case the tenant user is
presented with an interactive BIOS console where they can customize kernel
boot args used by the installer. Second they can boot from kernel+initrd, in
which case the kernel boot args can be passed programmatically. The latter
approach is necessary if any degree of automation of the install process is
desired. This requires the ability to customize the kernel arguments on a
per-instance basis.

A tenant user with NFV applications will wish to have fine control over
aspects of the virtual hardware policy, in particular usage of NUMA, hugepages
and CPU pinning policies. While some images they use have a standard policy
to be applied, it is not uncommon to want to change aspects of the policy at
instance boot time to suit a specific deployment need. For example, depending
on the size of the resources associated flavour they are booting, they may
wish to have different hugepage sizes used, or different number of NUMA nodes
created.


Proposed change
===============

The Nova boot API will be extended to include a new parameter which accepts
a dict of parameters. The keys in this dict will match those permitted by
the nova.objects.ImageMetaProps object fields.

In the Nova compute manager, the metadata properties from the image will be
augmented / overriden with the properties provided via the boot API. This
merged set of properties will be recorded as the image system metadata for
the instance. In this way no changes will be required to downstream code
in the virt drivers. The virt drivers will automatically see the per-instance
customized set.

The Nova client API will be extended to allow these new parameters to be passed
to the API, and the shell will gain a new --image-prop-override argument to set
this

::

  nova boot \
      --image IMAGE-ID \
      --image-prop-override "hw_os_command_line=console=ttyS0" \
      --image-prop-override "hw_numa_nodes=2" \
      --flavour m1.small \
      ...other args...


Alternatives
------------

Instead of allowing arbitrary override of the image metadata properties, it
would be possible to define a smaller set of allowed properties for the
boot time API. The intention behind such an approach would be to have a more
restrictive per-instance customization. The problem with such an approach
would be deciding just which properties to allow override of at boot time.
This would likely result in a never ending stream of requests from users to
add support for "just one more" property. Thus it is is considered simpler
to just allow override of any property defined by the ImageMetaProps object.

Instead of doing image metadata property overide, special case the specific
features that are needed. For example, the boot API could gain a new "kernel
command line" parameter. This would be extrememly niche and would ultimately
require many extra parameters to be added to the boot API to cover all
scenarios. This would in turn lead to lots more special case code in the
compute manager and virt drivers. It is far simpler to just customize the
existing defined image metadata properties.

Add support for soft-cloning with reference counting to Glance, so that it
is possible to cheaply create multiple images with different metadata, all
sharing the same underlying content. This could certainly be useful in
some scenarios where you are going to be repeatedly using the same set of
image metadata properties to boot multiple VMs. When you have a completely
one-off image metadata properties on every single boot attempt, creating
and then deleting images in glance each time is an undesirable burden on
the user.

Do nothing is always an alternative. In such a case, tenant users would have
to carry on with the current workaround which is to upload multiple copies of
the same image and set different properties against each copy. Glance could
potentially be enhanced to recognise when the same image content is uploaded
and de-duplicate the disk space consumed. This is still a rather tedious
approach for users though, particularly when every single instance wants a
slightly different override, as would be the case when using Nova to run distro
OS installers automatically.

Data model impact
-----------------

None

The compute manager boot code will take the new parameters from the boot
API and merge them into the existing image metadata dict which is stored
in the system metadata table. As such no new storage is required.

REST API impact
---------------

The POST method on the '/servers' location will be extended to gain a
new 'image_props_override' parameter. This will be a simple dict of
key/value strings. The accepted keys will be any of those permitted
by the nova.objects.ImageMetaProps object.

Taking the 'nova boot' example earlier, the JSON passed in the request
would look like this:

::

  {
      'server' : {
          'accessIPv4': '1.2.3.4',
          'accessIPv6': '80fe::',
          'name' : 'new-server-test',
          'imageRef' : 'http://glance.openstack.example.com/images/70a599e0-31e7-49b7-b260-868f441e862b',
          'flavorRef' : 'http://openstack.example.com/flavors/1',
          'metadata' : {
            'My Server Name' : 'Apache1'
          },
          'image_props_override' : {
            'hw_os_command_line' : 'console=ttyS0',
            'hw_numa_nodes' : '2',
          }
      }
  }

This will need a new API microversion

Security impact
---------------

Glance has a facility to set image property protection, to prevent a tenant
user from setting specific properties on an image. Since the image property
overrides are completely done in Nova, this is invisible to glance's access
control rules. To deal with this there will be a nova.conf property provided
that whitelists/blacklists what properties can be overridden at instance
boot time.

Notifications impact
--------------------

None

Other end user impact
---------------------

The nova client API will support the new parameter and the 'boot' shell
command will gain an '--image-prop-override' argument for specifying image
property override.

Performance Impact
------------------

None

Other deployer impact
---------------------

When an adminsitrator sets up property protections in glance, they need to
also consider whether the nova.conf property override whitelist needs to be
updated too.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  berrange

Other contributors:
  none

Work Items
----------

* Extend the Nova servers resource create method to accept the new parameter
* Extend the Nova compute manager to merge the boot time overrides with the
  image metadata properties, storing the result in the system metadata
* Extend the python nova client to pass in the new parameters

Dependencies
============

It depends in the compute manager being converted to use the ImageMetaProps
object, which is being completed in

  https://review.openstack.org/#/q/status:open+project:openstack/nova+branch:master+topic:virtimageprops-19,n,z

Testing
=======

New tempest test will be needed to boot a guest with image meta property
overrides and verify that the guest configuration was correspondingly
changed.

Documentation Impact
====================

The new Nova client 'boot' command parameters will need to be documented

References
==========

Previous related blueprints:

* Add kernel command line args to the boot API:

  https://blueprints.launchpad.net/nova/+spec/custom-kernel-args

* Add custom list of metadata properties to boot API

  https://blueprints.launchpad.net/nova/+spec/add-ability-to-pass-driver-meta-when-starting-instance

This blueprint comes out of feedback on those previous specs
which were considered to be too special cased and overly generic
respectively.
