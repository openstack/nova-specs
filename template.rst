::

  #
  # Copyright (C) 2014, <Copyright holder>
  #
  # Licensed under the Apache License, Version 2.0 (the "License"); you may
  # not use this file except in compliance with the License. You may obtain
  # a copy of the License at
  #
  #      http://www.apache.org/licenses/LICENSE-2.0
  #
  # Unless required by applicable law or agreed to in writing, software
  # distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  # WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  # License for the specific language governing permissions and limitations
  # under the License.
  #

*Delete this paragraph when you write your blueprint.* Here are some
simple instructions. This template should be in ReSTructured text. The
filename in the git repository should match the launchpad URL, for example a
URL of https://blueprints.launchpad.net/nova/+spec/awesome-thing should be
named awesome-thing.rst .

=============================
 The title of your blueprint
=============================

Put the URL of your blueprint on launchpad here, as well as any other related
blueprints.

Introduction paragraph -- why are we doing anything? A single paragraph of
prose that operators can understand.

Detailed problem description
============================

A detailed description of the problem. For a new feature this might be use
cases. For a major reworking of something existing it would describe the
problems in that feature that are being addressed.

Proposed change
===============

Here is where you cover the change you propose to make. Some things to
consider:

- How will the feature be used? You could call this the user interface. It
  might take various forms:

  - For an API extension, API samples are required, *NOT* simply nova command
    line examples.

  - Does this change have an impact on python-novaclient? What does the user
    interface there look like?

  - If this change is a new binary, how would it be deployed?

- Consistency of the user experience is also important. Some concrete examples:

  - What config options are being added? Should they be more generic than
    proposed (for example a flag that other hypervisor drivers might want to
    implement as well)? Are the default values ones which will work well in
    real deployments?

  - If the blueprint proposes a change to the driver API, discussion of how
    other hypervisors would implement the feature is required.

- If this is one part of a larger effort make it clear where this piece ends.
  In other words, what's the scope of this effort?

Dependencies
============

- Include specific references to specs in other projects that this one either
  depends on or is related to.

- If this requires functionality of another project that is not currently used
  by Nova (such as the glance v2 API when we previously only required v1),
  document that fact.

- Does this feature require any new library dependencies or code otherwise not
  included in OpenStack?

Implementation
==============

Who is writing the code? Is anyone signed up to do the work? Or is this a
blueprint where you're throwing it out there to see who picks it up?

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.

Cover upgrade impact -- how will deploying this change affect existing users?
For example, if we change the directory name that instances are stored in,
how do we handle instance directories created before the change landed? Do we
move them?  Do we have a special case in the code? Do we assume that the
operator will recreate all the instances in their cloud?

Alternative implementations
===========================

What other ways could we do this thing? Why aren't we using those? This doesn't
have to be a full literature review, but it should demonstrate that thought has
been put into why the proposed implementation is the appropriate one.

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

Documentation impact
====================

What is the impact on the docs team of this change? Some changes might require
donating resources to the docs team to have the documentation updated.
