..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Versioned notification transformation
=====================================

https://blueprints.launchpad.net/nova/+spec/versioned-notification-transformation-newton

In Mitaka the basic infrastructure for the versioned notification has been
merged [1]. Now it is time to start transforming our existing legacy
notifications to the new format. This spec proposes the first couple of
transformations.


Problem description
===================

The legacy notification interface of nova is not well defined and the legacy
notifications define a very inconsistent interface.
There is no easy way for a notification consumer to see the format and content
that nova will send.

Use Cases
---------

As a tool developer I want to consume nova notifications to implement my
requirements. I want to know what is the format of the notifications and I want
to have some way to detect and follow up the changes in the notification format
later on.

Proposed change
===============

Let's transform the following notifications first as they are the most common
notifications in the nova code base:

* instance.update is the biggest notification we have in nova in
  terms of payload size so this will give us good feedback about the
  usefulness of the new versioned notification infrastructure
* instance.delete.* is one instance of a common notification pattern in
  nova. There are similar notifications with instance.*
  event_type. All of them go through the same code path with different extra
  payload pieces. Therefore a generic instance action payload will be defined
  that can be used directly if there is no extra payload field for the
  event_type or can be subclassed easily to add the extra payload fields.
  Also there is a generic pattern to have action.start action.end and
  action.error notification of a given instance action. The new notifications
  will share payload classes between these event_types as much as possible.

  The instance.delete.end -- in the same way as
  identity.user.deleted -- is used by operators to trigger cleanup and billing
  activities when resources are freed in the system. Therefore it is important.
  Also nova wants to add new notifications with similar type in
  [3], [4] so creating an example will help those efforts as well.
* nova.exceptions.wrap_exception decorator emits a legacy notification with
  variable payload. The 'args' field of the notification is filled with the
  call args of the decorated function gathered by nova.safe_utils.getcallargs.
  So here we cannot formulate a fully versioned notification as that would
  require separate payload object for every decorated function which is
  unfeasible so we will only emit the static part of the information e.g.
  module name, function name, exception class, exception message.

During the transformation we will define an object model for these
notifications, see the Data model impact section for details. The new
notification objects will support emitting both the legacy and the new
versioned formats as well so the proposed change is backward compatible.

Alternatives
------------

We can start transforming the legacy notifications in a different order.

Data model impact
-----------------
Database schema is not impacted.


Separate namespace for notification objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently every object we have is private / internal to Nova. The object model
defined for notification payloads is part of the Nova public interface.
Therefore the notification model needs to be separated from the existing object
model, so that it is clear to developers when they define something that is
consumed outside of nova, and guarantee that we don't end up accidentally
exposing internal objects as part of the public notifications.

To achieve the necessary separation we will:

* We will move the already created notification related objects to a separate
  directory under nova/notifications/objects/ and we will add the newly
  proposed object there as well.
* The NotificationBase and NotificationPayloadBase will set
  OBJ_PROJECT_NAMESPACE to 'nova-notification' so all the notification related
  objects will belong to a separate ovo namespace.
* Keep using the NovaObject as a base class for the notification objects to
  keep the wire format but do not register notification object to the
  NovaObjectRegistry to avoid mixing nova internal objects with the
  notification objects.
* Separate the unit tests so that we can test the unregistered object hashes to
  maintain versioning.


instance.update and instance.delete
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The instance.delete and the instance.update notification has
a partially common payload, so we can create some base classes and then mix
them together as we need.

