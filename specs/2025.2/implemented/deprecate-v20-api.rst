..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Remove legacy v2.0 API
======================

https://blueprints.launchpad.net/nova/+spec/remove-v20-api

Remove the legacy v2.0 API.

Problem description
===================

Nova introduced the v2.1 API over a decade ago. Since that time, we have
continued to support the legacy v2.0 API, which was reimplemented as a shim
around the v2.1 API. A decade is a long time, and the Compute API has grown and
changed significantly over this time, hitting the 100th microversion in the
Epoxy (2025.1) release. Deploying and maintaining the legacy API has a cost and
there is no good reason why anyone would continue to use this over even the
base microversion. It is also mostly undocumented for an end-user perspective.
We should deprecate it so that we can remove it.

Use Cases
---------

As a developer, I no longer want to concern myself with potential differences
between v2.0 and v2.1.

As a developer of deployment tooling, I would like to be able to stop deploying
an additional, unused endpoint.

As a library developer, I would like to able to ignore the v2 API without
feeling bad for doing so.

Proposed change
===============

Change the API status to ``DEPRECATED``. This will cause keystoneauth1 and
recent versions of Gophercloud to ignore the API unless the user opts into it.
This is a strong signal to users that the API is not long for the world, and
will allow us to remove it in the H release.

Update all tests to remove confusing references to the ``/v2`` path. In most
cases, these are irrelevant since we call controllers directly and the path
part of the URL is ignored, but updating things will make things clearer.

A "do not merge (DNM)" patch will be proposed removing the v2 API. This will
serve to highlight any places we have missed things in the unit or functional
tests.

Alternatives
------------

Continue to pretend we support this in a meaningful way.

Data model impact
-----------------

None.

REST API impact
---------------

The root version document will not report status ``DEPRECATED`` for the v2 API.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None. All known clients use and rely on the microversioned endpoint.

Performance Impact
------------------

Negligible.

Other deployer impact
---------------------

Deployment tooling will be encouraged to stop create a legacy v2 endpoint.

Developer impact
----------------

The v2 API will no longer need to be considered when undertaking work on the
API. Future changes to the API frameworks used will become somewhat easier.

Upgrade impact
--------------

The v2 legacy API will be deprecated. As such, applications that rely on this
and use libraries that ignore deprecated APIs (like keystoneauth and recent
Gophercloud) will need to be reworked to use the v2.1 API or to opt-in to the
v2 API. It is expected that there are few to none of these applications in the
wild nowadays.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephen.finucane

Feature Liaison
---------------

Feature liaison:
  N/A

Work Items
----------

* Mark the API as deprecated
* Update tests to use the v2.1 API or remove paths where irrelevant
* Update docs to reflect deprecation and future plans for removal

Dependencies
============

None.

Testing
=======

Unit tests should cover this.

Documentation Impact
====================

References to the v2 API will be updated to highlight the deprecation and
future plans for removal.

References
==========

None.
