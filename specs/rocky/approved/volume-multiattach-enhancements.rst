..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Volume multiattach enhancements
===============================

https://blueprints.launchpad.net/nova/+spec/volume-multiattach-enhancements

This spec proposes adding a compute API microversion to allow
creating multiple servers in the same request using the same
multiattach volume and to allow the user to specify the attach
mode when attaching volumes to a server.


Problem description
===================

There are two problems this change will address.

1. Add the ability to boot multiple servers in a single request from a
   multiattach-capable volume.

   Related bug: https://bugs.launchpad.net/nova/+bug/1747985

   Users currently cannot create multiple servers in a single request with a
   multiattach volume because the compute API specifically blocks more than
   one server trying to attach to the same volume (and is not multiattach
   aware in that respect).

2. Add the ability to pass through the *attach_mode* when attaching volumes.

   Related bug: https://bugs.launchpad.net/cinder/+bug/1741476

   Currently all secondary attachments to a multiattach volume are in
   read/write mode. Users would like the ability to be able to specify that
   attachments to a multiattach volume are read-only. Nova will simply pass
   this through to Cinder when creating (or updating) the attachment (the
   attach mode is specified in the host connector parameter to
   ``POST /attachments`` and ``PUT /attachments/{id}``).

   While specifying a read-only attach mode mostly only makes sense when using
   multiattach volumes, the compute API will not distinguish between
   multiattach-capable volumes and non-multiattach-capable volumes when
   passing through the attach mode. By default the attach mode will match the
   default in Cinder which is read/write:

   https://github.com/openstack/cinder/blob/12.0.0/cinder/volume/manager.py#L4391

Use Cases
---------

As an end user of the compute API, I want to be able to create a set of
servers in a single request using the same multiattach volume.

As an end user of the compute API, I want to be able to attach the same
volume to multiple servers but have only one of those servers be able to
write to the volume.

As a Scientific SIG user [1]_, I want to create multiple servers with the same
read-only multiattach root volume for my baremetal instances.

Proposed change
===============

The following changes will be made to the compute API in a new microversion.

* Change the compute API _check_and_transform_bdm logic [2]_ such that if the
  new microversion is requested and a multiattach volume is being used, that
  multiattach volume can be re-used with multiple servers being created in a
  single request.

* Change the ``block_device_mapping_v2`` request body parameter schema to
  allow passing an ``attach_mode`` field. If not specified, volume BDMs will
  default to "rw" for read/write. The other possible value will be "ro" for
  read-only. This will allow for boot-from-volume scenarios where the volume
  should be attached in read-only mode.

  .. note:: The ``attach_mode`` field will only apply to block device
      mappings where ``destination_type=volume``. If ``destination_type=local``
      and ``attach_mode`` is specified, it will result in a
      ``400 HTTPBadRequest`` error response to the user. This is because local
      block devices are for swap or ephemeral disks and are not modeled as
      volumes in the block storage service, where the ``attach_mode`` field
      will be used. Rather than ignore the ``attach_mode`` request in this
      case, we will explicitly fail since it is not supported.

* Add an ``attach_mode`` parameter to the request body of the
  ``POST /servers/{server_id}/os-volume_attachments`` volume attach API.
  Similar rules apply to the ``block_device_mapping_v2`` schema: default is
  "rw" and the only other valid option is "ro".

When creating or updating a volume attachment with a host connector dict, the
``mode`` key will be added to the connector dict which is the current way to
pass this information through to Cinder since it is not a top-level parameter
on those APIs.

The compute RPC API version will be bumped to indicate which compute services
support user-defined attach modes. This will allow us to check (and fail) from
the API if a user tries to attach a volume in read-only mode to an instance
running on an old compute that does not yet support that functionality. That
would result in a 409 error response to the user.

**Swap volume**

The ``PUT /servers/{server_id}/os-volume_attachments/{attachment_id}`` swap
volume API request will not change. The block device mapping for the volume
being swapped *to* will have the same ``attach_mode`` as the volume being
swapped *from*. For example, if volume A is attached to server X in read-only
mode, and the user retypes the volume to B, then volume B will be attached to
server X in read-only mode also.


Alternatives
------------

**Multi-create**

Being able to create multiple servers in a single request all attached to the
same multiattach volume is admittedly non-essential since users can create the
servers in serial against the same multiattach volume. However, it makes for
a spotty API user experience when only certain features are supported
depending on which parameters are used to create a server, in this case server
multi-create, boot from volume and multiattach volumes.

**Attach mode**

Rather than the user specifying which attachments should be read/write and
which should be read-only, nova (or cinder) could count attachments to
multiattach volumes and make all secondary attachments read-only. This would
introduce a few problems though:

* There could be a race when counting connections.
* What should be the default attach mode for secondary attachments? Making
  that default configurable would mean adding config-driven API behavior which
  is not interoperable across OpenStack clouds.
* What should we do if the first and only read/write attachments is deleted
  and there are other read-only attachments to the volume? Should one of them
  be automatically changed to read/write so at least one server can write to
  the volume?

Because of these complexities, it was agreed by the nova and cinder teams at
the Rocky Project Team Gathering [3]_ that we would leave the decision on
attach mode up to the user.

Data model impact
-----------------

An ``attach_mode`` column will be added to the ``block_device_mappings``
table. For now, this just needs to be a nullable 2-character field.

An accompanying change will be made to the ``nova.objects.BlockDeviceMapping``
object.

