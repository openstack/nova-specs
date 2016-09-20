..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Policy in code
==========================================

https://blueprints.launchpad.net/nova/+spec/policy-in-code

For a while now there has been a desire to embed sane policy defaults in code
and allow for a policy file to override them. This would allow deployers to
only configure policies that they specifically want to override which could
reduce the size and complexity of those files. It would also allow for
generating a sample policy file which includes an exhaustive list of all
policies.


Problem description
===================

There are a few things being addressed here:

Given a deployed policy file it is not trivial to determine how much it
differs from the defaults that Nova expects. This is due to the provided sample
file not having an exhaustive list of all configurable policies, and the
expected defaults are not contained in the Nova codebase.

For new deployments comfortable with the defaults a policy file will no longer
be needed. This will help deployers stay current with defaults if they change
in the code. For deployers updating to this they should be able to clean up, or
eliminate, their policy files making them simpler to deal with.

Given an authenticated request context it is not possible to determine which
policies will pass. This is because policy checks are ad hoc throughout the
code with no central registry of all possible checks.

Use Cases
---------

As a deployer I would like to configure only policies that differ from the
default.


Proposed change
===============

The proposal is that any policy that should be checked in the code will be
registered with the policy.Enforcer object, similar to how configuration
registration is done. Any policy check within the code base will be converted
to use a new policy.Enforcer.authorize method to ensure that all checks are
defined. The authorize method has the same signature as
policy.Enforcer.enforce. Any attempt to use a policy that is not registered
will raise an exception.

Registration will require two pieces of data:

1. The rule name, e.g. "compute:get" or "os_compute_api:servers:index"
2. The rule, e.g. "rule:admin_or_owner" or "role:admin"

The rule name is needed for later lookups. The rule is necessary in order to
set the defaults and generate a sample file.

An optional description can also be provided. This will be available in a
sample policy file which can be generated from these registered rules. It
should be noted that the sample file will be generated as yaml, which
oslo.policy can now take as input.

As an example::

    nova/policy/create.py
    ---------------------

    from nova import policy

    server_policies = [
        policy.PolicyOpt("os_compute_api:servers:create",
                         "rule:admin_or_owner",
                         description="POST /servers"),
        policy.PolicyOpt("os_compute_api:servers:create:forced_host",
                         "rule:admin_or_owner",
                         description="POST /servers with forced_host hint"),
        policy.PolicyOpt("os_compute_api:servers:create:attach_volume",
                         "rule:admin_or_owner",
                         description="POST /servers with provided BDM"),
        policy.PolicyOpt("os_compute_api:servers:create:attach_network",
                         "rule:admin_or_owner",
                         description="POST /servers with requested or "
                         "provided network"),
    ]

    policy_engine = policy.get_policy()
    # registration will error if a duplicate policy is defined
    policy_engine.register_opts(server_policies)


    nova/api/openstack/servers.py
    -----------------------------

    def create(self, context):
        context.can('os_compute_api:servers:create')
        if volume_to_attach:
            context.can('os_compute_api:servers:create:attach_volume')

Please note that context.can() will simply be a wrapper around
policy.authorize().

The current proposal would have policy registration happen in a centralized
place, like configuration is.

Alternatives
------------

Discussion on the policy API has occurred in the oslo.policy spec for this
work so there are no alternatives to discuss on that here.


Data model impact
-----------------

None

REST API impact
---------------

None.

Security impact
---------------

None. This change essentially allows for preemptive policy checks but does not
change the handling of policy. And this change doesn't expose anything directly
it simply allows for later work to build on this.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

The performance cost of this will be in doing policy registration at service
startup time. It will be similar in mechanism to configuration registration
which has a negligible impact. Policy checking may become marginally faster due
to potentially having smaller policy files to read before each check.

Other deployer impact
---------------------

When all policies are registered there will no longer be a fallback to the
default rule. Deployers who are currently reliant on it for setting multiple
policies will need to explicitly define policy overrides for those policies.
This will be covered in reno upgrade notes.

Additionally this will enable us to set up a check to ensure that if new
policies are added they are accompanied by a reno addition. Deployers should be
aware that new policies may show up in release notes.

Developer impact
----------------

Any policies added to the code should be registered before they are used. While
the code is switching checks over to context.can() it will be possible to use
policy checks that have not been registered. At some point a hacking check
should be added to disallow the use of oslo_policy.Enforcer.enforce().


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alaski

Other contributors:
  claudiub

Work Items
----------

* Define and register all policies.

  * This can happen gradually

* Add context.can() which proxies to oslo_policy.policy.Enforcer.authorize().
* Update all policy checks to use the new context.can() method.
* Add hacking check to disallow oslo_policy.policy.Enforcer.enforce().
* Update Devstack to have an empty/no policy file.
* Update deployer documentation.
* Add sample file generation configuration and tox target.
* Add a nova-manage command to write out a merged policy file. This will be the
  effective policy used by Nova, a combination of defaults and configured
  overrides.
* Add a nova-manage command to dump a list of policies in a policy file which
  are duplicates of the coded defaults. This will help deployers trim the fat.


Dependencies
============

* https://review.openstack.org/#/c/309152/ Allow policy registration from code
  (oslo.policy). This is a hard dependency for the core functionality here.

* https://review.openstack.org/#/c/309153/ Add capability to generate a sample
  policy.json (oslo.policy). This is for the nice to haves, like sample file
  generation and showing default overrides.


Testing
=======

This spec does not intend to expose anything to end users so most testing will
be limited to in tree unit and functional tests.

A new tox target will be added for sample policy file generation and that can
be used to test that the generation works. The docs generation job could be
updated to also output this file.

Devstack will be updated to run Nova without a policy file as a way to check
that the defaults are used, and sane.

Documentation Impact
====================

Documentation for deployers about the policy file will be updated to mention
that only policies which differ from the default will need to be included.

References
==========

None


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
