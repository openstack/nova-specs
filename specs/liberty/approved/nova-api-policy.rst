..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================================
Policy should be enforced at API REST layer where possible (Final Part)
=======================================================================

https://blueprints.launchpad.net/nova/+spec/nova-api-policy-final-part

NOTE: This spec follow up the rest work of nova api policy blueprint:
https://blueprints.launchpad.net/nova/+spec/v3-api-policy , In the Kilo
The v2.1 policy improvement already finshed, but only finished part of db
policy improvement and rest of those works will be continue in Liberty.
The detail is described at 'Work Items' section.

This BP proposes enforcing all policy checks only at the Nova REST API
layer. The extra permission checks at the lower layers of Nova will be
removed. There will be consistent policy naming for the V2.1 API and
backwards compatibility will be retained for existing policy checks
related to the V2 API so that the policy checks remain effectively the
same, even though they may in practice be implemented at different points.

This BP is already discussed at Icehouse summit:
https://etherpad.openstack.org/p/icehouse-summit-nova-v3-api

Problem description
===================

Currently policy permission checking is spread through the various
levels of the Nova code.  There are also duplicated checks where
effectively the same sort of policy check under different names is
done at different levels such as both at the Nova REST API layer
and the Nova Compute API layer. In addition to this there are also
some cases where there are hard coded permission checks in the db
layer.

This situation makes it much harder for operators to correctly
configure the policy settings that they want and because of the multi
layered complexity of permission the implementation itself is more
vulnerable to security bugs.

A detailed description of the problem:

* Permission checking spread in different level of nova code
  Example:

  * REST API layer: pause server "compute_extension:admin_actions:pause"
  * Compute API layer: pause in compute API "compute:pause"
  * DB layer: require_admin_context decorator for db API service_get

* Duplicated policy checking for same API. Example:

  * For server's pause action:
  * REST API layer:
        "compute_extension:admin_actions:pause": "rule:admin_or_owner"
  * Compute API layer: "compute:pause": ""

* Hard code policy check at db layer
  Example:

::

    @require_admin_context
    def service_get_all(context, disabled=None):
        query = model_query(context, models.Service)

        if disabled is not None:
            query = query.filter_by(disabled=disabled)

        return query.all()

  This means it won't have any effect after you modify the policy at REST
  API layer, it always enforced as admin at db layer.

Use Cases
---------

1. Operator want to specified role can access service API, but it's hard-code
as only admin can operator those API.

2. As developer view, Only one rule for pause server API at REST API layer.
Developer needn't be confused how to process permission checks in the nova.

Project Priority
----------------

None

Proposed change
===============

Enforce policy at REST API layer. Because REST API will access
different internal APIs, like compute API, DB API or other internal API, the
REST API layer is the place to enforce policy consistently.

* Remove policy check from compute API layer for EC2 and Nova V2.1 API

  * For V2.1 API, there will only be policy checks in the nova REST API
    layer. There will be a parameter 'skip_policy_check' for compute API to
    control whether doing the policy checks. For V2.1 API,
    skip_policy_check will be True.

    https://review.openstack.org/#/c/100408/2/nova/api/openstack/compute/plugins/v3/shelve.py

  * For Ec2, we want to keep the backwards-compatibility. Also we want to
    move the compute API layer policy checking into REST API layer, the same
    as V2.1 API. That means the old policy and new policy will be available
    at sametime. At least after one release, we can remove the old polcy.

  * For V2 API, we want to keep the backwards-compatibility. So we won't move
    the compute API layer policy checking into REST API layer. We will set
    compute API's parameter skip_policy_check to False, that means still
    doing policy checking at compute API layer. It's because V2 API will be
    depreciated. Before V2 API removed, we needn't take risk of breaking
    existing code.

    https://review.openstack.org/#/c/100408/2/nova/compute/api.py

* Remove hard-code permission check from db layer

  * Example: https://review.openstack.org/#/c/73490/
  * For the v2.1 API, we remove all the hard-code permission check from DB
    layer. And we should ensure we have policy check at REST API layer.
  * For the v2 API, we remove all the hard-code permission check from DB
    layer, and move the hard-code permission checks into REST API layer to
    keep back-compatibility. V2 API will removed once V2.1 ready, this
    can reduce the risk we break something existed.
  * Update policy configuration file to match the existing behavior for
    EC2 and V2.1 API.

