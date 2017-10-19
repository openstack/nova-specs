..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Service create and destroy versioned notification
=================================================

https://blueprints.launchpad.net/nova/+spec/service-create-destroy-notification

External system can get versioned notification [1] for service update based
information. But not for service create and destroy action.

Adding notifications for create and destroy help the external system to get
the realtime status for service without callback to the nova API.


Problem description
===================

Use Cases
---------

The external notification consumer like Searchlight wants to get the services
information when service created, updated or destroyed.

Proposed change
===============

Send notification for Service.create and Service.destroy as well as
Service.save [2].

Alternatives
------------

The only alternative is to poll /v2/{tenant_id}/os-services/ API periodically
however it means slower information flow and creates load on the nova API
and DB services.

Data model impact
-----------------

No database schema change is foreseen.

uuid field will need be added to ServiceStatusPayload for external system to
query the right service for updating or destroying, and make the data
consistent with new os-services API [3].

.. code-block:: python

    @base.NovaObjectRegistry.register
    class ServiceStatusPayload(base.NovaObject):
        SCHEMA = {
            'id': ('service', 'id'),
            'host': ('service', 'host'),
            'binary': ('service', 'binary'),
            'topic': ('service', 'topic'),
            'report_count': ('service', 'report_count'),
            'disabled': ('service', 'disabled'),
            'disabled_reason': ('service', 'disabled_reason'),
            'availability_zone': ('service', 'availability_zone'),
            'last_seen_up': ('service', 'last_seen_up'),
            'forced_down': ('service', 'forced_down'),
            'version': ('service', 'version')
        }
        # Version 1.0: Initial version
        # Version 1.1: Added id field
        VERSION = '1.1'
        fields = {
            'id': fields.UUIDField(),
            'host': fields.StringField(nullable=True),
            'binary': fields.StringField(nullable=True),
            'topic': fields.StringField(nullable=True),
            'report_count': fields.IntegerField(),
            'disabled': fields.BooleanField(),
            'disabled_reason': fields.StringField(nullable=True),
            'availability_zone': fields.StringField(nullable=True),
            'last_seen_up': fields.DateTimeField(nullable=True),
            'forced_down': fields.BooleanField(),
            'version': fields.IntegerField(),
        }

        def __init__(self, service):
            super(ServiceStatusPayload, self).__init__()
            self.populate_schema(service=service)

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------
New notifications service.create and service.delete will be introduced with
INFO priority and the payload of the notification will be the serialized form
of the already existing Service versioned object. Service.create notification
will be emitted after the service is created (so the id is available) and also
send the service.delete notification after the service is deleted.

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
  liyingjun


Work Items
----------

* Send version notifications for service.create and service.delete.


Dependencies
============
None

Testing
=======
Besides unit test new functional test cases will be added to cover the
new notifications


Documentation Impact
====================
None


References
==========

[1] Versioned notification https://docs.openstack.org/developer/nova/notifications.html

[2] https://github.com/openstack/nova/blob/stable/ocata/nova/objects/service.py#L312-L320

[3] http://specs.openstack.org/openstack/nova-specs/specs/pike/approved/service-hyper-uuid-in-api.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