We will not set a default value of "rw" in the data model since "local" BDMs
do not use an ``attach_mode``. Instead, the BlockDeviceMapping versioned
object will ensure a default value of "rw" is used for volume BDMs.

REST API impact
---------------

The following APIs will return the ``attach_mode`` value in the response body:

* ``GET /servers/{server_id}/os-volume_attachments``::

   {
       "volumeAttachments": [
           {
               "device": "/dev/sdd",
               "id": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
               "serverId": "4d8c3732-a248-40ed-bebc-539a6ffd25c0",
               "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
               "attach_mode": "rw"
           },
           {
               "device": "/dev/sdc",
               "id": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
               "serverId": "4d8c3732-a248-40ed-bebc-539a6ffd25c0",
               "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
               "attach_mode": "ro"
           }
       ]
   }

* ``GET /servers/{server_id}/os-volume_attachments/{volume_id}``::

   {
       "volumeAttachment": {
           "device": "/dev/sdd",
           "id": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
           "serverId": "2390fb4d-1693-45d7-b309-e29c4af16538",
           "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
           "attach_mode": "rw"
       }
   }

There are two API schema changes in a new microversion.

Server create
~~~~~~~~~~~~~

**POST /servers**

Add an **optional** ``attach_mode`` field to the ``block_device_mapping_v2``
request body parameter, e.g.::

  "block_device_mapping_v2": [{
      "boot_index": "1",
      "uuid": "ac408821-c95a-448f-9292-73986c790911",
      "source_type": "volume",
      "destination_type": "volume",
      "attach_mode": "ro"}]

The schema for the new field will be::

  'attach_mode': {
      'type': 'string',
      'enum': ['ro', 'rw'],
  }

Attach volume
~~~~~~~~~~~~~

**POST /servers/{server_id}/os-volume_attachments**

Add an **optional** ``attach_mode`` field to the ``volumeAttachment`` request
body parameter, e.g.::

   {
       "volumeAttachment": {
           "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
           "attach_mode": "ro"
       }
   }

The schema for the new field will be::

  'attach_mode': {
      'type': 'string',
      'enum': ['ro', 'rw'],
  }

Security impact
---------------

None

Notifications impact
--------------------

The ``nova.notifications.objects.instance.BlockDevicePayload`` object will
mirror the ``attach_mode`` field from the ``nova.objects.BlockDeviceMapping``
object. A new enum will be used to model the ``attach_mode`` field in
versioned objects.

Other end user impact
---------------------

Changes will be made to python-novaclient and python-openstackclient for the
resulting microversion.

Similarly, a new field may be added to the Horizon "Attach Volume" form but
that is out of the scope of this change.

Users that need/want to change the attach mode for a given volume and server
will need to detach the volume and then re-attach it with the desired mode.
The ``PUT /servers/{server_id}/os-volume_attachments/{attachment_id}`` API
will not change to grow an ``attach_mode`` parameter.

Performance Impact
------------------

None

Other deployer impact
---------------------

None. The API will check if a read-only attachment can be made to an instance
based on the compute RPC API version which allows for rolling upgrade support
of the nova-compute services.

Developer impact
----------------

None. This change is hypervisor-agnostic.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem.os@gmail.com> (mriedem)

Other contributors:
  None

Work Items
----------

* Add the data model and versioned object changes for the new ``attach_mode``
  field.
* Use the ``BlockDeviceMapping.attach_mode`` field in the compute service when
  attaching a volume to an instance. This will be during any call to create
  or update attachment where a host connector is specified, so not only normal
  volume attach but also during instance move operations like resize.
* Increment the compute RPC API version.
* Add the changes to the REST API with the new microversion to enable the
  feature.


Dependencies
============

`Bug 1747985`_ will need to be fixed in Cinder such that multiple attachments
can exist on a multiattach volume before they are all "completed", which
likely means adding "reserved" to the list of acceptable states for a
multiattach volume in this code. [4]_

.. _Bug 1747985: https://bugs.launchpad.net/nova/+bug/1747985


Testing
=======

* Unit tests for negative scenarios like:

  * Specifying ``attach_mode`` with the wrong microversion
  * Specifying ``attach_mode`` with the wrong value/format
  * Specifying ``attach_mode`` against an instance that is running on an older
    compute service
  * Specifying ``attach_mode`` with a ``destination_type=local`` BDM.
  * Trying to create multiple servers in a single request against a
    non-multiattach volume

* Functional tests for the usual API samples tests with the new microversion.
* Given the relative complexity involved with the
  "multi-create to same multiattach volume" scenario, a Tempest test should
  be added for that case.

Documentation Impact
====================

* The compute API reference will be updated for the new microversion.
* The `Known issues`_ section of the compute admin guide will be updated.

.. _Known issues: https://docs.openstack.org/nova/latest/admin/manage-volumes.html#known-issues

References
==========

* https://bugs.launchpad.net/nova/+bug/1747985
* https://bugs.launchpad.net/cinder/+bug/1741476

.. [1] https://etherpad.openstack.org/p/scientific-sig-ptg-rocky
.. [2] https://github.com/openstack/nova/blob/17.0.0/nova/compute/api.py#L731
.. [3] https://etherpad.openstack.org/p/nova-ptg-rocky
.. [4] https://github.com/openstack/cinder/blob/12.0.0/cinder/volume/api.py#L2071-L2081

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
