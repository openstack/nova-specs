..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
Add Policy Docs
===============

https://blueprints.launchpad.net/nova/+spec/policy-docs

Today operators need to read the code to work out what a policy rule actually
means. That is terrible, and this spec proposes we fix that by adding a
description for every policy rule.

Problem description
===================

Operators need to read the code to understand what a policy rule controls.

Use Cases
---------

* Operator wants to audit the default policy rules and see if they are
  appropriate for their deployment.

* Operator wants to give users access to a particular API that they currently
  get a 403 error when accessing.

* Operator wants to restrict access to an API a user currently has access to.

Proposed change
===============

We should fill in the description field for all of the policy rules in the
system. To help ensure the operator doesn't need to read the code to fully
understand the impact of each rule, we should ensure:

* All docs should use the names of entities described in the API docs:
  http://developer.openstack.org/api-ref/compute/

* We should state the URL of the API the policy rule affects, in the same
  format as it appears in the api-ref, i.e.: DELETE /servers/{server_id}

* We should ensure the docs are rendered well in the generated policy file,
  including ensuring all the rules are commented out by default:
  http://docs.openstack.org/developer/nova/sample_policy.html
  Note we already render the sample policy file in yaml.

For example, we might see something like this in the sample policy::

    # Show details of a specific server
    #
    # GET /servers/{server_id}
    #
    # "os_compute_api:servers:show": "rule:admin_or_owner"

    # Show real hostname of nova-compute managing the server
    #
    # Users normally only see an obfuscated hostname that is unique
    # to each project. If you pass this rule, we show the real hostname
    # so admins can find which host the server is on.
    #
    # GET /servers/details
    # GET /servers/{server_id}
    #
    # "os_compute_api:servers:show:host_status": "rule:admin_api"

    # Create a server
    #
    # POST /servers/{server_id}
    #
    # "os_compute_api:servers:create": "rule:admin_or_owner"

    # Create an image from a server
    #
    # POST /servers/{server_id}/action (createImage)
    #
    # "os_compute_api:servers:create_image": "rule:admin_or_owner"

    # List all host aggregates
    #
    # GET /os-aggregates
    #
    # "os_compute_api:os-aggregates:index": "rule:admin_api"

    # Delete a host aggregate
    #
    # DELETE /os-aggregates/{aggregate_id}
    #
    # "os_compute_api:os-aggregates:delete": "rule:admin_api"

As an example, we would update the policy definition from::

    policy.RuleDefault(SERVERS % 'show', RULE_AOO),

To something more like this::

    policy.DocumentedRuleDefault(SERVERS % "show", RULE_AOO,
        "Show details of a specific server",
        operations=[{"method": "GET", "path": "/servers/{server_id}"}])

Depending on how soon DocumentedRuleDefault is available, we may fake this
using a wrapper inside nova, so we can make progress before this is released.
oslo.policy > 1.20 now supports multi-line descriptions.

Alternatives
------------

We could try documentation separate to the code, but that has proven hard
to maintain and keep in sync with the code.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

A better understanding of what each rule means can only help operators and
developers get the policy configuration correct.

Notifications impact
--------------------

None

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

We must add a description when adding a policy rule. These are all
required arguments when creating DocumentedRuleDefault.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  John Garbutt (johnthetubaguy)

Other contributors:
  OSIC

Work Items
----------

* Add docs for each policy rule
* Ensure sample policy file renders correctly
* Add hacking check to prefer DocumentedRuleDefault over RuleDefault

Dependencies
============

Waiting on changes to oslo.polcy before we can call this finished.
Mostly we are waiting for this change:
https://review.openstack.org/#/c/439070/

Testing
=======

The documentation job generates the updated policy sample file.
That clearly shows which rules are left and how the updated rules look.

Documentation Impact
====================

We get a much improved sample policy file.

We should ensure this gets into the configuration guide for Nova.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced

