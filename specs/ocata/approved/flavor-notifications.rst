..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Notifications on flavor operations
==================================

https://blueprints.launchpad.net/nova/+spec/flavor-notifications

Nova currently does not send notifications on flavor create/update/delete
operations.

Flavors have a base set of attributes (id, name, cpus, ram, disk, swap,
ephemeral, rxtx). Privately accessible flavors also have a set of tenants
allowed to use them. Finally, they also have additional information
(accessed through get_keys() from the API but also referred to as extra_specs).

It would be useful to receive create, update and delete notifications on
any of this information changing, and the payload should contain the same
information for create and update as accessible from the API.

Problem description
===================

Use Cases
---------

An external system like Searchlight[1] wants to index the flavors which
makes the query for large number of flavors faster and efficient. This
will allow powerful querying as well unified search across openstack
resources (flavor being one of them).

The maintainer wants to get the notifications when there are flavors added,
updated or destroyed.

Proposed change
===============

Versioned notifications will be added for the following actions:

* Flavor.create
* Flavor.save_projects
* Flavor.add_access
* Flavor.remove_access
* Flavor.save_extra_specs
* Flavor.destroy

.. note:: Flavor doesn't have an update API, the updating action for flavor
          is combined with delete and create.

Alternatives
------------
None

Data model impact
-----------------

No database schema change is needed.

The following new object will be added to flavor for create, save_projects,
and save_extra_specs.

.. code-block:: python

    @base.NovaObjectRegistry.register
    class FlavorNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('FlavorPayload')
        }

    @base.NovaObjectRegistry.register
    class FlavorPayload(notification.NotificationPayloadBase):
        # Version 1.0: Initial version
        SCHEMA = {
            'id': ('flavor', 'flavorid'),
            'name': ('flavor', 'name'),
            'ram': ('flavor', 'memory_mb'),
            'vcpus': ('flavor', 'vcpus'),
            'disk': ('flavor', 'root_gb'),
            'ephemeral': ('flavor', 'ephemeral_gb'),
            'swap': ('flavor', 'swap'),
            'rxtx_factor': ('flavor', 'rxtx_factor'),
            'vcpu_weight': ('flavor', 'vcpu_weight'),
            'disabled': ('flavor', 'disabled'),
            'is_public': ('flavor', 'is_public'),
            'extra_specs': ('flavor', 'extra_specs'),
            'projects': ('flavor', 'projects'),
        }
        VERSION = '1.0'
        fields = {
            'id': fields.StringField(),
            'name': fields.StringField(nullable=True),
            'ram': fields.IntegerField(),
            'vcpus': fields.IntegerField(),
            'disk': fields.IntegerField(),
            'ephemeral': fields.IntegerField(),
            'swap': fields.IntegerField(),
            'rxtx_factor': fields.FloatField(nullable=True),
            'vcpu_weight': fields.IntegerField(nullable=True),
            'disabled': fields.BooleanField(),
            'is_public': fields.BooleanField(),
            'extra_specs': fields.DictOfStringsField(),
            'projects': fields.ListOfStringsField(),
        }
        def __init__(self, flavor):
            super(FlavorPayload, self).__init__()
            self.populate_schema(flavor=flavor)

The following new object will be added to flavor for destroy:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class FlavorDestroyNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('FlavorDestroyPayload')
        }

    @base.NovaObjectRegistry.register
    class FlavorDestroyPayload(notification.NotificationPayloadBase):
        # Version 1.0: Initial version
        SCHEMA = {
            'id': ('flavor', 'flavorid'),
        }
        VERSION = '1.0'
        fields = {
            'id': fields.StringField(),
        }
        def __init__(self, flavor):
            super(FlavorDestroyPayload, self).__init__()
            self.populate_schema(flavor=flavor)

The definition of NotificationBase can be found [2].

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------

New notifications for flavor different actions will be emitted to a amqp topic
called 'versioned_notifications'.

Other end user impact
---------------------
None

Performance Impact
------------------

Notifications will be emitted if the versioned notification is enabled.

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
  liyingjun

Work Items
----------

* Add versioned notifications for flavor

Dependencies
============
None

Testing
=======

Besides unit test new functional test cases will be added to cover the
new notifications and the tests will assert the validity of the stored
notification samples as well.

Documentation Impact
====================
None

References
==========

[1]: Searchlight: http://docs.openstack.org/developer/searchlight/index.html

[2]: Versioned notification: http://docs.openstack.org/developer/nova/notifications.html#versioned-notifications

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
