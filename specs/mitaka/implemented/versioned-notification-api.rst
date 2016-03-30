..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Versioned notification API
==========================

https://blueprints.launchpad.net/nova/+spec/versioned-notification-api

The notification interface of nova is not well defined and the current
notifications define a very inconsistent interface. There is no easy
way to see from the notification consumer point of view what is the format
and the content of the notification nova sends.

Problem description
===================

This is the generic notification envelope format supported by oslo.messaging
[1]::

    {
        "priority": "INFO",
        "event_type": "compute.instance.update",
        "timestamp": "2015-09-02 09:13:31.895554",
        "publisher_id": "api.controller",
        "message_id": "06d9290b-b9b0-4bd5-9e76-ddf8968a70b4",
        "payload": {}
    }

The problematic fields are:

* priority
* event_type
* publisher_id
* payload


priority: Nova uses info and error priorities in the current code base except
in case of the nova.notification.notify_decorator code where the priority is
configurable with the notification_level configuration parameter. However this
decorator is only used in the monkey_patch_modules configuration default value.


event_type: oslo allows a raw string to be sent as event_type, nova uses the
following event_type formats today:

* <service>.<object>.<action>.<phase> example: compute.instance.create.end
* <object>.<action>.<phase> example: aggregate.removehost.end
* <object>.<action> example: servergroup.create
* <service>.<action>.<phase> example: scheduler.select_destinations.end
* <action> example: snapshot_instance
* <module?>.<action> example: compute_task.build_instances


publisher_id: nova uses the following publisher_id formats today:

* <service>.controller examples: api.controller, compute.controller
* <object>.controller example: servergroup.controller
* <object>.<object_id> example: aggregate.<aggregate.name> and
  aggregate.<aggregate_id>. See: [2].

It seems that the content of publisher_id and event_type overlaps in some
cases.

payload: nova does not have any restriction on the payload field which
leads to very many different formats. Sometimes it is a view of an existing
nova versioned object e.g. in case of compute.instance.update notification
nova dumps the fields of the instance object into the notification after some
filtering. In other case nova dumps the exception object or dumps the args and
kwargs of a function into the payload. This complex payload format seems to be
the biggest problem for notification consumers.

Use Cases
---------

As a tool developer I want to consume nova notifications to implement my
requirements. I want to know what is the format of the notifications and I want
to have some way to detect and follow up the changes in the notification format
later on.

Proposed change
===============

This spec is created to agree on the format, content and meaning of the fields
in notification sent by nova and to propose way to change the existing
notifications to the new format while giving time to the notification
consumers to adapt to the change. Also it tries to give a technical solution to
keep the notification payload more stable and versioned.

Current notifications are un-versioned. This spec proposes to transform the
un-versioned notification to versioned notifications while keeping the
possibility to emit un-versioned notifications for limited time to help the
transition for the notification consumers.

Versioned notifications will have a well defined format which is documented and
notification samples will be provided similarly to nova api samples.
New versions of a versioned notification will be kept backward compatible.

To model and version the new notifications nova will use the oslo
versionedobject module. To emit such notification nova will continue to use
the notifier interface of oslo.messaging module. To convert the notification
model to the format that can be fed into the notifier interface nova will use
the existing NovaObjectSerializer.

A single versioned notification will be modeled with a single oslo versioned
object but that object can use other new or existing versioned object as
payload field.

However some of the today's notifications cannot be really converted to
versioned notifications. For example the notify_decorator dumps the args and
kwargs of any function into the notification payload therefore we cannot create
a single versioned model for every possible payload it generates. For these
notifications a generic, semi-managed, dict based payload can be defined
that formulates as much as possible and leaves the rest of the payload
un-managed. Adding new semi-managed notifications shall be avoided in the
future.

We want to keep the notification envelope format defined by the notifier
interface in oslo.messaging, therefore versioned notifications will have the
same envelope on the wire as the un-versioned notifications.
Which is the following::

    {
        "priority": "INFO",
        "event_type": "compute.instance.update",
        "timestamp": "2015-09-02 09:13:31.895554",
        "publisher_id": "api.controller",
        "message_id": "06d9290b-b9b0-4bd5-9e76-ddf8968a70b4",
        "payload": {}
    }

The main difference between the wire format of the versioned and un-versioned
notification is the format of the payload field. The versioned notification
wire format will use the serialized format of a versioned object as payload.

