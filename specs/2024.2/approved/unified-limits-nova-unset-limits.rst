..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Config option to control behavior of unset unified limits
=========================================================

https://blueprints.launchpad.net/nova/+spec/unified-limits-nova-unset-limits

The default behavior in the oslo.limit quota enforcement library used by Nova
when ``[quota]driver`` is set to ``nova.quota.UnifiedLimitsDriver`` is to
consider resources that do not have registered limits set as having a limit of
zero. This behavior can be unforgiving especially in the scenario of an
upgrade that enables unified limits quota (i.e. if we ever want to make unified
limits the default). If we make the behavior configurable within Nova, we can
help prevent situations where an admin/operator upgrades or installs Nova and
suddenly all API requests begin to be rejected for being over quota.

Problem description
===================

The problem is centered around the behavior of the oslo.limit quota enforcement
library when a given resource does not have a registered limit set for it. If
no registered limit is found for a resource, the enforce function will consider
that resource to have a limit of 0 and all requests for the resource will fail
for being over quota.

We want to be able to change the default quota driver to the
UnifiedLimitsDriver, but the aforementioned behavior raises concerns about
changing the default.

If we were to make unified limits quotas the default in Nova, any
admin/operator who has missed auditing all of their resources and limits in
Keystone before upgrading could experience complete denial of service by the
Nova API immediately after the upgrade. This could happen if even one resource
is missing a registered limit set in Keystone.

While ideally an admin/operator will not miss setting any registered limits in
an upgrade scenario like this, the penalty for missing even one resource limit
is quite harsh as the API rejects all requests for that resource leading to an
immediate emergency situation.

Use Cases
---------

* As an admin/operator, I would like to be warned if I have missed setting a
  registered limit for a resource in Keystone rather than having all API
  requests involving that resource be rejected for being over quota

Proposed change
===============

The proposal in this spec is to add a new configuration option
``[quota]strict_unified_limits`` which defaults to ``True``. When set to
``True``, the Nova API will use the native oslo.limit behavior of considering
unset unified limits as zero. When set to ``False``, the Nova API will consider
unset unified limits as unlimited or "don't care". When set to ``True``, the
Nova API will use the native oslo.limit behavior of considering unset unified
limits as zero.

The only exception to ``[quota]strict_unified_limits = False`` is if there are
not registered limits set at all. `Registered limits`_ are default limits that
are global to the deployment and apply in any case that a project-specific
limit has not been set. If unified limits are enabled but no registered limits
have been set, all quota checks will fail and log a warning message about the
total absence of any limits set every time quota is enforced. The combination
of unified limits enabled but no unified limits set is considered to be an
error state and not something the admin/operator has intended. We could also
consider failing to start the nova-api and nova-conductor services if unified
limits are enabled but no limits are set.

The idea of the proposed config option is to give the admin/operator some
flexibility to resolve a situation where not all resources have registered
limits set without immediately rejecting API requests. Of course, there will be
the risk of potentially allowing allocation of more resources than would be
desired until the admin/operator either sets registered limits or disables
unified limits quotas. A warning will be logged every time quota is enforced
for resources without registered limits set because we don't want or expect
unset limits to be a permanent state. The admin/operator can stop the warning
logs by setting registered limits for the resources listed in the warning
message.

.. _Registered limits: https://docs.openstack.org/keystone/latest/admin/unified-limits.html#registered-limits

Alternatives
------------

Alternatively a change could be made to the oslo.limit library to handle
missing registered limits differently `[1]`_. This would be more difficult
because oslo.limit has established default behavior and providing new behavior
desirable for all projects may not be realistic.

.. _[1]: https://review.opendev.org/c/openstack/oslo.limit/+/899415

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

If ``[quota]strict_unified_limits`` is set to ``False``, resources could be
allocated beyond what the admin/operator would have intended during the window
of time between the logging of the warning and the admin/operator taking action
to either set registered limit(s) or disable unified limits quotas.

Notifications impact
--------------------

None

Other end user impact
---------------------

As part of this work, the ``nova-manage limits migrate_to_unified_limits`` CLI
command will be enhanced to scan the database for resources in flavors that do
not have registered limits set and show them in the output. The intent is to
help admins/operators catch all resources and set limits for them before
unified limits quotas are enabled.

Performance Impact
------------------

The performance impact of having ``[quota]strict_unified_limits`` set to
``False`` should be relatively small as it adds one extra Keystone API call
each time a quota check fails and the limit for the associated resource is 0.

Other deployer impact
---------------------

Admin/operators will need to be prepared and set
``[quota]strict_unified_limits`` to ``False`` _before_ upgrading Nova if they
wish to relax quota checks initially when enabling unified limits quotas.

Developer impact
----------------

None

Upgrade impact
--------------

The ``[quota]strict_unified_limits`` config option would only impact an upgrade
if the admin/operator sets it to ``True`` at the same time they enable unified
limits quotas by using the UnifiedLimitsDriver.

If a deployer decides to switch to the UnifiedLimitsDriver during their upgrade
and set ``[quota]strict_unified_limits`` to ``False`` before upgrading, there
is a possibility that resources could be allocated beyond what the deployer
would have intended until they take action on the logged warnings and set
registered limits for resources missing limits.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  melwitt

Work Items
----------

* Add a configuration option to control whether unset unified limits should be
  considered unlimited and logged as a warning

* Augment the ``nova-manage limits migrate_to_unified_limits`` command to scan
  database flavors to detect resources that do not have registered limits set
  and show them in the output to the user to let them know which limits they
  need to set

Dependencies
============

* Related to https://specs.openstack.org/openstack/nova-specs/specs/yoga/implemented/unified-limits-nova.html

Testing
=======

The functionality of the ``[quota]strict_unified_limits`` config option will be
tested by writing new functional tests.

Documentation Impact
====================

The `unified limits documentation`_ will be updated to include information
about the new config option.

.. _unified limits documentation: https://docs.openstack.org/nova/latest/admin/unified-limits.html

References
==========

* https://specs.openstack.org/openstack/nova-specs/specs/yoga/implemented/unified-limits-nova.html

* https://docs.openstack.org/nova/latest/admin/unified-limits.html

* https://docs.openstack.org/oslo.limit/latest/user/usage.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.2 Dalmatian
     - Introduced
