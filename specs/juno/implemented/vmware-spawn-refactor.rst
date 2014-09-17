..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
VMware Spawn Refactor
=====================

https://blueprints.launchpad.net/nova/+spec/vmware-spawn-refactor

A structured refactor of the VMware driver spawn utility code to create a more
cohesive and coherent whole.


Problem description
===================

The VMware driver's spawn utility method is over 500 lines of code and very
difficult to follow. It features redundant logic in several places as well as
a general lack of cohesive constructs for a programmer to follow. Tests of the
spawn method involve complicated test frameworks that require a developer or
reviewer to hold important context between different seemingly unrelated
modules in their heads. While test coverage is actually quite good on the
spawn method, it can be very difficult to comprehend how a test functions and
comprehending this complexity slows reviews.

* create a spawn method that composes utility methods

* improve readability

* provide encapsulation

* separate model code from action code for easier maintenance

* make tests more understandable to reviewers and test coverage easier to see


Proposed change
===============

* Extract inner methods and create reusable and testable methods

  * allow for simple mocking in tests to easily cover all paths

  * create easier to follow test cases with shallower call depths

* Consolidate vSphere image properties for easier use and testing

  * NOTE: for the scope of this blueprint we examine only existing configs

  * include checks for valid values for use in vSphere API before transmiting
    to vSphere where possible. Pre-checking values will make it easier to
    diagnose a driver fault.

* Identify and extract additional utilities and methods hidden in spawn

  * large sections of spawn are repeated in other utilities (stop that)

  * identify image actions and create utilities for those

Alternatives
------------

* continue to add to the existing method

* expand fake.py into a full blown vCenter simulator

* only change code as it pertains to new features or bugs

Data model impact
-----------------

None.

REST API impact
---------------

None. This is a zero new feature blueprint.

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

None or negligible. Some early work has determined that there are multiple
network round trips to glance that do not need to occur, but performance
changes will be an expected side-effect of the refactoring work.

Other deployer impact
---------------------

None.

Developer impact
----------------

- Sanity preservation: consolidation and refactoring of driver logic will make
  an easier to follow driver that will make addition of new features easier.

- Simplified testing, smaller units of code means more granular tests and
  easier to follow test structure.

- Introduction of better practice, this code will serve as a positive example
  for future contributions.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  hartsock

Other contributors:
  vui
  rhsu
  tjones-i
  garyk
  maithem

Work Items
----------

* extract inner methods from spawn

* consolidate VMware specific image configurations

  * identify parameters set in image metadata and formalize them

  * identify values that control current behavior and isolate them

* refactor image file manipulation into a set of re-usable utilities


Dependencies
============

None.


Testing
=======

Standard Minesweeper testing should reveal if this refactor has not regressed
any features and will cover all cases this code will refactor.


Documentation Impact
====================

None. Internal developer documentation will be greatly improved.


References
==========

* https://blueprints.launchpad.net/nova/+spec/vmware-spawn-refactor