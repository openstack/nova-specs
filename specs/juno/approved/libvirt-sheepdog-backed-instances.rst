..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
Support Sheepdog ephemeral disks for libvirt driver
====================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-sheepdog-backed-instances

Add support for Sheepdog instance ephemeral disks.

Problem description
===================

Sheepdog block devices can already be attached to QEMU and KVM
virtual machines.  Nova's libvirt driver supports most of the
functionality. The only additional changes are to the image-backend
drivers. Both Glance and Cinder support sheepdog backends, so this
would complement the efforts made in those projects.


Proposed change
===============

This change would extend several parts of the libvirt driver. In
general, these changes are very similar to the changes required for
the RBD driver. These changes would bring Sheepdog support into
feature-parity with RBD, QEMU and other libvirt image drivers.

- nova.virt.libvirt.driver would be extended with cleanup functions
  for Sheepdog, in the same way that ``cleanup_rbd_instance`` does
  for the RBD backend.

- A new ``Image`` subclass class would be added to
  ``nova.virt.libvirt.imagebackend`` for Sheepdog.

- Helper functions would be added to ``nova.virt.libvirt.utils`` where needed.

- /etc/nova/rootwrap.d/filters would be extended to support rootwrap
  on the ``dog`` command used to interact with Sheepdog.

- See Deployer impact for configuration changes.

Alternatives
------------

Cinder has existing support for Sheepdog volumes. One alternative
is to use that driver and only launch instances from volumes. There
are two problems with this option. First, it would not support
instance disks that are deleted after the instance is destroyed.
Second, for the end-user it requires additional steps to provision
the volume before the instance is booted.

Data model impact
-----------------
None.

REST API impact
---------------

None. This blueprint makes no REST API changes.

Security impact
---------------
Rootwrap of 'dog' command on nova-compute machines.

Notifications impact
--------------------
None. No plans for new notifications.

Performance Impact
------------------
None.

Other end user impact
---------------------

None. This blueprint has no impact on python-novaclient or any other
end-user interface.

Other deployer impact
---------------------

To use this feature, a deployer must first set up a sheepdog cluster and
then make several configuration changes to nova on machines running the
nova-compute process. If Sheepdog is to be used with Glance and Cinder,
the deployer must also make the appropriate configuration changes for those
services.

To setup a Sheepdog cluster, follow the install guide provided by
Sheepdog [1]_. After setting up a Sheepdog cluster, each nova-compute
process must be configured. The following options must be set under
the ``[libvirt]`` section of ``nova.conf`` or ``nova-compute.conf``:

- ``images_type=sheepdog`` This must be set to indicate that sheepdog should
  be used.

- ``images_sheepdog_host=locahost`` Change this if the machine running the
  nova-compute process is not a member of the sheepdog cluster, or is not
  acting as a gateway node within the cluster.

- ``images_sheepdog_port=7000``` Change this if the sheep process is listening
  on a different port than the default.

For sites doing continuous deployment, this change will have no impact until
the deployer changes the ``images_type`` setting to deliberately switch a
nova-compute machine to use Sheepdog.

There are no database migrations required for this change.

Developer impact
----------------

This change would add an additional disk-backend to the libvirt driver,
slightly increasing code support costs.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <scott-devoid> Scott Devoid

Other contributors:
  <None>


Work Items
----------

- Implement basic support for Sheepdog images booted from a Glance image.

- Implement snapshot support.


Dependencies
============

None

Testing
=======

Devstack integration is required before tempest can run functional
tests against the Sheepdog drivers for Nova, Glance and Cinder. A patch
has been proposed which would use Sheepdog for each service. [2]_

This, I think, would result in many functional tests of the Sheepdog
drivers via the Tempest tests. However, a Jenkins job would need
to be defined and VMs would need to be provisioned to run the jobs.
It is not clear if openstack-infra is willing or capable of committing
to a proliferation of CI test runs. There is a Juno Summit scheduled for
this. [3]_


Documentation Impact
====================

- Configuration reference would need to be updated with the new configuration
  options. See the Deployer Impact section.

- Cloud Administer or Operations guide should be updated with a section which
  describes in detail how to configure Sheepdog for nova and what sort of
  considerations should be taken into account, e.g. cluster size, Zookeeper vs
  Corosync, the use of gateway nodes.

These documentation changes would happen as part of this blueprint.


References
==========

.. [1] https://github.com/sheepdog/sheepdog/wiki
.. [2] https://review.openstack.org/#/c/90244/
.. [3] http://summit.openstack.org/cfp/details/198
