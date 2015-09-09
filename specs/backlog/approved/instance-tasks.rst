..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Instance tasks - A short history and primer
===========================================

This starts as a story about exposing errors to users.

From very early on, if not the beginning, the Nova API has had a concept of an
instance fault.  This is a record that contains information on a failure that
occurred within Nova while doing something with an instance.  It is extremely
useful for conveying information to users when there is a failure but it has
two major drawbacks.  The first is that it's only visible when the instance is
in an ERROR state, and the second is that only the latest fault is visible.
With the advent of API v2.1 it may be possible to address these issues.

Before API v2.1 was in progress two things, called instance-actions and
instance-action-events, were added to Nova to address the shortcomings of
instance faults.  Instance-actions is a user visible log of API actions that a
user has requested with a success or failure status.  Instance-action-events
are an admin facing log which goes into more details of the compute methods
invoked and any stack traces that occurred.  These made it possible to expose
failures without needing to set an instance to ERROR.  The biggest drawback to
these is that they're not well publicized so users may not know to look at
them.

Along the way we realized that the concept of displaying most errors on the
instance was flawed and what we needed was a way to represent a task on an
instance and a corresponding success or failure of the task.  For example
something like rebooting an instance can fail before affecting the power state
of an instance and the instance isn't affected.  In that case we want to say
that the reboot failed and not have to consider the instance to have a
fault/error on it because it is still running normally.  This lead to the idea
that from an API perspective we want an action to be, or lead to, the creation
of a task with an associated status rather than a POST to /actions on the
instance.  However as an intermediate step we could have that POST create a
task resource and return a link to it.  A proposal for how this could look was
provided by jaypipes at `http://docs.oscomputevnext.apiary.io/#servertask`.

Beyond the API impact there are other reasons to introduce a task concept to
Nova, keeping in mind that a task could mean something high level like rebuild
or the multiple individual units of work needed to accomplish rebuild:

1. The Nova code implements a rudimentary state machine for instances with
   logic for what to do spread across multiple modules.  However it's not
   always clear that there aren't dead ends in the state machine or states that
   can't be reached.  If the logic for various actions could be pulled into
   task modules we could more easily create proper state machines for them.

2. In conjunction with the above idea tasks should be the mechanism of change
   within Nova.  Right now we send an instance to a method like rebuild() and
   that contains the logic for rebuild.  What I envision instead is sending the
   task object via RPC and having it drive the state changes on an instance.
   Ultimately conductor/compute could just have a single method like
   execute_task_on_instance(task, instance).  That's a bit unrealistic but that
   could be the general concept.

3. Actions on instances should be able to be stopped and resumed.  This is
   important for being able to restart services.  If the state of a task can be
   persisted then when a service restarts it could pick up and resume the task.
   This implies that tasks should be idempotent, which is unlikely, or that
   they should have checkpoints.

4. A future idea could be to strip nova-compute to being a tasks worker which
   has very little logic in it and is mostly responsible for pulling tasks from
   a queue.  This moves us closer to a place where multiple nova-computes could
   be running for a single hypervisor just pulling work from multiple
   conductors.  Then nova-compute would not be a single point of failure.  This
   idea has not been discussed within the community and is simply something
   I've considered and should be considered completely out of scope here.  But
   it is an example of the type of thing that tasks could enable.


The early work on tasks was focused on introducing the concept at the API
level.  The idea was to get the interface in place and then rework the Nova
internals to match that concept.  There's some merit to that approach but this
can be done differently as well.  The focus could start on the internals of
Nova and getting that framework in place and then exposing it in the API once
the details are understood.  The main advantage I saw to working on the API
first is that we could rework the internals of Nova without being completely
bound by the state machine that the API currently exposes.  The main advantage
I see to working on the internals first is that we currently have to guess at
how tasks should be exposed and what fields they should contain but by
implementing them within Nova that will become clear.

What about TaskFlow?  TaskFlow is a potential implementation detail in all of
this work but I believe it is too early to talk about integrating it into Nova.
There's a lot of work to do to untangle the mess of RPC cast/calls and the
implicit state machine within Nova and start to centralize some of that within
conductor before something like TaskFlow looks like a good fit.  My suggestion
would be to work on iterating towards a task model within Nova and if the
solution starts to look like a fit for TaskFlow then that discussion can
happen.  In other words let's not change Nova to fit TaskFlow but use TaskFlow
if it fits in Nova.


Finally, instance faults and instance-actions should be deprecated by
implementing them on top of tasks.  Instance faults should be doable by
exposing the last failed task as an instance fault.  Instance actions is a
simplified view of the list of tasks.  But there is one instance-action per API
operation and potentially multiple tasks so one task will need to be selected
to be exposed as the instance-action.


Problem description
===================

None

Use Cases
----------

None

Project Priority
-----------------

None

Proposed change
===============

None

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

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

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  None

Other contributors:
  alaski

Work Items
----------

None

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

None

References
==========

[1] `http://docs.oscomputevnext.apiary.io/#servertask`


History
=======

Optional section for liberty intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
