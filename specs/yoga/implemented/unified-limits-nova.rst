..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Unified Limits Integration in Nova
==================================

https://blueprints.launchpad.net/nova/+spec/unified-limits-nova

The spec is about adopting Keystone's unified-limits.
Includes using oslo.limit to enforce the Nova related limits set in Keystone.

This spec proposes having unified limits in parallel with the existing
quota system for at least one cycle, to allow for operators to transition
from setting quotas via Nova to setting limits relating to the Nova API
endpoint via Keystone.

All per user quota support is dropped, in favor of hierarchical
enforcement that will be supported by unified limits.

Only server count limits and limits on Resource Class resources requested in
the flavor will be supported with unified limits. All other existing quotas
will no longer support per project or per user limits.

Given this placement focused approach, we will depend on the work done here:
http://specs.openstack.org/openstack/nova-specs/specs/train/approved/count-quota-usage-from-placement.html

Problem description
===================

While much work has been done to simplify how quotas are implemented in
Nova, there are still some major usability issues for operators with
the current system:

* We don't have consistent support for limit/quota hierarchy across OpenStack
* Requiring operators to set limits individually in each service
  (i.e. Cinder, Nova, Neutron, etc)
* Nova's existing quotas don't work well with Ironic
* No support for custom Resource Class quotas (includes "per flavor" quotas)
* Confusion when API defined quota limits override any changes made to the
  configuration
* Some Nova quotas are unrelated to resource consumption, causing confusion

Transitioning to use Keystone's unified limits, via oslo.limit, will help fix
these issues.

For more details on unified limits in keystone see:
https://docs.openstack.org/keystone/stein/admin/identity-unified-limits.html

Use Cases
---------

The key use cases driving this work are:

* API User tries to understand why they got an Over Quota error
* Operator migrates to unified limits from existing limits
* Operator sets a default limit for a given endpoint via Keystone. Note there
  can be different limits for each Region, even with a shared Keystone.
* Operator sets specific limits for a given project via Keystone
* Operator defines limits of a set of projects via non-flat enforcement
  i.e. the feature formally known as hierarchical quotas

We will focus on adding unified limits relating to:

* total number of servers
* amounts of each Resource Class requested in the flavor

Note, this includes things like DISK_GB which is not supported today,
along with things like custom resource class resources that are requested
in extra specs (e.g. Ironic flavors).

We will now look at all quotas exposed via the API and what they map to
when using unifed limits:
https://docs.openstack.org/api-ref/compute/?expanded=show-a-quota-detail#show-a-quota

The follow existing quota types move to unified limits, allowing for
per endpoint defaults and per project overrides (and hierarchical limits)
via the unified limits system:

* ``cores`` -> ``class:VCPU``
* ``instances`` -> ``servers``
* ``ram`` -> ``class:MEMORY_MB``

The following existing quota becomes defined only by registered (default)
limits in the unified limits system, and we no longer support and per project
or user overrides via the API, we just report the existing limit as defined in
Keystone.

* ``key_pairs`` (counted per user) -> ``server_key_pairs``
* ``server_groups`` (counted per project)
* ``server_group_members`` (counted per server group)
* ``metadata_items`` (counted per server) -> ``server_metadata_items``

The above are purely protecting database bloat (i.e to stop a denial
of service attack that fills up the database). They are similar to the
hardcoded limit of the number of tags you can attach to a server.

While deprecated in the API, we will also treat these quotas in the
same way as the quotas above, i.e. they will now be set via
registered limits with no per project overrides possible:

* ``injected_file_content_bytes`` -> ``server_injected_file_content_bytes``
* ``injected_file_path_length`` -> ``server_injected_file_path_bytes``
* ``injected_files`` -> ``server_injected_files``

Proposed change
===============

There are several parts to this spec:

* Enforce Unified Limits
* No per-user limits
* No uncountable limits
* Deprecate Nova's Quota APIs
* Operator tooling to assist with the migration

Enforcing Unified Limits
------------------------

We will support the following limits:

* ``servers``
* ``class:<RESOURCE_CLASS>``
* ``server_group_members``
* ``server_groups``
* ``server_injected_files``
* ``server_injected_file_content_bytes``
* ``server_injected_file_path_bytes``
* ``server_key_pairs``
* ``server_metadata_items``

All the resource class usage will be counted using placement, but
server count will make use of instance mappings. This only works if the
queued for delete data migration has been completed. Due to no user
based quotas, we don't need the ``user_id`` migration. If the operator
tries to use unified limits before completing the migration, the code
will block all new usage until the migration is completed. It is
expected a blocking migration will be added before we turn on unified
limits by default. For more details on the this data migration see
this point in the existing quota code:
https://github.com/openstack/nova/blob/0d3aeb0287a0619695c9b9e17c2dec49099876a5/nova/quota.py#L1053