* Correct the policy rule name specification for the v2.1 api and ec2 api

  The policy naming style as below:
    For V2.1: api:[extension_alias]:[action]
    For ec2: ec2_api:[action]

  * We won't use 'compute' and 'compute_extension' to distingish the core and
    extension API. Because the core API may be changed in the future.
  * We also remove the API verison from the policy rule. Because after we have
    Micro-version, the version will be changed often.

* For volume related extensions, there isn't any thing can do, there already
  have policy checks at REST API layer, also have policy checks by cinder.

* For network related extensions, we are doing same change like compute API.

  For nova-network, move all the policy enforcement into REST API layer from
  network API, and remove the db layer hard-code permission checks.

  For neutron, we didn't have too much can do, neutron has its own policy
  enforcement. We just need ensure we have policy enforcement at nova REST
  API layer.

Alternatives
------------
The alternative is the status quo which is confusing for both deployers as
well as developers having to maintain the current implementation

Data model impact
-----------------
None

REST API impact
---------------
None

Security impact
---------------
This BP will remove the policy permission checks in the compute API layer
and DB layer.

These patches will require very rigorous double checking and high
quality reviews to ensure that security bugs are not introduced as the
nova internal calls can be called from quite a few different code
paths (Ec2, V2 API, V2.1 API and other internals).

Notifications impact
--------------------
None

Other end user impact
---------------------
None

Performance Impact
------------------
This BP will improve the error handling performance. Because the permission
checking occurs at the API level rather than at a lower level in Nova less
processing will occur before a request is rejected. Also potentially for newer
versions of the API redundant policy checks are removed which will also
improve performance.

Other deployer impact
---------------------

Every effort will be made to keep all existing policy permission
settings backwards compatible for v2 API, except the db hard-code permission
checks. Because v2 API will be removed once v2.1 API is ready.

As v2.1 API isn't ready yet, there isn't any user for v2.1 for now, so we
won't worry about any change will affect the user.

For EC2 API, we also want to keep backwards compatibility, just like v2 API.
The old policy rules will be keep at least for one release. If the user
just want to use the old policy, user can set all the new policy to empty.
Then all the policy will be skipped. If user want to use new policy, just
set the rule into new policy, then new policy will be enforced before old
policy.

The extension will be affect by remove db layer hard-code permission checks
as below:

* services
* certificates
* floating_ips
* floating_ips_bulk
* floating_ip_dns
* fixed_ips
* os-network
* network_associate
* quotas
* quota_classes
* security_group
* security_group_default_rule
* migrations
* flavor_manage
* flavor_access
* cell
* agent
* pci

For v2.1 and ec2 api, the policy rule name prefix is changed. So it need
Deployer update their policy config.

Developer impact
----------------

When a developer adds a new REST API for nova policy permission checks
will only be added at the REST API layer.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Alex Xu <hejie.xu@intel.com>

Other contributors:
  Eli Qiao <liyong.qiao@intel.com>
  ShaoHe Feng <shaohe.feng@intel.com>
  YunTong Jin <yuntong.jin@intel.com>
  Park Hei <heijlong@linux.vnet.ibm.com>
  jichenjc <jichenjc@cn.ibm.com>

Work Items
----------

The tasks with "(Done)" mean already done at Kilo. Other tasks will be
continue.

* Add parameter to compute and network API to skip policy checks. (Done)
* Improve the EC2 API policy enforcement. (Abandon because EC2 deprecated)

  * Add new policy rules at REST API layer
  * Add new EC2 API rules
  * Move EC2 API rules into separated file.
* Improve the V2.1 API policy enforcement. (Done)

  * Remove compute API and network API layer policy enforcement
  * Rename V2.1 API rules
  * Move V2.1 API rules into separated file.
* Remove db layer hard-code permission checks.
  The rest of part is most about nova-network and service/compute_nodes db
  calls.

  * Add back-compatibility rules into REST API layer for v2 API
  * Add policy rules at REST API layer instead of hard-code checks for v2.1
* Move V2 API policy out of policy.conf

Working list:
https://etherpad.openstack.org/p/apipolicycheck


Dependencies
============

None


Testing
=======

No tempest changes. All the policy checks tests will be test by unittest,
as this is mostly an internal nova blueprint.

Documentation Impact
====================
The db layer permission checks will be deleted, this should be document at
upgrade documentation.

All the policy should enforce at API layer, this should be document at
developer documentation.

For the consistent configuration of policy rule, this should be document at
Cloud Admin documentation.

References
==========

https://etherpad.openstack.org/p/icehouse-summit-nova-v3-api