The following InstancePayload class holds the common part::

   @base.NovaObjectRegistry.register_if(False)
   class InstancePayload(notification.NotificationPayloadBase):
       SCHEMA = {
           'uuid': ('instance', 'uuid'),
           'user_id': ('instance', 'user_id'),
           'tenant_id': ('instance', 'project_id'),
           'reservation_id': ('instance', 'reservation_id'),
           'display_name': ('instance', 'display_name'),
           'host_name': ('instance', 'hostname'),
           'host': ('instance', 'host'),
           'node': ('instance', 'node'),
           'os_type': ('instance', 'os_type'),
           'architecture': ('instance', 'architecture'),
           'cell_name': ('instance', 'cell_name'),
           'availability_zone': ('instance', 'availability_zone'),

           'instance_type_id': ('instance', 'instance_type_id'),
           'memory_mb': ('instance', 'memory_mb'),
           'vcpus': ('instance', 'vcpus'),
           'root_gb': ('instance', 'root_gb'),
           'ephemeral_gb': ('instance', 'ephemeral_gb'),

           'kernel_id': ('instance', 'kernel_id'),
           'ramdisk_id': ('instance', 'ramdisk_id'),

           'created_at': ('instance', 'created_at'),
           'launched_at': ('instance', 'launched_at'),
           'terminated_at': ('instance', 'terminated_at'),
           'deleted_at': ('instance', 'deleted_at'),

           'state': ('instance', 'terminated_at'),
           'state_description': ('instance', 'task_state'),
           'progress': ('instance', 'progress'),

           'metadata': ('instance', 'metadata'),
       }
       # Version 1.0: Initial version
       VERSION = '1.0'
       fields = {
           'uuid': fields.UUIDField(),
           'user_id': fields.StringField(nullable=True),
           'tenant_id': fields.StringField(nullable=True),
           'reservation_id': fields.StringField(nullable=True),
           'display_name': fields.StringField(nullable=True),
           'host_name': fields.StringField(nullable=True),
           'host': fields.StringField(nullable=True),
           'node': fields.StringField(nullable=True),
           'os_type': fields.StringField(nullable=True),
           'architecture': fields.StringField(nullable=True),
           'cell_name': fields.StringField(nullable=True),
           'availability_zone': fields.StringField(nullable=True),

           'instance_flavor_id': fields.StringField(nullable=True),
           'instance_type_id': fields.IntegerField(nullable=True),
           'instance_type': fields.StringField(nullable=True),
           'memory_mb': fields.IntegerField(nullable=True),
           'vcpus': fields.IntegerField(nullable=True),
           'root_gb': fields.IntegerField(nullable=True),
           'disk_gb': fields.IntegerField(nullable=True),
           'ephemeral_gb': fields.IntegerField(nullable=True),
           'image_ref_url': fields.StringField(nullable=True),

           'kernel_id': fields.StringField(nullable=True),
           'ramdisk_id': fields.StringField(nullable=True),
           'image_meta': fields.DictOfStringsField(nullable=True),

           'created_at': fields.DateTimeField(nullable=True),
           'launched_at': fields.DateTimeField(nullable=True),
           'terminated_at': fields.DateTimeField(nullable=True),
           'deleted_at': fields.DateTimeField(nullable=True),

           'state': fields.StringField(nullable=True),
           'state_description': fields.StringField(nullable=True),
           'progress': fields.IntegerField(nullable=True),

           'ip_addresses': fields.ListOfObjectsField('IpPayload'),

           'metadata': fields.DictOfStringsField(),
       }

       def __init__(self, instance):
           super(InstancePayload, self).__init__()
           self.populate_schema(instance=instance)

Then here is the InstanceUpdatePayload that adds the extra fields unique for
the instance.update notification::

   @base.NovaObjectRegistry.register_if(False)
   class InstanceUpdatePayload(InstancePayload):
       # No SCHEMA as all the additional fields are calculated

       VERSION = '1.0'
       fields = {
           'state_update': fields.ObjectField('InstanceStateUpdatePayload'),
           'audit_period': fields.ObjectField('AuditPeriodPayload'),
           'bandwidth': fields.ListOfObjectsField('BandwidthPayload'),
           'old_display_name': fields.StringField(nullable=True)
       }

       def __init__(self, instance):
           super(InstanceUpdatePayload, self).__init__(instance)

Then here is the InstanceActionPayload that adds the extra fault field that is
common for every instance.<action> notification::

   @base.NovaObjectRegistry.register_if(False)
   class InstanceActionPayload(InstancePayload):
       # No SCHEMA as all the additional fields are calculated

       VERSION = '1.0'
       fields = {
           'fault': fields.ObjectField('ExceptionPayload', nullable=True),
       }

       def __init__(self, instance):
           super(InstanceActionPayload, self).__init__(instance)

Also we refer to a couple of extra classes in our payloads::

   @base.NovaObjectRegistry.register_if(False)
   class BandwidthPayload(base.NovaObject):
       # Version 1.0: Initial version
       VERSION = '1.0'
       fields = {
           'network_name': fields.StringField(),
           'in_bytes': fields.IntegerField(),
           'out_bytes': fields.IntegerField(),
       }


   @base.NovaObjectRegistry.register_if(False)
   class IpPayload(base.NovaObject):
       # Version 1.0: Initial version
       VERSION = '1.0'
       fields = {
           'label': fields.StringField(),
           'vif_mac': fields.StringField(),
           'meta': fields.DictOfStringsField(),
           'port_uuid': fields.UUIDField(nullable=True),
           'version': fields.IntegerField(),
           'address': fields.IPAddressField(),
       }

   @base.NovaObjectRegistry.register_if(False)
   class AuditPeriodPayload(base.NovaObject):
       # Version 1.0: Initial version
       VERSION = '1.0'
       fields = {
           'audit_period_beginning': fields.DateTimeField(nullable=True),
           'audit_period_ending': fields.DateTimeField(nullable=True),
       }


   @base.NovaObjectRegistry.register_if(False)
   class InstanceStateUpdatePayload(base.NovaObject):
       # Version 1.0: Initial version
       VERSION = '1.0'
       fields = {
           'old_state': fields.StringField(nullable=True),
           'state': fields.StringField(nullable=True),
           'old_task_state': fields.StringField(nullable=True),
           'new_task_state': fields.StringField(nullable=True),
       }

Now we can define the notification class for instance.update
notification::

   @notification.notification_sample('instance-update.json')
   @base.NovaObjectRegistry.register_if(False)
   class InstanceUpdateNotification(notification.NotificationBase):
       # Version 1.0: Initial version
       VERSION = '1.0'

       fields = {
           'payload': fields.ObjectField('InstanceUpdatePayload')
       }

Then we can define the three instance.delete.* notification::

   @notification.notification_sample('instance-action.json')
   @base.NovaObjectRegistry.register_if(False)
   class InstanceActionNotification(notification.NotificationBase):
       # Version 1.0: Initial version
       VERSION = '1.0'

       fields = {
           'payload': fields.ObjectField('InstanceActionPayload')
       }


Note that the payload of the instance.delete.start and
instance.delete.end and instance.delete.error has the same structure
therefore the same generic InstanceActionPayload can be used in the model.
This allows that both notifications can be created from the same
InstanceActionNotification class.

This model is intended to hold the same information as the existing legacy
notification however some changes are necessary:

* There are fields in the legacy notification like 'progress' which is either
  an integer or an empty string in the notification. This behaviour cannot be
  kept in the model so in the versioned notification 'progress' is a nullable
  integer instead.
* In the existing notification the 'bandwidth' field is a dict where the keys
  are network labels and the values are dicts with two key value pairs for the
  in and out bandwidth. The new model simplifies this to a list of dict where
  every dict has three key value pairs one for the label and two for the
  bandwidths.
* Audit period fields were at the root level of the payload in the legacy
  instance.update notification now it is moved to a sub object.

The proposed IpPayload, InstanceStateUpdatePayload and the AuditPeriodPayload
classes are separate definitions from the existing nova.object classes. The
existing ones are for nova internal use and the new ones are for notification
payload use. We cannot use the same name for these objects as ovos just use the
unqualified name of the class to validate the content of the field.


nova.exception.wrap_exception
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The nova.exceptions.wrap_exception decorator is used to send notification in
case an exception happens during the decorated function. Today this
notification has the following structure::

    {
        event_type: <the named of the decorated function>,
        publisher_id: <needs to be provided to the decorator via the notifier>,
        payload: {
            exception: <the exception object>
            args: <dict of the call args of the decorated function as gathered
                   by nova.safe_utils.getcallargs except the ones that has
                   '_pass' in their names>
        }
        timestamp: ...
        message_id: ...
    }

Having a variable event_type makes it really hard to consume these
notifications so in the versioned format we shall define a single event_type
'compute.exception' and add the function name into the payload instead.

We can define a following notification object for it::

    @base.NovaObjectRegistry.register_if(False)
    class ExceptionPayload(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'module_name': fields.StringField(),
            'function_name': fields.StringField(),
            'exception': fields.StringField(),
            'exception_message': fields.StringField()
        }


    @notification.notification_sample('compute-exception.json')
    @base.NovaObjectRegistry.register_if(False)
    class ExceptionNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ExceptionPayload')
        }

Also the NotificationPayloadBase class will be extended with two new nullable
fields instance_uuid and request_id as these are generic information for almost
every nova notification including instance action notifications.



REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------

The transformed notifications will have a new versioned notification format
emitted if the existing 'notification_format' config option is set to 'both' or
'versioned'. If the config is set to 'unversioned' or 'both' then the legacy
notification will be emitted unchanged.

As implemented in the versioned-notification-api bp the versioned notifications
are always emitted to a different amqp topic called 'versioned_notifications'
so the consumer can differentiate between the legacy and the new format by the
topic.

Other end user impact
---------------------
None

Performance Impact
------------------
If the 'notification_format' is set to 'both' then two instances of the same
notification will be emitted with different format.

Other deployer impact
---------------------
None

Developer impact
----------------
Developers adding new notification emitting code for the transformed
notifications needs to call the new interface provided by the new object model.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  balazs-gibizer

Work Items
----------

For each transformed notification:

* Move the existing notification related objects to a separate namespace
* Add the new object model
* Add the possibility to emit the legacy format with the new Notification class
* Change the nova codebase to call the new Notification class
* Add notification sample for the new versioned format


Dependencies
============
None

Testing
=======

Functional tests will be provided to exercise emitting the new versioned
notifications and the tests will assert the validity of the stored notification
samples as well.

Documentation Impact
====================

Notification sample files will be provided. The table about the versioned
notifications in the notification.rst [2] updates automatically.

References
==========

* [1] https://blueprints.launchpad.net/nova/+spec/versioned-notification-api
* [2] http://docs.openstack.org/developer/nova/notifications.html
* [3] https://blueprints.launchpad.net/openstack/?searchtext=expose-quiesce-unquiesce-api
* [4] https://blueprints.launchpad.net/openstack/?searchtext=add-swap-volume-notifications
* [5] https://blueprints.launchpad.net/oslo.versionedobjects/+spec/json-schema-for-versioned-object

History
=======


.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