The versioned notification model will define versioned object fields for every
fields oslo.messaging notifier interface needs (priority, event_type,
publisher_id, payload) so that a single notification can be fully modeled in
nova code. However only the payload field will use the default versioned object
serialization. The other fields in the envelope will be filled with strings as
in the example above.

The value of the event_type field of the envelope on the wire will be defined
by the name of the affected object, the name of the performed action emitting
the notification and the phase of the action. For example: instance.create.end,
aggregate.removehost.start, filterscheduler.select_destinations.end.
The notification model will do basic validation on the content of the
event_type e.g. enum for valid phases will be created.

The value of the the priority field of the envelope on the wire can be selected
from the predefined priorities in oslo.messaging (audit, debug, info, warn,
error, critical, sample) except 'warning' (use warn instead).
The notification model will do validation of the priority by providing an enum
with the valid priorities.

For concrete examples see the Data model impact section.

Backward compatibility
----------------------

The new notification model can be used to emit the current un-versioned
notification as well to provide backward compatibility while the un-versioned
notification will be deprecated. Nova might want to restrict adding new
un-versioned notification after this spec is implemented.

A new version of a versioned notification has to be backward compatible with
the previous version. Nova will always emit the latest version of a versioned
notification and nova will not support pinning back the notification versions.

Backward compatibility for pre Mitaka notification consumers will be ensured
by emitting both the verisoned and the un-versioned notification format on the
wire on separate topics. The new notification model will provide
a way to emit both old and new wire format from a same notification object.
A configuration option will be provided to specify which version of the
notifications shall be emitted but asking for the old format only will be
deprecated from the beginning. Emitting the un-versioned wire format of a
versioned notification will be deprecated along with a proper deprecation
message in Mitaka and will be removed in N release.



Alternatives
------------

Version the whole wire format instead of only the payload:

There seems to be two main alternatives how to generate the actual notification
message on the wire from the KeyPairNotification object defined in the Data
model impact section.

Use the current envelope structure defined by the notifier in oslo.messaging
[1] and use the versioning of the payload on the wire as proposed in the
Data model impact section.

Pros:

* No oslo.messaging change is required.
* Consumers only need to change the payload parsing code.
* Notification envelope in the whole OpenStack ecosystem are the same.

Cons:

* The envelope on the wire is not versioned just the payload field of
  it. However the envelope structure is generic and well defined by
  oslo.messaging.

Or alternatively create a new envelope structure in oslo.messaging that already
a versioned object and use the serialized form of that object on the wire.
If we change oslo.messaging to provide an interface where an object inheriting
from NotificationBase object can be passed in and oslo.messaging uses the
serialized from of that object as the message directly then KeyPair
notification message on the wire would look like the following::

    {
        "nova_object.version":"1.0",
        "nova_object.name":"KeyPairNotification",
        "nova_object.data":{
            "priority":"info",
            "publisher":{
                "nova_object.version":"1.19",
                "nova_object.name":"Service",
                "nova_object.data":{
                    "host":"controller",
                    "binary":"api"
                    ...  # a lot of other fields from the Service object here
                },
                "nova_object.namespace":"nova"
            },
            "payload":{
                "nova_object.version":"1.3",
                "nova_object.name":"KeyPair",
                "nova_object.namespace":"nova",
                "nova_object.data":{
                    "id": 1,
                    "user_id":"21a75a650d6d4fb28858579849a72492",
                    "fingerprint": "e9:49:b2:ca:56:8c:25:77:ea:0d:d9:7c:89..."
                    "public_key": "ssh-rsa AAAAB3NzaC1yc2EAA...",
                    "type": "ssh",
                    "name": "mykey5"
                }
            },
            "event_type":{
                "nova_object.version":"1.0",
                "nova_object.name":"EventType",
                "nova_object.data":{
                    "action":"create",
                    "phase":"start",
                    "object":"keypair"
                },
                "nova_object.namespace":"nova"
            }
        },
        "nova_object.namespace":"nova"
    }

In this case the NotificationBase classes shall be provided by the
oslo.messaging.

Pros:

* The whole message on the wire are versioned.

Cons:

* Needs extensive changes in oslo.messaging in the notification interface code
  as well as in the notification drivers as today notification drivers depend
  on the current envelope structure.
