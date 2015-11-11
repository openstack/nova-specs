..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Add notification for administrative service status change
=========================================================

https://blueprints.launchpad.net/nova/+spec/service-status-notification

Today external system cannot get notification based information about the nova
service status. Nova service status can be changed administratively via
os-services/disable API.

Having such a notification helps to measure the length of maintenance windows
or indirectly notify users about maintenance actions that possibly effect the
operation of the infrastructure.


Problem description
===================

Use Cases
---------

Deployer wants to measure the time certain nova services were disable
administratively due to troubleshooting or maintenance actions as this
information might be part of the agreement between Deployer and End User.

Deployer wants to measure the time certain nova services was forced down due
to an externally detected error as this information might be part of the
agreement between Deployer and End User.

Proposed change
===============

An easy solution for the problem above is to add oslo.messaging notification
for the following actions:

* /v2/{tenant_id}/os-services/disable

* /v2/{tenant_id}/os-services/enable

* /v2/{tenant_id}/os-services/disable-log-reason

* /v2/{tenant_id}/os-service/force-down

Then ceilometer can receive these notifications and the length of the
maintenance window can be calculated via ceilometer queries.

Alternatively other third party tools like StackTach can receive the new
notifications via AMQP.


Alternatives
------------

The only alternative is to poll /v2/{tenant_id}/os-services/ API periodically
however it means slower information flow and creates load on the nova API
and DB services.

Data model impact
-----------------
No database schema change is foreseen.

The following new objects will be added to nova:

.. code-block:: python

    @base.NovaObjectRegistry.register
    class ServiceStatusNotification(notification.NotificationBase):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('ServiceStatusPayload')
        }

    @base.NovaObjectRegistry.register
    class ServiceStatusPayload(base.NovaObject):
        # Version 1.0: Initial version
        VERSION = '1.0'
        fields = {
            'service': fields.ObjectField('Service')
        }

The definition of NotificationBase can be found in the Versioned notification
spec [3].

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------
A new notification service.status.update will be introduced with INFO priority
and the payload of the notification will be the serialized form of the already
existing Service versioned object. This notification will be the first that
uses versioned object as a payload but there is an initiative to
use versioned objects as notification payload for every nova notification [3].
This  new notification will not support emitting legacy format.

During the implementation of this spec we will provide the minimum
infrastructure to emit versioned notification based on [3] but all the advanced
things like sample and doc generation will be done during the implementation
[3].

For example after the following API call::

    PUT /v2/{tenant_id}/os-services/disable-log-reason
        {"host": "Devstack",
         "binary": "nova-compute",
         "disabled_reason": "my reason"}


The notification would contain the following payload::

       {
            "nova_object.version":"1.0",
            "nova_object.name":"ServiceStatusPayload",
            "nova_object.namespace":"nova",
            "nova_object.data":{
                "service":{
                    "nova_object.version":"1.19",
                    "nova_object.name":"Service",
                    "nova_object.namespace":"nova",
                    "nova_object.data":{
                        "id": 1,
                        "host": "Devstack"
                        "binary": "nova-compute",
                        "topic": "compute",
                        "report_count": 32011,
                        "disabled": true,
                        "disabled_reason": "my reason,
                        "availability_zone": "nova",
                        "last_seen_up": "2015-10-15 07:29:13",
                        "forced_down": false,
                        "version": 2,
                        }
                    "nova_object.changes":[
                        "disabled",
                        "disabled_reason",
                        ]
                }
            }
       }

Please note that the compute_node field will not be serialized into the
notification payload as that will bring in a lot of additional data not needed
here.

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
  balazs-gibizer


Work Items
----------

* Send a new notification if the disabled disabled_reson or forced_down field
  of the Service object is updated


Dependencies
============
This work is part of the Versioned notification API [3] work. But it is not
directly depends on it. On the summit we agreed to add this new notification as
the first step of the versioned notification api work to serve us as a carrot
motivating the operators to start consuming new versioned notifications.

Testing
=======
Besides unit test new functional test cases will be added to cover the
new notification


Documentation Impact
====================
None


References
==========

[1] This idea has already been discussed on ML
    http://lists.openstack.org/pipermail/openstack-dev/2015-April/060645.html

[2] This work is related to but not depends on the bp mark-host-down
    https://blueprints.launchpad.net/nova/+spec/mark-host-down

[3] Versioned notification spec https://review.openstack.org/#/c/224755/


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