To allow the new system to co-exist with the older quota system, we make
use of the existing quota driver sytem. The default will be unchanged,
but operators can opt-into the new system in the following way:

* ``[quota]driver=nova.quota.UnifiedLimitsDriver``

For further details on the transition, please see the update section of this
specification. Note the new unified limits code will have a hard dependency
on counting usage via placement; as such it will ignore the value of
``CONF.quota.count_usage_from_placement``.

Looking at the existing quotas, `instances` becomes `servers`,
`cores` becomes `class:VCPU` and `ram` becomes `class:MEMORY_MB`.

This work will re-use a lot of the new logic to query placement for resource
usage, and use the instance mapping table to count servers added in this spec:
http://specs.openstack.org/openstack/nova-specs/specs/train/approved/count-quota-usage-from-placement.html

To find out what resources a server will claim, we reuse this
code to extract the resources from any given flavor:
https://github.com/openstack/nova/blob/2e85453879533af0b4d0e1178797d26f026a9423/nova/scheduler/utils.py#L387

For server build, we use the above function to get the Resource Class
resource amounts for the requested flavor. This will then be checked using
olso.limit, which ensures the additional usage will not push the associated
project over any of its limits. The oslo.limit library is responsible for
counting all the current resource usage using a callback we provide that makes
use of placement to count the current resource usage.

Once resources are claimed in placement, we optionally recheck the limits
to see if we were racing with other server builds to consume the last bits
of available quota. The only change is using oslo.limit to do the recheck.
That is, we will still respect the config: `quota.recheck_quota`
Note: we do the first check of limits in nova-api, and the recheck in
nova-conductor after resource allocation in placement succeeds.

It is a similar story with resize. Except in this case, we check that we can
claim resources for both the new flavor and old flavor at the same time.
Note that this is quite different to the current quota system, even when
counting usage via placement.

For further details on the semantic changes relating to counting with
placement see:
http://specs.openstack.org/openstack/nova-specs/specs/train/approved/count-quota-usage-from-placement.html

Note baremetal instances no longer claim any VCPU or MEMORY_MB resources.
With this method, baremetal instances can be limited using custom
resource class resources they request in the flavor.

Should we choose to allow additional custom inventory entries
from hypervisor based compute nodes, such as `{'CUSTOM_GPU_V100':1}`
we will be also be able to apply quotas on these resources.

The oslo.limits library will likely add additional configuration options.
In particular, operators will need to specify the Nova API's endpoint uuid
to oslo.limit, so it knows what unified limits apply to each particular
Nova API service.

No per user limits
------------------

Nova currently supports "per user" limits. They will no longer be supported
when: ``[quota]driver=nova.quota.UnifiedLimitsDriver``

There are no plans for migration tools, however it is expected that users
that need a similar model can test out using the unified limits support for
hierarchical limits, and report back on what could help others migrate.

Note: Keypairs will still have a max limit enforced, and that max limit
will still be enforced per user. However, there will now only be a single
default registered limit value in Keystone to set the max number of keypairs
each user is allowed.

No uncountable limits
---------------------

As stated above, the focus for unified limits is the instance count and
resource class allocations in placement. No other limits will be moved to
unified limits, as agreed with operators in the Train Forum session.

There are limits that are specific to nova-network. These are all ready
deprecated. There are no plans to support these with unified limits turned on:

* ``fixed_ips``
* ``floating_ip``
* ``security_group_rules``
* ``networks``

The remaining limits are all mainly used to protect the database from rogue
users using up all available space in the database and/or missuse the API as
some sort of storage system. As such, it is not expected that operators need
per project overrides for any of these limits.

The following limits will be changed to only be set via registered limits in
the unified limits system that applies equally to all projects:

* ``server metadata_items``
* ``server_injected_files``
* ``server_injected_file_content_bytes``
* ``server_injected_file_path_bytes``
* ``server_key_pairs`` (counted per user)
* ``server_groups`` (counted per project)
* ``server_group_members`` (counted per server group)

Note that the server_group_members are currently counted per user, but this
is frankly very confusing, so above we propose the simpler limit servers
in the server group. This seems consistent with removing per user limits for
all other project owned resources.

Using registered limits only means:

* no per project overrides
* no per user overrides

These are limits on the amount of data that can be stored in various
Nova databases. There is no way to display a project's usage of these limits,
which further demonstrates how these are different to the resource limits
unified limits has been designed for.

Currently we honor ``quota.recheck_quota`` for all of these quotas. This adds
significant code complexity, however most users never hit these limits and
they are all very soft limits. As such, when we transition to a single default
registered limit value for all of these, we also will stop doing any rechecks.

In summary the impact on the configuration options is:

