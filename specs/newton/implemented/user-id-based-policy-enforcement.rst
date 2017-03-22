..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
User_id based policy enforcement
================================

https://blueprints.launchpad.net/nova/+spec/user-id-based-policy-enforcement

Policy.json is a turing complete ball of confusion. Only the brave
dare to wander through it's halls. Only the fortunate come out
unscathed. No one has truly explored what can be created from this
beast, and we discover new wonders every day.


Problem description
===================

In the legacy v2 Nova API code base, it turned out there was a back
door feature by which operations could be scoped to 'user_id' instead
of 'project_id'. No one on the Nova team realized this was a thing. It
was not baked into the current Nova API stack, which started being
worked on 3 years ago.

As is the great promise of all software, if a feature/bug exists, and
is shipped, eventually someone will make it critical to their use of
that software.

In this case this was used as a backdoor to the lack of hierarchical
projects. That should be the real solution here. And it is also clear
based on this feature use that simple 1 level of nesting of
hierarchical projects with only quota accounted at the top level, is
sufficient for many people's needs.

The way this was used was to put large sets of users (~150) into a
single project, with one quota for them all, but not allow users to
manipulate each other's servers.

This spec proposes that we support a very limited set of operations on
servers to check the user_id of the server in policy. These are
operations that are considered destructive to servers.

Use Cases
---------

Large deployments, like CERN, find it cumbersome to create keystone
projects for every single effort that has a different group of
people. For these more ephemeral efforts they create large "catchall"
projects and put users in them.

These users are working on different things, are not collaborating in
the traditional boundaries we expect within a keystone project, and
may not even know who else is in their "project". As such they want to
prevent users from accidentally destroying each others work. This was
done by updating policy to constrain many operations to user_id scoped
instead of project_id scoped.

.. note::

   This goes wildly against the designed permissions model in
   OpenStack. We really don't want this feature in Nova, and we don't
   want it used. This spec is entirely a shim until basic hierarchical
   project support exists, after which it will be removed.

Proposed change
===============

The following operations will be checked in policy taking the user_id
into account (if configured in policy.json).

* DELETE /servers/{server_id} - destructive
* PUT /servers/{server_id} - lets you change server name

As well as the following server actions:

* changePassword
* lock
* pause
* rebuild
* resize
* rescue
* os-stop
* suspend
* evacuate
* forceDelete
* shelve
* crashDump

These are considered destructive actions. Other, only disruptive,
actions such as `reboot` will be allowed. Also other security
exposures such as `show console` won't be addressed. The boundary for
security in OpenStack is a `project`. This is just a safe guard for
some server destructive behavior that existing sites are concerned
about. This list of actions was `acknowledged`_ as sufficient by key
stake holders (such as CERN) that spoke up with the initial issue.

This will be added as a deprecated construct, and will be removed in
the future. It should give people some time to migrate away to other
models, and realize this is not going to be supported in the
future. This kind of change introduces an interop problem, which is
why it will be discouraged from use.

The eventual solution will be hierarchical projects. As seen from this
use case, many uses of hierarchical projects only need quota at the top
level. As such, that should be considered a first pass before working
out hierarchical quotas.

Alternatives
------------

Do nothing. This is somewhat of a fringe feature.

Data model impact
-----------------

None.

REST API impact
---------------

This changes the way we do policy enforcement in a series of API
calls.

For deployments that choose to do this, they should realize that they
are breaking the basic interop construct that permissions for all
server constructs are a project level permissions construct. It would
be great to have some Tempest tests to check for this.

Security impact
---------------

We are explicitly not handling all the security sensitive API
points. This is only to prevent the worse accident destruction of
resources (like the fact that ``rm -rf /`` no longer actually does the
scary thing).

Users operating within the same project should be considered
collaborative multi taskers, and can access each others resources.

Notifications impact
--------------------

None.

Other end user impact
---------------------

In the default case, None.

Performance Impact
------------------

None. All the data needed for the policy checks is already there.

Other deployer impact
---------------------

In the default case, None.

Because deployers were using this feature of the legacy v2 stack in
Liberty, we should consider backporting this to Mitaka and possibly
liberty to smooth the transition.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Ghanshyam Mann <ghanshyam.mann@nectechnologies.in>

Work Items
----------

* Implement policy checks for the listed calls above
* Implement custom policy testing for each of those calls
* Backport to Mitaka
* Potentially backport to Liberty


Dependencies
============

None.

Testing
=======

This will all be tested in tree with unit / functional testing and a
custom policy using `user_id` rules. There is currently no testing
which is why we removed this backdoor feature and did not notice.

Documentation Impact
====================

We should at the same time delete all references to using `user_id`
based policies for Nova from any OpenStack documentation, so that new
people do not start using this.

The only exception being `keypairs`, which has always been a bit of
an oddball element in Nova.

References
==========

* OpenStack Operators Discussion -
  http://lists.openstack.org/pipermail/openstack-operators/2016-May/010526.html

.. _acknowledged: http://lists.openstack.org/pipermail/openstack-dev/2016-June/096590.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
