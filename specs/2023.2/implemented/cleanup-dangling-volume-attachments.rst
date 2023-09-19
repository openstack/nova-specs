..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Cleanup dangling volumes block device mapping
=============================================

https://blueprints.launchpad.net/nova/+spec/cleanup-dangling-volume-attachments

Find out if there are any dangling/unattached volumes in Nova and Cinder
database and remove them, if they exists.


Problem description
===================

In case after some volume related operation, volume get detached from instance
at but Nova did not get notified and thinks volume is still attached to an
instance because volume attachment id is still listed in BDM table of Nova.

This can lead to different issues in functionalities, which required volume
details from block_device_mapping table, such as live miration and resizing
of instance.

Similarly attachment for instance exists at Cinder side but not in Nova
DB.

Use Cases
---------

- As an operator, I want all dangling volume attachments safely removed
  from my instance, as having these attachments in BDM may makes instance
  goes to error state on instance startup.

- As an operator, I want all dangling volume attachments safely removed
  from my instance, so any volume-related operations do not get affected.

- As an admin, I want all dangling attachments listed at Cinder, safely
  removed from Cinder DB that are claiming to be for the instance.


Proposed change
===============

Notes
-----

To spawn a new instance, Nova retrieves a copy of the base OS image from
Glance, now this image is an instance storage, which means if we create any
file, it will persist in this storage. Nova creates a BDM for it in the
block_device_mapping database with source_type as image and destination_type
as local.

Similarly, when we ask Nova to attach volume to an instance, Nova creates a
BDM of it in the block_device_mapping database and sets source_type and
destination_type as volume.

Changes
-------

While restarting the instance, verify, on the basis of source_type and
volume_type, whether the attached BDM is a volume or not, if it is a volume,
then verify if this volume exists in Cinder or not. If it exists, verify if
its status is "in-use" or "available". If it's "in-use", that means the volume
attachment is correct, and both Nova and Cinder are aware of this attachment.
If it's "available" that means the volume is not attached properly to the
instance, so remove or soft delete the BDM from the block_device_mapping
database.

Also log the update info, so operators can be aware of the reason for this
modification in the database.

Code Changes
------------

To delete the BDM's from the database, we first must need to shutdown the
instance, so instance domain get redefined at the virt level. We need to make
sure BDM's updated before generating the new XML.

Hence, this functionality should be added in the instance reboot process.
While rebooting, update the block_device_mapping DB at Nova side and
volume_attachment DB at Cinder side via Cinder API call. Once after instance
shutoff properly, while starting again, at the virt level (such as libvirt)
driver module will generate a new XML domain with updated BDM's.

Functionality _delete_dangling_bdms() should be added inside ComptuteManager
and called from ComptuteManager.reboot_instance. It should verify whether
target volume BDM source and destination type is not image and local but
volume and then if target volume is not listed in Cinder or status of volume
at Cinder is 'available' and not 'in-use' delete the BDM mapping from
block_device_mapping table.

Once a dangling volume is found, log a message saying removing stale volume
attachments.

Alternatives
------------

- A cleanup functionality for Nova-manage utility, which takes instance
  and remove all dangling volumes from instance.

  .. code-block:: shell

    $ nova-manage volume_attachment cleanup <server-id>

- A cron job which check for each instance in the Nova BDM and Cinder
  volume_attachment table, if instance has dangling volumes, remove volume
  entry from table. In this job instance UUID is not required.

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

  None

Performance Impact
------------------

Server might take more time to reboot, as there will be GET and DELETE
API call(s) towards Cinder service.

It primarily depends on number of attachments to delete.

Other deployer impact
---------------------

  None

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
  auniyal

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

- Create a cleanup functionality and add in instance restart process.
- Add unit and functional tests for cleanup.


Dependencies
============

  None


Testing
=======

Unit and Functional tests will be added.


Documentation Impact
====================

- Releasenote for cleanup dangling volumes while server restart will be added.
- Update admin manage volumes doc.


References
==========

  None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.2 Bobcat
     - Introduced