* ``quota.recheck_quota`` will have an updated description, noting what
  functionality is lost when ``[quota]driver=nova.quota.UnifiedLimitsDriver``
* ``quota.floating_ips``, ``quota.fixed_ips``, ``quota.security_groups``,
  ``security_group_rules``: remain deprecated, and will be ignored when
  ``[quota]driver=nova.quota.UnifiedLimitsDriver``.
* ``quota.metadata_items``, ``quota.injected_files``,
  ``quota.injected_file_content_bytes``, ``quota.injected_file_path_length``,
  ``quota.server_groups``, ``quota.server_groups_members``,
  ``quota.key_pairs``:  these will all be kept, but the description will be
  updated to note if ``[quota]driver=nova.quota.UnifiedLimitsDriver`` all
  updates via the API are ignored.

Deprecate Nova's Quota APIs
---------------------------

To query and set limits, Keystones APIs should be used. To query a user's
usage, the Placement API should be used, assuming placement is happy
changing the default policy to allow users to query their usage.

The one exception is server count can't currently be checked via
Placement. When placement implements consumer records,
or similar, then all usage could be queried via Placement. To avoid
using a proxy API, users can do a server list API and count the number
of servers returned.

When ``[quota]driver=nova.quota.UnifiedLimitsDriver`` a best effort will be
made to keep the older micro-versions working by proxing API calls to Keystone
and Placement as needed. No quota related DB tables will be accessed when
``[quota]driver=nova.quota.UnifiedLimitsDriver``.

This includes the follow API resources:

* /limits
* /os-quota-sets
* /os-quota-class-sets

Existing tooling to set quotas should continue to operate, as long as it only
changes quotas relating to instances, cores and ram. Requests to change any
other quotas will be silently ignored. As one example, this should allow
Horizon to function as normal during the transition.

There are some trade-offs with this approach:

* Proxy APIs suck, but horizon must keep working as such all current operator
  tooling around these existing APIs.
* We don't need a micro version to enable/disable this proxy
  of the quota APIs, as it doesn't really change the API.
* In a future release when unifed limits becomes the default,
  we should deprecate the APIs
  ``/os-quota-sets`` and ``/os-quota-class-sets`` and tell users to talk to
  the Keystone API instead. API based discovery of when Nova is enforcing
  the limits set in Keystone is left for a future spec.
* It is expected the above API deprecation will follow the pattern used
  by nova-network proxy APIs, i.e. the APIs return 404 in new microversions
  but continue to work in older microversions. Its possible in the more
  distant future the APIs could be removed by returning 410 error.
* Rejecting updates to quotas that we were previously able to set would be a
  breaking change in behaviour, and require a microversion. Adding a new API
  microversion that returns BadRequest for unsupported quotas would be a nice
  addition if we were not planning on deprecating the API in favor of calling
  Keystone instead.
* Ideally we would also deprecate ``/limits`` in favor of a cross project
  agreed direction that is aware of both flat and hierarchical limit
  enforcement. Howerver we do not yet have consenus on what direction
  we take. For this spec, we leave ``/limits`` in its current form, even
  though it does not report on all the types of resource usage we now
  support have limits on, and even though it lists limits that can
  now only be changed via registered unified limits in Keystone.
* When hierarchical limits are added, the per project usage information
  in ``/limits`` does not mention anything about parent limits.
  As such quota APIs may claim resources are available, but you will be
  unable to build any new resources.
  It is not clear what action the user can make to be able to build those new
  resources. Operators can avoid this confusion by not over allocating quota.
  We could extext the API to include a boolean to say if the limit has been
  exceeded in the parent project, and as such the user is unable to consume
  more resources even though their own usage is not over their own limits.
  We could consider extending the API to include the usage of the full tree

Migration to Unified Limits
---------------------------

The migration of all users to unified limits is happening in three phases:

* enable unified limits as an option, with migration path from existing quotas
* make unified limits the default, deprecate existing quota system
* remove existing quota system

To help with the transition we need operator tooling to:

* Set registered limits in Keystone for each Nova endpoint in Keystone,
  based on current limits in DB and/or configuration
* Copy per-project quotas set in Nova into Keystone unified-limits
* Operator confirms unified limits works for them
* Drop all quota info from the DB to signal operator has completed transition
* Upgrade status check to check there is no data left in quota DB tables

Note the setting of project limits and registered limits in keystone will
happen via files that are generated and passed to keystone-manage. This
allows fast-forward upgrades where no API are available during the migration
of limits from Nova to Keystone.

There will be a new tool to setup the registered limits in keystone. It will
read from the Nova DB and configuration and generate a file. That file can be
by used with keystone-manage to register the current endpoint defaults in
keystone.::

  nova-manage limits generate_registered_limits --endpoint <endpoint-uuid>

