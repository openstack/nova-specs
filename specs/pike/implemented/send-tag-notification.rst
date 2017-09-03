..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Notifications on tags operations
================================

https://blueprints.launchpad.net/nova/+spec/send-tag-notification

Nova currently does not send notifications on tag create/update/delete
operations.

Tags are designed to be used for searching and filtering, without
up-to-date tag information, services like OpenStack Searchlight will
not be able to work effectively and correctly.

It would be useful to send out create, update and delete notifications on
any of instance tags information changing.

Problem description
===================

Use Cases
---------

An external system like Searchlight[1] wants to index the instance tags
which makes the query for large number of instances using instance tags
faster, efficient and accurate. This will allow powerful querying as well
unified search across openstack resources.

The maintainer wants to get the notifications when there are tags added to,
updated or destroyed from instances.

Proposed change
===============

Tags fields will be added to InstancePayload for instance.update
versioned notification in:
https://blueprints.launchpad.net/nova/+spec/additional-notification-fields-for-searchlight

This blueprint will then send out instance.update notifications for
the following actions:

* PUT /servers/{server_id}/tags/{tag}
* PUT /servers/{server_id}/tags
* DELETE servers/{server_id}/tags/{tag}
* DELETE /servers/{server_id}/tags

Alternatives
------------

Tags notification with the payload including resource_id can be send
for tags.create/update/delete actions as an alternative. Since
tags.resource_id field is free-form:
https://github.com/openstack/nova/blob/edf51119fa59ff8a3337abb9107a06fa33d3c68f/nova/db/sqlalchemy/models.py#L1466
then it's up to the notification receiver to have to correlate what the
resource_id is pointing to.


Data model impact
-----------------

Notification payload object changes will be depend on [2].


REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------

Instance.update notifications for tags different actions will be emitted
to an amqp topic called 'versioned_notifications'.

Other end user impact
---------------------
None

Performance Impact
------------------

Notifications will be emitted if the versioned notification is enabled.
Every server tag manipulating API call loads the related instance from
the db to check if it is in a valid state [3]. So the notification payload
generation in this case can be designed to reuse that already loaded
instance object. This way the notification send only adds load to the
db due to lazy loading some of the instance fields that are not loaded
by default. However that can be again avoided in this case if we load
the instance in the API with proper expected_attrs.

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
  Kevin Zheng

Work Items
----------

* Send out instance.update notifications when instance tags change.

Dependencies
============

[2] https://blueprints.launchpad.net/nova/+spec/additional-notification-fields-for-searchlight
[3] https://github.com/openstack/nova/blob/edf51119fa59ff8a3337abb9107a06fa33d3c68f/nova/api/openstack/compute/server_tags.py#L54

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

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
