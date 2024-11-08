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

* As an admin/operator, I would like to be able to control which resources I
  will require to have a limit set. And I would also like to be able to control
  which resources I do not need any limit set, by not including them in the
  required resources list.

* As an admin/operator, I would like to be able to see a DEBUG log message if I
  have missed setting a registered limit for a resource in Keystone, rather
  than to have all API requests involving that resource be rejected for being
  over quota.

Proposed change
===============

The proposal in this spec is to add new configuration option(s) to the
``[quota]`` group which would enable operators to:

* Require limit enforcement for only specific resources, or

* Require limit enforcement for all resources except specific resources

The goal with the options is to make management of unset unified limits easy
and maintainable over time.

Alternatives
------------

Alternatively we could make a change to the oslo.limit library to handle
missing registered limits differently than it does today `[1]`_. This would be
more difficult because oslo.limit 1) has established and thus expected default
behavior and 2) providing new behavior that fits all OpenStack projects may not
be realistic.

A previously proposed alternative would be a boolean config option
``[quota]strict_unified_limits`` which has only two modes: consider unset
limits as zero or consider unset limits as unlimited `[2]`_. Discussion at the
last PTG raised concerns that a boolean option is likely too generic and
wouldn't provide the level of control most operators would need.

.. _[1]: https://review.opendev.org/c/openstack/oslo.limit/+/899415
.. _[2]: https://review.opendev.org/c/openstack/nova-specs/+/923807/3/specs/2024.2/approved/unified-limits-nova-unset-limits.rst

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

If a resource is not configured to require limit enforcement, that resource
would be considered to have unlimited quota and malicious callers could attempt
to exhaust that resource intentionally.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The performance impact of using new config options to handle unset limits
should be relatively small as it will add one extra Keystone API call each time
1) a quota check fails and 2) the limit for the associated resource is returned
as 0 by oslo.limit.

Other deployer impact
---------------------

Admin/operators will need to consider if and when they will need to adjust
configuration values if new Placement resource classes are added to their
deployment in the future.

Also as part of this work, the ``nova-manage limits migrate_to_unified_limits``
CLI command will be enhanced to scan the database for resources in flavors that
do not have registered limits set and show them in the output. The intent is to
help admins/operators catch all resources and set limits for them before
unified limits quotas are enabled.

Developer impact
----------------

None

Upgrade impact
--------------

There should not be upgrade impact with the new configuration options.

For a deployer not running with
``[quota]driver = nova.quota.UnifiedLimitsDriver``, the config options have no
effect.

For a deployer already running with
``[quota]driver = nova.quota.UnifiedLimitsDriver``, they will have had to set
registered limits for all resources allocated by their cloud (because the
current behavior is to default all limits to zero) and should not experience
any change in quota enforcement for those resources.

After upgrading however, any _new_ resource the deployer adds to the cloud will
either default to unlimited quota or default to zero quota until the deployer
sets a registered limit for it in Keystone, depending on how the deployer has
configured the new options. If the deployer needs to update config option
values, they need to update them for the ``nova-api`` and ``nova-conductor``
services. Quota "rechecks" are performed by the ``nova-conductor`` service if
``[quota]recheck_quota = True`` (the default).

For a deployer switching to the
``[quota]driver = nova.quota.UnifiedLimitsDriver`` during the upgrade, the
default behavior will only require limits for the default resources in the
config options (currently proposed as ``servers``).

It is recommended for these deployers to first use the ``nova-manage limits
migrate_to_unified_limits`` tool to have it read their legacy quota limits from
the Nova database and ``[quota]`` config options and set them in
Keystone automatically. The output of the command will also show what
resources, if any, are found to be used in the deployment but do not have
registered limits set in Keystone. Deployers can use this information to know
what resources they need to set limits for in Keystone.

Then, deployers should add or remove resources from the list based on the
resources they want to require to enforce quota. All other resources will be
considered to have unlimited quota until the deployer sets registered limits
for them in Keystone.

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

* Add configuration options to control which resources to require a registered
  limit set in Keystone

* Augment the ``nova-manage limits migrate_to_unified_limits`` command to scan
  database flavors to detect resources that do not have registered limits set
  and show them in the output to the user to let them know which limits they
  need to set

Dependencies
============

* Related to https://specs.openstack.org/openstack/nova-specs/specs/yoga/implemented/unified-limits-nova.html

Testing
=======

The functionality of the new config options will be tested by writing new
functional tests. Adding testing to the post test hook for the ``nova-next`` CI
job is also a possibility.

Documentation Impact
====================

The `unified limits documentation`_ will be updated to include information
about the new config options.

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
   * - 2025.1 Epoxy
     - Re-proposed with changes
