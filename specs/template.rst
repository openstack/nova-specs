::

# This work is licensed under a Creative Commons Attribution 3.0 Unported
# License.
#
# http://creativecommons.org/licenses/by/3.0/legalcode

..
  This template should be in ReSTructured text. The filename in the git
  repository should match the launchpad URL, for example a URL of
  https://blueprints.launchpad.net/nova/+spec/awesome-thing should be named
  awesome-thing.rst .  Please do not delete any of the sections in this
  template.  If you have nothing to say for a whole section, just write: None
  For help with syntax, see http://sphinx-doc.org/rest.html
  To test out your formatting, see http://rst.ninjs.org/
  Please wrap text at 80 columns.

==========================================
Example Spec - The title of your blueprint
==========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/example

Introduction paragraph -- why are we doing anything? A single paragraph of
prose that operators can understand.


Problem description
===================

A detailed description of the problem:

- For a new feature this might be use cases. Ensure you are clear about the
  actors in each use case: End User vs Deployer

- For a major reworking of something existing it would describe the
  problems in that feature that are being addressed.


Proposed change
===============

Here is where you cover the change you propose to make in detail. How do you
propose to solve this problem?

If this is one part of a larger effort make it clear where this piece ends. In
other words, what's the scope of this effort?

Alternatives
------------

What other ways could we do this thing? Why aren't we using those? This doesn't
have to be a full literature review, but it should demonstrate that thought has
been put into why the proposed solution is an appropriate one.

Data model impact
-----------------

Changes which require modifications to the data model often have a wider impact
on the system.  The community often has strong opinions on how the data model
should be evolved, from both a functional and performance perspective. It is
therefore important to capture and gain agreement as early as possible on any
proposed changes to the data model.

Questions which need to be addressed by this section include:

- What new data objects and/or database schema changes is this going to require?

- What Database migrations will accompany this change.

- How will the initial set of new data objects be generated, for example if you
  need to take into account existing instances, or modify other existing data
  describe how that will work.

REST API impact
---------------

Each API method which is either added or changed should have the following

* Specification for the method

  * A description of what the method does suitable for use in
    user documentation
  * Method type (POST/PUT/GET/DELETE)
  * Normal http response code(s)
  * Expected error http response code(s)
  * URL for the resource
  * Parameters which can be passed via the url
  * JSON schema definition for the body data if allowed
  * JSON schema definition for the response data if any

* Example use case including typical API samples for both data supplied
  by the caller and the response

Example JSON schema definitions can be found in the Nova tree
http://git.openstack.org/cgit/openstack/nova/tree/nova/api/openstack/compute/schemas/v3

Note that the schema should be defined as restrictively as
possible. Parameters which are required should be marked as such and
only under exceptional circumstances should additional parameters
which are not defined in the schema be permitted (eg
additionaProperties should be False).

Reuse of existing predefined parameter types such as regexps for
passwords and user defined names is highly encouraged.

Notifications impact
--------------------

Please specify any changes to notifications. Be that an extra notification,
changes to an existing notification, or removing a notification.

Other End user impact
---------------------

Aside from the API, are there other ways a user will interact with this feature?

- Does this change have an impact on python-novaclient? What does the user
  interface there look like?

Deployer impact
---------------

Discuss things that will affect how you deploy and configure OpenStack,
such as:

- What config options are being added? Should they be more generic than
  proposed (for example a flag that other hypervisor drivers might want to
  implement as well)? Are the default values ones which will work well in
  real deployments?

- Is this a change that takes immediate effect after its merged, or is it
  something that has to be explicitly enabled?

- If this change is a new binary, how would it be deployed?

- Please state anything that those doing continuous deployment, or those
  upgrading from the previous release, need to be aware of. Also describe
  any plans to deprecate configuration values or features.  For example, if we
  change the directory name that instances are stored in, how do we handle
  instance directories created before the change landed?  Do we move them?  Do
  we have a special case in the code? Do we assume that the operator will
  recreate all the instances in their cloud?

Developer impact
----------------

Discuss things that will affect other developers working on OpenStack,
such as:

- If the blueprint proposes a change to the driver API, discussion of how
  other hypervisors would implement the feature is required.


Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  <launchpad-id or None>

Other contributors:
  <launchpad-id or None>

Milestones
----------

Originally approved for:
  Juno-1

Completed:
  None

Work Items
----------

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.


Dependencies
============

- Include specific references to specs and/or blueprints in nova, or in other
  projects, that this one either depends on or is related to.

- If this requires functionality of another project that is not currently used
  by Nova (such as the glance v2 API when we previously only required v1),
  document that fact.

- Does this feature require any new library dependencies or code otherwise not
  included in OpenStack? Or does it depend on a specific version of library?


Testing
=======

Please discuss how the change will be tested. We especially want to know what
tempest tests will be added. It is assumed that unit test coverage will be
added so that doesn't need to be mentioned explicitly, but discussion of why
you think unit tests are sufficient and we don't need to add more tempest
tests would need to be included.

Is this untestable in gate given current limitations (specific hardware /
software configurations available)? If so, are there mitigation plans (3rd
party testing, gate enhancements, etc).


Documentation Impact
====================

What is the impact on the docs team of this change? Some changes might require
donating resources to the docs team to have the documentation updated. Don't
repeat details discussed above, but please reference them here.