* It would create a circular dependency between oslo.messaging and
  oslo.versionedobject
* Consumers need to adapt to the top level structure change as well.

Use a single global notification version:

The proposal is to use separate version number per notification. Alternatively
a single global notification version number can be defined that is bumped every
time when a single notification has been changed.


Data model impact
-----------------

The following base objects will be defined:

.. code-block:: python

    class NotificationPriorityType(Enum):
        AUDIT = 'audit'
        CRITICAL = 'critical'
        DEBUG = 'debug'
        INFO = 'info'
        ERROR = 'error'
        SAMPLE = 'sample'
        WARN = 'warn'

        ALL = (AUDIT, CRITICAL, DEBUG, INFO, ERROR, SAMPLE, WARN)

        def __init__(self):
            super(NotificationPriorityType, self).__init__(
                valid_values=NotificationPriorityType.ALL)


    class NotificationPriorityTypeField(BaseEnumField):
        AUTO_TYPE = NotificationPriorityType()


    @base.NovaObjectRegistry.register
    class EventType(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'

        fields = {
            'object': fields.StringField(),
            'action': fields.EventTypeActionField(),   # will be an enum
            'phase': fields.EventTypePhaseField(),     # will be an enum
        }


    @base.NovaObjectRegistry.register
    class NotificationBase(base.NovaObject):

        fields = {
            'priority': fields.NotificationPriorityTypeField(),
            'event_type': fields.ObjectField('EventType'),
            'publisher': fields.ObjectField('Service'),
        }

        def emit(self, context):
            """Send the notification. """

        def emit_legacy(self, context):
            """Send the legacy format of the notification. """

Note that the publisher field of the NotificationBase will be used to fill the
publisher_id field of the envelope in the wire format by extracting the name of
the service and the host the service runs on from the Service object.

Then here is a concrete example that uses the base object:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class KeyPairNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('KeyPair')
        }

Where the referred KeyPair object is an already existing versioned object in
nova. Then the current keypair notification sending code can be written like:

.. code-block:: python

    def _notify(self, context, keypair):
        event_type = notification.EventType(
            object='keypair',
            action=obj_fields.EventTypeActionField.CREATE,
            phase=obj_fields.EventTypePhaseField.START)
        publisher = utils.get_current_service()
        keypair_obj.KeyPairNotification(
            priority=obj_fields.NotificationPriorityType.INFO,
            event_type=event_type,
            publisher=publisher,
            payload=keypair).emit(context)



When defining the payload model for a versioned notification we will try to
reuse the existing nova versioned objects like in case of the KeyPair example
above. If that is not possible a new versioned object for the payload will be
created.

The wire format of the above KeyPair notification will look like the
followings::

    {
        "priority":"INFO",
        "event_type":"keypair.create.start",
        "timestamp":"2015-10-08 11:30:09.988504",
        "publisher_id":"api:controller",
        "payload":{
            "nova_object.version":"1.3",
            "nova_object.name":"KeyPair",
            "nova_object.namespace":"nova",
            "nova_object.data":{
                "id": 1,
                "user_id":"21a75a650d6d4fb28858579849a72492",
                "fingerprint": "e9:49:b2:ca:56:8c:25:77:ea:0d:d9:7c:89:35:36"
                "public_key": "ssh-rsa AAAAB3NzaC1yc2EAA...",
                "type": "ssh",
                "name": "mykey5"
            }
        },
        "message_id":"98f1221f-ded0-4153-b92d-3d67219353ee"
    }

For an alternative wire format see the Alternatives section.

Semi managed notification example
---------------------------------

The nova.exceptions.wrap_exception decorator is used to send notification in
case an exception happens during the decorated function. Today this
notification has the following structure::

    {
        event_type: <the named of the decorated function>,
        publisher_id: <needs to be provided to the decorator via the notifier>,
        payload: {
            exception: <the exception object>
            args: <dict of the call args of the decorated function as gathered
                   by nova.safe_utils.getcallargs expect the ones that has
                   '_pass' in their names>
        }
        timestamp: ...
        message_id: ...
    }


We can define a following semi managed notification object for it::

    @base.NovaObjectRegistry.register
    class Exception(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'message': fields.StringField(),
            'code': fields.IntegerField(),
        }


    @base.NovaObjectRegistry.register
    class ExceptionPayload(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'exception': fields.ObjectField('Exception'),
            'args': fields.ArgDictField(),
        }


    @base.NovaObjectRegistry.register
    class ExceptionNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ExceptionPayload')
        }

Where the ArgDictField takes any python object, it uses object serialisation
when available, otherwise, a primitive->json conversion,
but if that fails, it just stringifies the object.
This field does not have a well defined wire format so this part of the
notification will not be really versioned, hence the semi versioned name.


send_api_fault notification example
-----------------------------------
The nova.notifications.send_api_fault function is used to send notification in
case of api faults. The current format of the notification is the following::

    {
        event_type: "api.fault",
        publisher_id: "api.myhost",
        payload: {
            "url": <the request url>,
            "exception": <the stringified exception object>,
            "status": <http status code>
        }
        timestamp: ...
        message_id: ...
    }

We can define the following managed notification object for it::

    @base.NovaObjectRegistry.register
    class ApiFaultPayload(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'url': fields.UrlField(),
            'exception': fields.ObjectField('Exception'),
            'status': fields.IntegerField(),
        }


    @base.NovaObjectRegistry.register
    class ApiFaultNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ApiFaultPayload')
        }

instance update notification example
------------------------------------
The nova.notifications.send_update function is used today to send notification
about the change of the instance. Here is an example of the current
notification format::

    {
        "priority":"INFO",
        "event_type":"compute.instance.update",
        "timestamp":"2015-10-12 14:33:45.704324",
        "publisher_id":"api.controller",
        "payload":{
            "instance_id":"0ab36db7-0770-47de-b34d-45adb17248e7",
            "user_id":"21a75a650d6d4fb28858579849a72492",
            "tenant_id":"8cd4a105ae504184ade871e23a2c6d07",
            "reservation_id":"r-epzg3dq2",
            "display_name":"vm1",
            "hostname":"vm1",
            "host":null,
            "node":null,
            "architecture":null,
            "os_type":null,
            "cell_name":"",
            "availability_zone":null,

            "instance_flavor_id":"42"
            "instance_type_id":6,
            "instance_type":"m1.nano",
            "memory_mb":64,
            "vcpus":1,
            "root_gb":0,
            "disk_gb":0,
            "ephemeral_gb":0,

            "image_ref_url":"http://192.168.200.200:9292/images/34d9b758-e9c8-4162-ba15-78e6ce05a350",
            "kernel_id":"7fc91b81-2ff1-4bd2-b79b-ec218463253a",
            "ramdisk_id":"25f19ee8-a350-4d8c-bb53-12d0f834d52f",
            "image_meta":{
                "kernel_id":"7fc91b81-2ff1-4bd2-b79b-ec218463253a",
                "container_format":"ami",
                "min_ram":"0",
                "ramdisk_id":"25f19ee8-a350-4d8c-bb53-12d0f834d52f",
                "disk_format":"ami",
                "min_disk":"0",
                "base_image_ref":"34d9b758-e9c8-4162-ba15-78e6ce05a350"
            },

            "created_at":"2015-10-12 14:33:45.662955+00:00",
            "launched_at":"",
            "terminated_at":"",
            "deleted_at":"",
            "new_task_state":"scheduling",
            "state":"building",
            "state_description":"scheduling",
            "old_state":"building",
            "old_task_state":"scheduling",
            "progress":"",

            "audit_period_beginning":"2015-10-12T14:00:00.000000",
            "audit_period_ending":"2015-10-12T14:33:45.699612",

            "access_ip_v6":null,
            "access_ip_v4":null,
            "bandwidth":{

            },
            "metadata":{

            },
        }
    }