The following tool will generate the unified limits overrides (if any)
that needs to be added into Keystone for each project. Again this too
produces a file that is handed to keystone-manage which will update keystone::

  nova-manage limits generate_project_limits [--project_id <project_id>]

Once the operator sets ``[quota]driver=nova.quota.UnifiedLimitsDriver``, the
Nova DB is ignored, and limits are accessed from Keystone only.

To complete the migration, there is an operation to remove all the DB entries
relating to the quota overrides. The tool only works when
``[quota]driver=nova.quota.UnifiedLimitsDriver``. It also removes all any per
user limits associated with each project.::

  nova-manage limits remove_db_quota_entries [--project_id project_id]

Note the last two tools allow operators to iterate per project, to limit the
load on the running system. If these tools are used on a running system, it is
recommended that operators don't change quotas via the API during the
transition.

The nova status command will warn users that have failed to remove all the
quota information from the DB. This will become an error in the release when
``[quota]driver`` defaults to ``nova.quota.UnifiedLimitsDriver``.

It is worth noting that the Nova database may contain entries for projects
that have been deleted in keystone. As such, it is advisable to get a list
of active projects from keystone, and only generate_project_limits for those
particular projects.

This transition leaves several configuration options redundant, in particular
the following will all be deprecated once unified limits is on by default:

* ``quota.instances``, ``quota.cores``, ``quota.ram``: deprecate all these as
  the limit now comes from keystone for unified limits, which will default to
  unlimited if there is no limit in keystone.

The setting ``quota.recheck_quota`` will be kept, and will be used in the same
way with unified limits to avoid races when multiple instances are built at
the same time.

Alternatives
------------

Ideally we would not add any more proxy APIs, however, operators pushed back
at the Train Forum session, requesting that their tooling continue to work
across the transition. No operators reported using limits other than the
instances, cores and ram limits.

We could implement hierarchical quotas in isolation, and not adopt unified
limits.

We could limit the types of resources we limit, but it will be hard to
transition to supporting different kinds of resource limits in a clear
and interoperable way.

Data model impact
-----------------

See upgrades, no changes in Victora due to having old and new quota systems
side by side. Once we remove the old quota system, we could drop all the
quota related DB tables.

REST API impact
---------------

When ``[quota]driver=nova.quota.UnifiedLimitsDriver`` Nova will proxy the
requests to Keystone's unified limits API, where possible. The aim will be to
keep horizon functioning correctly during the transition.

Once using unified limits, operators should move to using Keystone's
unified limit APIs to set and query limits. Usage information should be
queried via Placement and the Servers API.

Security impact
---------------

The removal of quota rechecks for some limits slightly reduces the protection
provided, but really it encourages the proper implementation of API
rate limiting as replacement protection.

Notifications impact
--------------------

None

Other end user impact
---------------------

Quota errors with unified limits will use the standard and consistent error
messages from oslo.limit after this change.

Performance Impact
------------------

It is possible to have more complicated quota counts with hierarchical
quotas, but the implementation of that is delegated to oslo.limit.

Other deployer impact
---------------------

There are several tools to help ease the transition to unified limits noted
above. Although it is expected that use of the feature will help inform the
end direction.

Developer impact
----------------

There will now be two limit system to maintain for a few cycles during the
transition. But this avoids the long term need to maintain complicated
hierarchical limit code, which still getting the advantages, such as being able
to tidy up API policy.

Upgrade impact
--------------

To get the best experience, operators need to start using the unified limits
API via Keystone. Users should start querying usage from Placement.

The transition between the existing quota system and unified limits is
detailed in the proposed solution section.

It is expected that oslo.limit will limit versions of Keystone that can be
used to Queens and newer, which is not expected to affect most users.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johnthetubaguy

Other contributors:
  melwitt

Feature Liaison
---------------

Feature liaison:
  melwitt

Work Items
----------

* Add calls to oslo_limits, guarded by config to enable it
* Move quota APIs to proxy to Keystone when unified limit quotas enabled
* Add tools to migrate default and tenant limits from Nova into Keystone
* Upgrade checks to ensure above tooling is used

Dependencies
============

* http://specs.openstack.org/openstack/nova-specs/specs/train/approved/count-quota-usage-from-placement.html
* keystone manage commands to add limits when keystone API not available

Testing
=======

Grenade test that runs the migration of quota settings (after adding some
quotas).

Functional tests to ensure quotas are enforced based on unified limits
correctly.

Documentation Impact
====================

Building on the work to document quota usage from placement, we should
describe how the new system operates. The admin guide needs to detail
how to smoothly migrate to unified limits.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
   * - Victoria
     - Reproposed
   * - Xena
     - Reproposed
   * - Yoga
     - Reproposed
