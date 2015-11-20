..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Make os-instance-actions read deleted instances
===============================================

https://blueprints.launchpad.net/nova/+spec/os-instance-actions-read-deleted-instances

Change the os-instance-actions API to read deleted instances so the owner can
see the actions performed on their deleted instance.


Problem description
===================

The os-instance-actions API currently does not read deleted instances [#f1]_.

Also, instance_actions are not soft deleted when an instance is deleted, so
we can still read them out of the DB without needing the read_deleted='yes'
flag.

The point of instance actions is auditing, and in the case of a post-mortem
when an instance is deleted, instance_actions would be used for this, but
because of the API limitation, you can't get those out of the API using the
deleted instance.

Use Cases
---------

#. Multiple users are in the same project/tenant.
#. User A deletes a shared instance.
#. User B wants to know what happened to it (or who deleted it).

User B should be able to lookup the instance actions on the instance since they
are in the same project as user A.

Proposed change
===============

Add a microversion change to the os-instance-actions API so that we mutate the
context and set the read_deleted='yes' attribute when looking up the instance
by uuid.

Alternatives
------------

* We can assume that operators are listening for nova notifications and storing
  those off for later lookup in the case that they need to determine who
  deleted an instance. This is not a great assumption since it relies on an
  external monitoring system being setup outside of nova, which is optional.

* Operators can query the database directly to get the instance actions for a
  deleted instance, but then they have to know the nova data model. And only
  operators can do that, it doesn't allow for tenant users to do this lookup
  themselves (so they'd have to open a support ticket to the operator to do
  the lookup for them).

Data model impact
-----------------

None.

REST API impact
---------------

Impacted API: os-instance-actions

Impacted methods: GET

The os-instance-actions API only has two GET requests:

#. index: list the instance actions by instance uuid
#. show: show details on an instance action by instance uuid and request id
         including, if authorized, the related instance action events.

The request and response values do not change in the API. The expected response
codes do not change - there is still a 404 returned if the instance or instance
action is not found.

The only change is that when looking up the instance, we set the
read_deleted='yes' flag on the context. This will be done within a conditional
block based on the microversion in the request.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

We can bump the max support API version in python-novaclient automatically for
this change since it's self-contained in the server side API code, the client
does not have to do anything except opt into the microversion.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem@us.ibm.com>

Other contributors:
  None

Work Items
----------

* If the microversion in the request satisfies the minimum version required,
  temporarily mutate the context when reading the instance by uuid from the
  database. For example:

  ::

   with utils.temporary_mutation(context, read_deleted='yes'):
       instance = common.get_instance(self.compute_api, context, server_id)


Dependencies
============

None.


Testing
=======

#. Unit tests will be updated.
#. Functional tests (API sample tests) will be provided for the microversion
   change. The scenarios are basically:

   * Delete an instance and try to get it's instance actions where the
     microversion requested does not meet the minimum requirement and assert
     that nothing is returned.
   * Delete an instance and try to get it's instance actions where the
     microversion requested does meet the minimum requirement and assert that
     the related instance actions are returned.


Documentation Impact
====================

* http://docs.openstack.org/developer/nova/api_microversion_history.html will
  be updated.
* http://developer.openstack.org/api-ref-compute-v2.1.html will be updated to
  point out the microversion change.

References
==========

* Mailing list: http://lists.openstack.org/pipermail/openstack-dev/2015-November/080039.html

.. [#f1] API: https://github.com/openstack/nova/blob/12.0.0/nova/api/openstack/compute/instance_actions.py#L56


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