We can define the following managed notification object for it::

    @base.NovaObjectRegistry.register
    class BwUsage(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'label': fields.StringField(),
            'bw_in': fields.IntegerField(),
            'bw_out': fields.IntegerField(),
        }


    @base.NovaObjectRegistry.register
    class FixedIp(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'label': fields.StringField(),
            'vif_mac': fields.StringField(),
            'meta': fields.DictOfStringsField(),
            'type': fields.StringField(),   # maybe an enum
            'version': fields.IntegerField(),  # maybe an enum
            'address': fields.IPAddress()
        }


    @base.NovaObjectRegistry.register
    class InstanceUpdatePayload(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'instance_id': fields.UUIDField(),
            'user_id': fields.StringField(),
            'tenant_id': fields.StringField(),
            'reservation_id': fields.StringField(),
            'display_name': fields.StringField(),
            'host_name': fields.StringField(),
            'host': fields.StringField(),
            'node': fields.StringField(),
            'os_type': fields.StringField(),
            'architecture': fields.StringField(),
            'cell_name': fields.StringField(),
            'availability_zone': fields.StringField(),

            'instance_flavor_id': fields.StringField(),
            'instance_type_id': fields.IntegerField(),
            'instance_type': fields.StringField(),
            'memory_mb': fields.IntegerField(),
            'vcpus': fields.IntegerField(),
            'root_gb': fields.IntegerField(),
            'disk_gb': fields.IntegerField(),
            'ephemeral_gb': fields.IntegerField(),
            'image_ref_url': fields.StringField(),

            'kernel_id': fields.StringField(),
            'ramdisk_id': fields.StringField(),
            'image_meta': fields.DictOfStringField(),

            'created_at': fields.DateTimeField(),
            'launched_at': fields.DateTimeField(),
            'terminated_at': fields.DateTimeField(),
            'deleted_at': fields.DateTimeField(),

            'new_task_state': fields.StringField(),
            'state': fields.StringField()
            'state_description': fields.StringField(),
            'old_state': fields.StringField(),
            'old_task_state': fields.StringField(),
            'progress': fields.IntegerField(),

            "audit_period_beginning": fields.DateTimeField(),
            "audit_period_ending": fields.DateTimeField(),

            'access_ip_v4': fields.IPV4AddressField(),
            'access_ip_v6': fields.IPV6AddressField(),
            'fixed_ips': fields.ListOfFixedIps(),

            'bandwidth': fields.ListOfBwUsages()

            'metadata': fields.DictOfStringField(),

        }


    @base.NovaObjectRegistry.register
    class InstanceUpdateNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('InstanceUpdatePayload')
        }


No db schema changes are foreseen.

REST API impact
---------------
None.

Security impact
---------------
None.

Notifications impact
--------------------

See the Proposed change and Data model section.

Other end user impact
---------------------

None.

Performance Impact
------------------

Sending both un-versioned and versioned wire format for a notification due to
keeping backward compatibility in Mitaka will increase the load on the message
bus. A config option will be provided to specify which version of the
notificatios shall be emited to mitigate this. Also the deployer can use NoOp
notification driver to turn the interface off.

Other deployer impact
---------------------

Backward compatibility for pre Mitaka notification consumers will be ensured
by emitting both the verisoned and the un-versioned notification format on the
wire for every versioned notification using the configured driver. Emitting the
un-versioned wire format of a versioned notification will be deprecated along
with a proper deprecation message in Mitaka and will be removed in N release.

A new config option ``notification_format`` will be introduced with three
possible values ``versioned``, ``un-versioned``, ``both`` to specify which
version of the notifications shall be emited. The ``un-versioned`` value will
be deprecated from the beginning to encourage deployers to start consuming
versioned notifications. In Mitaka the default version of this config option
will be ``both``.

Developer impact
----------------

Developers shall use the notification base classes when implementing a new
notification.


Implementation
==============

Assignee(s)
-----------


Primary assignee:
  * balazs-gibizer

Other contributors:
  * belliott
  * andrea-rosa-m

Work Items
----------

* Create the necessary base infrastructure e.g base classes, sample generation,
  basic test infrastructure, documentation
* Create a versioned notifications for an easy old style notification
  (e.g. keypair notifications) to serve as an example
* Create versioned notification for instance.update notification
* Create versioned notifications for nova.notification.send_api_fault type of
  notifications


Dependencies
============

None

Testing
=======

Functional test coverage shall be provided for versioned notifications.


Documentation Impact
====================

* Notification samples shall be generated for versioned notifications.
* A new devref shall be created that describe how to add new versioned
  notifications to nova


References
==========

* [1] http://docs.openstack.org/developer/oslo.messaging/notifier.html
* [2] https://github.com/openstack/nova/blob/master/nova/compute/utils.py#L320
* [3] https://github.com/openstack/nova/blob/bc6f30de953303604625e84ad2345cfb595170d2/nova/compute/api.py#L3769
* [4] The service status notification will be the first new notification using
  a versisoned payload https://review.openstack.org/#/c/182350/ . That spec
  will add only a minimal infrastructure to emit the versioned payload.


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
