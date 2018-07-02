..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Boot instance specific storage backend
======================================

https://blueprints.launchpad.net/nova/+spec/boot-instance-specific-storage-backend

This blueprint proposes adding support for specifying ``volume_type`` when
booting instances.

Problem description
===================
Currently, when creating a new boot-from-volume instance, the user can only
control the type of the volume by pre-creating a bootable image-backed volume
with the desired type in cinder and providing it to nova during the boot
process. When the user wants to boot the instance on the specified backend,
this is not friendly to the user when there are multiple storage backends in
the environment.

Use Cases
---------
As a user, I would like to specify volume type to my instances when I boot
them, especially when I am doing bulk boot. The "bulk boot" means creating
multiple servers in separate requests but at the same time.

However, if the user wants to boot instance on a different storage backends,
they only need to specify a different backend to send the create request
again.

Proposed change
===============
Add a new microversion to the servers create API to support specifying volume
type when booting instances.

This would only apply to BDMs with ``source_type`` of blank, image and
snapshot. The ``volume_type`` will be passed from ``nova-api`` through to
``nova-compute`` (via the BlockDeviceMapping object) where the volume gets
created and then attached to the new server.

The ``nova-api`` service will validate that the requested ``volume_type``
actually exists in cinder so we can fail fast if it does not or the user does
not have access to it.

Alternatives
------------
You can also combine cinder and nova to do this.

* Create the volume with the non-default type in cinder and then provide the
  volume to nova when creating the server.

Data model impact
-----------------
We'll have to store the ``volume_type`` on the BlockDeviceMapping object
(and block_device_mapping table in the DB).

REST API impact
---------------
* URL:
    * /v2.1/servers:

* Request method:
    * POST

The volume_type data will be able to add to request payload ::

    {
        "server" : {
            "name" : "device-tagging-server",
            "flavorRef" : "http://openstack.example.com/flavors/1",
            "networks" : [{
                "uuid" : "ff608d40-75e9-48cb-b745-77bb55b5eaf2",
                "tag": "nic1"
            }],
            "block_device_mapping_v2": [{
                "uuid": "70a599e0-31e7-49b7-b260-868f441e862b",
                "source_type": "image",
                "destination_type": "volume",
                "boot_index": 0,
                "volume_size": "1",
                "tag": "disk1",
                "volume_type": "lvm_volume_type"
            }]
        }
    }

Security impact
---------------
None

Notifications impact
--------------------
Add ``volume_type`` field to BlockDevicePayload object.

Other end user impact
---------------------
The python-novaclient and python-openstackclient will be updated.

When we snapshot a volume-backed server, the block_device_mapping_v2 image
metadata will include the volume_type from the BDM record so if the user then
creates another server from that snapshot, the volume that nova creates from
that snapshot will use the same volume_type. If a user wishes to change that
volume type in the image metadata, they can via the image API. For more
information on image-defined BDMs, see [1]_ and [2]_.

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Upgrade impact
--------------
To support rolling upgrades, the API will have to determine if the minimum
``nova-compute`` service version across the deployment (all cells) is
high enough to support user-specified volume types. If ``volume_type`` is
specified but the deployment is not new enough to handle it, a 409 error will
be returned to the user.

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  Brin Zhang

Work Items
----------
* Add ``volume_type`` support in compute API
* Add related tests

Dependencies
============
None

Testing
=======
* Add Tempest integration tests for scenarios like:

  * Boot from volume with a non-default volume type.
  * Snapshot a volume-backed instance and assert the non-default volume
    type is stored in the image snapshot metadata.

* Add related unit test for negative scenarios like:

  * Attempting to boot from volume with a specific volume type before the
    new microversion.
  * Attempting to boot from volume with a volume type that does not exist
    and/or the user does not have access to.
  * Attempting to boot from volume with a volume type with old computes that
    do not yet support volume type.

* Add related functional tests for positive scenarios

  * The functional API samples tests will cover the positive scenario for
    boot from volume with a specific volume type and all computes in all
    cells are running the latest code.

Documentation Impact
====================
Add docs that mention the volume type can be specified when boot instances
after the microversion.

References
==========
For a discussion of this feature, please refer to:

* https://etherpad.openstack.org/p/nova-ptg-stein
  Stein PTG etherpad, discussion on or around line 496.

* http://lists.openstack.org/pipermail/openstack-dev/2018-July/132052.html
  Matt Riedemann's recap email to the dev list on Stein PTG, about halfway
  down.

.. [1] https://docs.openstack.org/nova/latest/user/block-device-mapping.html
.. [2] https://github.com/openstack/tempest/blob/3674fb138/tempest/scenario/test_volume_boot_pattern.py#L210

History
=======
.. list-table:: Revisions
      :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced

