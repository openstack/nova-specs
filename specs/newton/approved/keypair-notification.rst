..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Improve notification for keypair
================================

https://blueprints.launchpad.net/nova/+spec/keypair-notification

Currently, no useful notification will be sent for keypair state change.
Nova notifies only key_name when creating/deleting keypair.
So it is impossible for users to search keypair information
(e.g. ssh public key) by using external system like searchlight.

Problem description
===================

Use Cases
---------

The external system wants to index the keypairs which makes the query for
large number of keypairs more fast and efficient.
Some users and systems want to search and retrieve ssh public keys and
fingerprints to cooperate with external systems by ssh passthrough.

Proposed change
===============

This spec will transform legacy notification to versioned notification
about the following keypairs events, and at the same time extend
contents of notification with extra data to support the above use case.

* keypair.create.start
* keypair.create.end
* keypair.delete.start
* keypair.delete.end
* keypair.import.start
* keypair.import.end

Alternatives
------------
None

Data model impact
-----------------

No database schema change is needed.

The following new objects will be added to keypair:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class KeypairNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('KeypairPayload')
        }

    @base.NovaObjectRegistry.register
    class KeypairPayload(notification.NotificationPayloadBase):
        # Version 1.0: Initial version
        SCHEMA = {
            'name': ('keypair', 'name'),
            'type': ('keypair', 'type'),
            'fingerprint': ('keypair', 'fingerprint'),
            'public_key': ('keypair', 'public_key'),
            'user_id': ('keypair', 'user_id')
        }
        VERSION = '1.0'
        fields = {
            'name': fields.StringField(),
            'type': fields.KeypairTypeField(),
            'fingerprint': fields.StringField(),
            'public_key': fields.StringField(),
            'user_id': fields.StringField(),
        }
        def __init__(self, keypair):
            super(KeypairPayload, self).__init__()
            self.populate_schema(keypair=keypair)

    class KeypairType(Enum):
        """Represents possible type values for a Keypair."""

        SSH = 'ssh'
        X509 = 'x509'

        ALL = (SSH, X509)

        def __init__(self):
            super(KeypairType, self).__init__(
                valid_values=KeypairType.ALL)

    class KeypairTypeField(BaseEnumField):
        AUTO_TYPE = KeypairType()

The definition of NotificationBase can be found [1].


REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------

Notification for keypair will be changed as follows:

* 'Before':::

        {
            "key_name": "key1"
        }

* 'After':::

        {
            "priority": "INFO",
            "payload": {
                "nova_object.namespace": "nova",
                "nova_object.name": "KeypairPayload",
                "nova_object.version": "1.0",
                "nova_object.data": {
                    "id": 1,
                    "name": "key1",
                    "type": "ssh",
                    "fingerprint": "6d:a1:2c:a3:.....",
                    "public_key": "Public key: ssh-rsa AAAAB3Nza......",
                    "user_id": "5ed98568284443b09b82f2a519a3f1d5",
                    "created_at": "2016-04-04T04:18:30.000000",
                    "deleted_at": None
                }
            },
            "event_type": "keypair.create.end",
            "publisher_id": "nova-compute:host1"
        }


Other end user impact
---------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  h-eguchi

Work Items
----------

* Add a new notification of keypairs which have a versioned payload.

We keep both notifications available in parallel for some time.
We will remove the legacy ones as soon as we have feature parity
in the versioned side.

Dependencies
============
None

Testing
=======

Besides unit test new functional test cases will be added to cover the
improved notifications.
And notification samples and related tests need to be added.

Documentation Impact
====================
None

References
==========

[1]: Versioned notification: http://docs.openstack.org/developer/nova/notifications.html#versioned-notifications

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
