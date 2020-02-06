..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Support delete_on_termination in server attach volume
=====================================================

https://blueprints.launchpad.net/nova/+spec/support-delete-on-termination-in-server-attach-volume

This blueprint proposes to support passing delete_on_termination during
volume attach so the attached volume can be deleted when the server is
deleted.

Problem description
===================
Currently, nova already supports the volume attach API, but it is not
possible to configure whether the data volumes can be deleted when the
instance is destroyed while the volume is being attached. This is a bit
awkward when configuring the server to handle the data volume in the
destroy instance.

Use Cases
---------
In large scale environment, lots of resources were created in system, and
sometimes an instance needs to be attached with more data volumes.
Therefore, the user needs to set the processing mode of the attached volume
for each instance. When destroying the instance, the data volume can be
deleted together, the invalid data is cleared, and the storage space is
released.

Proposed change
===============
Add a new microversion to volume attach API to support configuring whether
to delete the data volume when the instance is destroyed.

In the same microversion, add ``delete_on_termination`` to the GET responses
when showing attached volumes.

See the `REST API impact`_ section for details.

Alternatives
------------
The user cleans up the data volumes manually after deleting the server as they
would have to do today.

Data model impact
-----------------
None

REST API impact
---------------
URL: /v2.1/servers/{server_id}/os-volume_attachments

* Request method: POST (attach volume)

  Add the ``delete_on_termination`` parameter to the request body with the
  same semantics/schema as the initial server create
  ``block_device_mapping_v2`` object.

  .. code-block:: json

    {
      "volumeAttachment": {
        "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
        "delete_on_termination": true
      }
    }

  The default value of the ``delete_on_termination`` field is **False** if not
  specified.

* Request method: GET (list volume attachments)

  Add the ``delete_on_termination`` field to the response payload for attached
  volumes.

  .. code-block:: json

    {
      "volumeAttachments": [
        {
          "device": "/dev/sdd",
          "id": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
          "serverId": "fb6077e6-c10d-4e81-87fa-cb0f8c103051",
          "tag": "foo",
          "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
          "delete_on_termination": false
        },
        {
          "device": "/dev/sdc",
          "id": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
          "serverId": "fb6077e6-c10d-4e81-87fa-cb0f8c103051",
          "tag": null,
          "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
          "delete_on_termination": true
        }
      ]
    }

URL: /servers/{server_id}/os-volume_attachments/{volume_id}

* Request method: GET (show volume attachment)

  Add the ``delete_on_termination`` field to the response payload for attached
  volume.

  .. code-block:: json

    {
      "volumeAttachment": {
        "device": "/dev/sdc",
        "id": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
        "serverId": "fb6077e6-c10d-4e81-87fa-cb0f8c103051",
        "tag": null,
        "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f804",
        "delete_on_termination": true
      }
    }

.. note:: PUT /servers/{server_id}/os-volume_attachments/{volume_id} is not
          part of this proposed change since that API today is only implemented
          for the "swap volume" operation which is only implemented by the
          libvirt driver. [1]_ Modifying the PUT API is out of scope for this
          spec. If a user wishes to change the ``delete_on_termination`` value
          of a non-root attached volume, they can do so by detaching and
          re-attaching the volume with the updated ``delete_on_termination``
          value.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
python-novaclient and python-openstack client will need to be updated to
support the new ``delete_on_termination`` parameter when attaching a volume
and listing/showing attached volumes.

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
Depending on implementation there should be no upgrade impact. Today when a
volume is attached to a non-shelved-offloaded server, the BlockDeviceMapping
record is created in the ``nova-compute`` service. When attaching a volume
to a shelved offloaded server, the BDM is created in the API service. To avoid
issues with trying to attach a volume with ``delete_on_termination=true`` to
a server running on an older compute service, the implementation should just
set the field in the API rather than the compute service.

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  Brin Zhang

Work Items
----------
* Add ``delete_on_termination`` support in POST and GET os-volume_attachments
  APIs.
* Add ``delete_on_termination`` support in python-novaclient and
  python-openstackclient.
* Add related tests

Dependencies
============
None

Testing
=======
* Add related unit tests for negative scenarios such as trying to specify
  ``delete_on_termination`` during volume attach with an older microversion,
  passing ``delete_on_termination`` with an invalid value like null, etc.
* Add related functional tests for normal scenarions, e.g. API samples.

Tempest testing should not be necessary since in-tree functional testing with
the CinderFixture should be sufficient for testing this feature.

Documentation Impact
====================
Update the API reference for the affected APIs.

References
==========

.. [1] https://docs.openstack.org/nova/latest/user/support-matrix.html#operation_swap_volume

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
