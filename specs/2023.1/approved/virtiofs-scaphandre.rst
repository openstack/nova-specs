..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================================
Allow local scaphandre directory to be mapped to an instance using virtiofs
=============================================================================

https://blueprints.launchpad.net/nova/+spec/virtiofs-scaphandre

Scaphandre is a tool that can be used to measure compute and VM power
consumption down to processes. (https://github.com/hubblo-org/scaphandre)

If you want to know more, the BBC folks proposed an interesting use case
to create environmental dashboards:
https://superuser.openstack.org/articles/environmental-reporting-dashboards-for-openstack-from-bbc-rd/

Problem description
===================
Currently, this is not possible to get consumption per VM as scaphandre
requires a directory on the compute node accessible into running VMs.
This directory contains data required by the scaphandre instance (guest agent)
running on the VM to correctly reports VM and VM associated processes
consumption.

`Scaphandre proposed solution`__ to get these data is to mount the directory
using virtiofs in the VM.
However, the user can not do that, as it requires the VM XML definition file
to be modified. Nova fully manages this file, and as a result, only nova
can change it.

Use Cases
---------

- As a user, I want to know the consumption of my compute node and drill
  down to VM and VM processes individual consumption.

- As an administrator, I want to allow this usage but make sure the user
  can mount only the configured required directory. I also want not to leak
  cloud design insights.

Proposed change
===============

To simplify specifications, the feature will be named
`virtiofs-scaphandre`.

Although this feature is implemented to support scaphandre, other tools
could require this need. So the implementation will try to be as generic
as possible.

This change relies partially on
https://specs.openstack.org/openstack/nova-specs/specs/2023.1/approved/libvirt-virtiofs-attach-manila-shares.html
specification to build the VM XML file including virtiofs settings
(mostly `driver part`__).

This implies the same requirements and limitation.

- QEMU >=5.0 and libvirt >= 6.2
- Associated instances use file backed memory or huge pages
- Live migrate an instance will not be supported as life attach and detach has
  landed only "recently" in libvirt__.

Change description:

- Add a compute configuration option ``share_local_fs`` that specify mappings
  between compute source directory and VMs destination `mount_tags`__.

.. code-block:: text

  share_local_fs = { "/var/lib/libvirt/scaphandre": "scaphandre" }

- If the above configuration option is present starting the compute
  node, add a compute trait ``COMPUTE_SHARE_LOCAL_FS`` specifying the
  `virtiofs-scaphandre` feature is available on this compute.

- Users can add ``hw:power_metrics`` as
  extra specs or ``hw_power_metrics`` image properties, and thus 2 things
  will happen:

  1. Nova will schedule the instance to a host that has share_local_fs.
  2. Nova will add the virtiofs settings in the instance XML file as specified
     by the following example.

.. code-block:: xml

  <filesystem type='mount' accessmode='passthrough'>
      <driver type='virtiofs'/>
      <source dir='/var/lib/libvirt/scaphandre/<DOMAIN_NAME>'/>
      <target dir='mount_tag'/>
      <readonly />
  </filesystem>

.. note::

   The <DOMAIN_NAME> is the name reported by `virsh list`
   or `OS-EXT-SRV-ATTR:instance_name`.
   This is the common name between qemu process that scaphandre use to get the
   vm name and openstack.

   The instance name can be defined using the instance_name_template.
   https://docs.openstack.org/nova/latest/configuration/config.html#DEFAULT.instance_name_template

   Example:

   - "OS-EXT-SRV-ATTR:instance_name": "**instance-00000034**"
   - /usr/bin/qemu-system-x86_64 -name **guest=instance-00000034**...

- As a result, user will be able to mount the compute source directory on
  his VM using the following command line.

.. code-block:: shell

    user@instance $ mount -t virtiofs mount_tag /var/scaphandre

.. note::

   The user can see the mount_tag in the instance metadata. Mount automation
   can be build based on this mechanism.

.. __: https://hubblo-org.github.io/scaphandre-documentation/how-to_guides/propagate-metrics-hypervisor-to-vm_qemu-kvm.html
.. __: https://review.opendev.org/c/openstack/nova/+/833090
.. __: https://bugzilla.redhat.com/show_bug.cgi?id=1897708
.. __: https://libvirt.org/kbase/virtiofs.html#other-options-for-vhost-user-memory-setup

Alternatives
------------

NA

REST API impact
---------------

NA

Data model impact
-----------------

Introduce `hw_powermetrics` image property as a new property object.

Extend the flavor extra spec validation to check `hw:power_metrics`.

Security impact
---------------

The compute node filesystem will be shared read-only.
This is to prevent any modification on the host by VM users.

Notifications impact
--------------------

NA

Other end user impact
---------------------

The scaphandre installation and `configuration`__ on compute nodes is left
to the openstack administrator.

.. __: https://hubblo-org.github.io/scaphandre-documentation/how-to_guides/propagate-metrics-hypervisor-to-vm_qemu-kvm.html

Performance Impact
------------------

NA

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

NA

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  uggla (rene.ribaud)

Feature Liaison
---------------

Feature liaison:
  uggla

Work Items
----------

- New configuration option.
- Add new trait.
- Changes to share the compute node filesystem if requested by an image
  property or a flavor extra spec.

Dependencies
============

None

Testing
=======

- Functional API tests
- Integration Tempest tests

Documentation Impact
====================

Extensive admin and user documentation will be provided.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Antelope
     - Introduced
