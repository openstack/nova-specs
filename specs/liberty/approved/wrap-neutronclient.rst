..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Wrap the Python NeutronClient
==========================================

https://blueprints.launchpad.net/nova/+spec/nova-neutron-refactor

The Neutron client module used by the Neutron implementation of the
Openstack Network API is a basic, thin wrapper around the Neutron API.
Direct use of the module's functionality has resulted in pervasive adaptive
code throughout the API adapter implementation. The repetitive and
occasionally opaque nature of this code makes the implementation difficult
to debug and maintain. Providing higher level, Nova oriented abstractions
by wrapping the existing client:

* Makes it easier to implement readable implementations of the networking
  API implementation.

* Allows knowledge of the functioning of the Neutron API to be captured in
  code for reuse by all developers, independent of their Neutron API
  expertise. This is maintainable, extensible and testable in itself.

* Provides a natural boundary to hide neutron specific details such as:

  * thrown exceptions

  * JSON request and response translation


Problem description
===================

Direct use of the neutronclient module is pervasive throughout the
implementation of the Neutron Network API adapter. This has the following
consequences:

* Construction of JSON requests and parsing of replies is repeated
  throughout the code.

* Neutron specific exceptions are allowed to permeate the API boundary to
  the caller.

* How well the Neutron client is used varies depending on the expertise of
  the respective authors. There is no mechanism for capturing best
  practices that is immediately available to developers.

* Changes to the Neutron client can require pervasive changes to the
  adapter implementation.

* Certain API features are only accessible through contexts with administrative
  credentials, requiring maintainers to understand which operations are
  constrained or otherwise affected by administrative credentials.


Use Cases
----------

* Nova developers should not need to have direct knowledge of Neutron client
  or API specific details to perform rudimentary code changes.

* Developers with Neutron expertise need a mechanism to capture best
  practices in an accessible and immediately useful way for themselves and
  other developers.

* Special handling of remote call behavior can be introduced in a manageable
  and consistent fashion.


Project Priority
-----------------

This refactoring addresses an issue of significant technical debt and
is a step towards deprecating nova-network.


Proposed change
===============

Provide higher level abstractions of the Neutron client calls used by Nova
through a class (or family of classes if required). The classes hide
construction of JSON requests, translation of replies to Nova objects and
Neutron exceptions to Nova exceptions.

Alternatives
------------

Continue to directly use the Neutron client "in-place", possibly mitigating
code repetition through helper methods and performing ad-hoc exception
translation through alternate means such as decorators.


Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None.

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

The results of this effort are to be consumed in the refactoring of the
adapter so only has impact to developers working on this effort.


Implementation
==============

Assignee(s)
-----------

Primary assignee: Brent Eagles (beagles@redhat.com)

One or more sponsors from the core teams should have direct involvement
in an, at minimum, advisory capacity. Particularly:

* Dan Smith for Nova objects
* Matt Riedemann
* Maru Newby (Neutron)


Primary assignee:
* Brent Eagles  beagles@redhat.com


Work Items
----------

1. Create a class that provides higher level methods for neutron client.
2. Create tempest tests to exercise wrapper.


Dependencies
============

None


Testing
=======

The changes will be exercised through the existing CI.

Documentation Impact
====================

None


References
==========
