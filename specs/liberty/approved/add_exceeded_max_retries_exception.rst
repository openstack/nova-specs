..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Add a Distinct Exception for Exceeding Max Retries
==================================================

https://blueprints.launchpad.net/nova/+spec/no-valid-host-reporting

There are two separate and very different situations which raise a NoValidHost
exception when attempting to spawn a new VM, which is confusing for operators
who need to determine why a VM failed to spawn. This proposes to add a new
exception class that will make the two failure modes more obvious to the
operators.

Problem description
===================

Currently, a NoValidHost exception is raised in two separate cases:

  * when the scheduler filters cannot find a host that meets the requirements
    of the request

  * when the maximum number of retries is exceeded when attempting to create
    the VM

Operators can have a difficult time distinguishing between the two situations
when attempting to learn why a VM failed to spawn.

Use Cases
----------

As an operator I want a less confusing way of determining why a VM failed to
spawn. The current practice of having a NoValidHost exception raised for very
different failure reasons is not as helpful as separate exception types raised
for the different modes.

Project Priority
-----------------

This is part of the scheduler improvement effort, which has been identified as
a priority for Liberty.

Proposed change
===============

A new exception class named `MaxRetriesExceeded` will be defined, and all
places where NoValidHost is currently raised that are not due to all hosts
being filtered out will be changed to raise this new exception. This new
exception class will be a subclass of NoValidHost, so that any existing code
that is catching NoValidHost exceptions will not break.

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  edleafe

Work Items
----------

* Define the new exception class

* Search through the code for all cases where NoValidHost is raised, and change
  the exception class raised by those that are the result of exceeding the
  maximum number of retries to raise this new exception class instead.

Dependencies
============

None.

Testing
=======

Existing tests will be updated to test for the new exception class instead of
the old class wherever appropriate.

Documentation Impact
====================

None.

References
==========

None.
