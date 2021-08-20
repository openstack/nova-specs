..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================================
Add attachmentId to responses of the os-volume_attachments API
==============================================================

https://blueprints.launchpad.net/nova/+spec/add-attachmentid-to-responses-of-the-os-volume-attachments-api

This spec aims to outline the use case for adding volume attachment ids to the
responses of Nova's `os-volume_attachments APIs`__.

.. __: https://docs.openstack.org/api-ref/compute/?expanded=#servers-with-volume-attachments-servers-os-volume-attachments

Problem description
===================

When using the Cinder volume attachments API to attach a volume to an
instance Nova will record the id of the Cinder volume attachment within the
block device mapping table. However this is not exposed at present through
Nova's os-volume_attachments APIs and is only visible through Cinders
attachments API or direct queries to Nova's database.

For example, using the `v2.79 mircoversion`__ GETs against the API provide the
following responses:

.. __: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#maximum-in-train

* GET ``/servers/{server_id}/os-volume_attachments``

.. code-block:: json

    {
        "volumeAttachments": [
            {
                "delete_on_termination": false,
                "device": "/dev/sdc",
                "id": "227cc671-f30b-4488-96fd-7d0bf13648d8",
                "serverId": "d5e4ae35-ac0e-4311-a8c5-0ee863e951d9",
                "tag": null,
                "volumeId": "227cc671-f30b-4488-96fd-7d0bf13648d8"
            },
            {
                "delete_on_termination": true,
                "device": "/dev/sdb",
                "id": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113",
                "serverId": "d5e4ae35-ac0e-4311-a8c5-0ee863e951d9",
                "tag": "foo",
                "volumeId": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113"
            }
        ]
    }


* GET ``/servers/{server_id}/os-volume_attachments/{volume_id}``

.. code-block:: json

    {
        "volumeAttachment": {
            "delete_on_termination": true,
            "device": "/dev/sdb",
            "id": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113",
            "serverId": "2aad99d3-7aa4-41e9-b4e6-3f960b115d68",
            "tag": "foo",
            "volumeId": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113"
        }
    }

.. note:: The ``id`` returned above responses is the id of Nova's block device
          mapping record and not that of the volume attachment in Cinder.

This renders the API useless in most volume attach troubleshooting scenarios,
for example when attempting to ensure that Nova has an existing and correctly
updated volume attachment recorded.

Use Cases
---------

As an operator or user I want to be able to confirm the id of the Cinder volume
attachment associated with a given block device mapping record within Nova.

Proposed change
===============

Introduce a new microversion that will display the volume attachment id of a
given block device mapping record in the response of ``GET
/servers/{server_id}/os-volume_attachments`` or ``GET
/servers/{server_id}/os-volume_attachments/{volume_id}``.

Alternatives
------------

We could provide this information to operators via a ``nova-manage`` command
however that would require DB access and wouldn't be available to users.

Data model impact
-----------------

None, ``attachment_id`` is already stored for each block device mapping record.

REST API impact
---------------

In a new microversion, expose ``attachmentId`` in the following responses:

.. note::

    While implementing this spec it was agreed that the ``id`` field that
    duplicates the ``volumeId`` field would be removed under this microversion
    with the ``uuid`` of the underlying ``BlockDeviceMapping`` object also
    added under a new ``bdm_uuid`` field.

* GET ``/servers/{server_id}/os-volume_attachments``

.. code-block:: json

    {
        "volumeAttachments": [
            {
                "delete_on_termination": false,
                "device": "/dev/sdc",
                "serverId": "d5e4ae35-ac0e-4311-a8c5-0ee863e951d9",
                "tag": null,
                "volumeId": "227cc671-f30b-4488-96fd-7d0bf13648d8",
                "attachmentId": "1ce1a7ee-c88c-41ce-a4d3-ce78b1ab20bf",
                "bdm_uuid": "2420cbab-4aef-409f-97c0-b60c0e1d6902"
            },
            {
                "delete_on_termination": true,
                "device": "/dev/sdb",
                "serverId": "d5e4ae35-ac0e-4311-a8c5-0ee863e951d9",
                "tag": "foo",
                "volumeId": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113",
                "attachmentId": "810511b1-ab87-4f42-9033-199543376ddb",
                "bdm_uuid": "e50caeba-b3f0-4a59-9973-7125d232d511"
            }
        ]
    }


* GET ``/servers/{server_id}/os-volume_attachments/{volume_id}``

.. code-block:: json

    {
        "volumeAttachment": {
            "delete_on_termination": true,
            "device": "/dev/sdb",
            "serverId": "2aad99d3-7aa4-41e9-b4e6-3f960b115d68",
            "tag": "foo",
            "volumeId": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113",
            "attachmentId": "1ce1a7ee-c88c-41ce-a4d3-ce78b1ab20bf",
            "bdm_uuid": "2420cbab-4aef-409f-97c0-b60c0e1d6902"
        }
    }

Security impact
---------------

None, operators and users have access to the underlying attachment details via
the Cinder attachments API, all we are exposing here is the mapping of the
volume attachment to the block device mapping record within Nova.

Notifications impact
--------------------

None

Other end user impact
---------------------

The ``nova volume-attachments $SERVER`` and ``openstack server volume list
$SERVER`` commands will be extended to expose the ``attachment_id`` when
provided with a high enough microversion.

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

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    lyarwood

Other contributors:


Feature Liaison
---------------

Feature liaison:
    lyarwood

Work Items
----------

Dependencies
============

None

Testing
=======

API schema, functional and tempest integration tests will be written.

Documentation Impact
====================

The API reference, microversion history, openstackclient and novaclient docs
will be updated.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
