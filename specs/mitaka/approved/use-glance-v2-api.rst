..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Add support for Glance v2 API
==============================

https://blueprints.launchpad.net/nova/+spec/use-glance-v2-api

This spec adds the ability support for Nova to use the Glance v2 API, and start
the deprecation period for the support of the Glance v1 API.

While parts of Nova already use the Glance v2 API, this is about making the
dependency on Glance v1 API optional, so it can be removed completely in a
future release.

Problem description
===================

Glance relegated v1 from CURRENT to SUPPORTED status in Kilo. Currently Nova
requires access to the Glance v1 API. Glance would like to deprecate that API,
so to help that effort Nova should stop using Glance v1 API.

To allow for a smooth upgrade, we need to ensure Mitaka supports using both
Glance v1 and Glance v2, to give deployers time to ensure they have Glance v2
deployed in a way that can be used by Nova.

While some areas of Nova already make use of Glance v2, there are many areas of
Nova that still have a hard dependency on Glance v1. The key areas that still
use Glance v1 include:

* Nova's Image API, that is effectively just a proxy of Glance's v1 API

* Virt driver specific download of images and upload of images

* CRUD operations on image metadata

* Creating and deleting snapshots in common code.

Before we can stop Nova requiring Glance v1 and fully deprecate the requirement
for Glance v1, we need to remove all the above uses of Glance v1.

Note we must keep compatibility for Glance v1 and Glance v2 to allow for a
smooth upgrade between releases.

Note the current version of Glance v2 does not provide an efficient way to
implement the changes_since parameter that is supported by the current Nova
Images API. However, Glance have plans to fix that:

https://blueprints.launchpad.net/glance/+spec/v2-additional-filtering

Use Cases
----------

Currently, Nova deployers are forced to deploy both Glance v1 and Glance
v2. This is because Nova currently requires Glance v1, but only Glance v2 is
considered safe to be exposed publicly to End Users.

It is assumed that Nova's lack of support for Glance v2 is causing confusion
that is holding people back from deploying Glance v2. This in turn is causing
some problems for the DefCore effort.


Proposed change
===============

The number of changes would be minimal to avoid destabilizing. A thorough
refactor can be done in a follow up spec(s).

The main bulk of the work is ensuring the Nova Image API contract is maintained
while talking to either Glance v1 API or Glance v2 API. This will require the
current Nova Image seam to be capable of talking to both version of the API at
the same time. Glance API's version discoverability will be used to determine
whether the v2 of the API is deployed or not. If so, it'll be prefered over v1.

The second part is looking at other areas in Nova's Glance related
modules that don't work with the Glance v2 API.

Once that is completed, there are still some virt driver specific Glance client
code, but that will be considered a stretch goal, and should not block the
general deprecation of Glance v1 API support.

The virt drivers that don't support Glance v2 should fallback to
v1. Eventually, all drivers should support v2 and Glance's v1 should be turned
off by default. The expected deadline for this switch is N.

This spec doesn't intend to change the value of the existing Nova
configurations for Glance - which include the version in the URL - but rather
notify the deployer that the new expected value has changed and the
configuration file should be updated. During the Mitaka cycle, we can strip the
verion from the URL to discover what versions of the API are deployed and favor
2 over 1 when possible.

Alternatives
------------

Ideally glanceclient should work as a seam for both Cinder and Nova to use to
upload and download images, with a stable API. But this is not currently the
case, and we have waited too long for this support to delay this work any
further. However, it is assumed that this will exist in the future to avoid
getting to these situation again.

Data model impact
-----------------

None.

REST API impact
---------------

There will be no impact on the REST API contract. The Nova Image API will
continue to proxy requests to Glance v1 until the work to bring back
changes_since is complete.


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

The deployers should need to be aware that it's possible some virt drivers may
not support Glance v2 yet. The details of this will be clearly documented in
the release notes and proper warnings will be logged.

These drivers will explicitly request v1 to be deployed instead of relying
entirely on version discoverability

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mfedosin

Other contributors:
  flaper87
  sudipto

Work Items
----------

* Move `nova.image` to be backed by either Glance v1 or Glance v2, defaulting
  to Glance v2. Do this by refactoring the models that consume the images API
  to support Glance v1 and Glance v2.

* Ensure the rest of the code base can use the existing image code to talk to
  either Glance v1 or Glance v2, again defaulting to Glance v2 when possible.

* Ensure all the virt drivers either support Glance v2 or fallback to v1.

* Add a deprecation warning in the logs if users run with Glance v1.

Dependencies
============

Full support for Glance v2 by the Nova Image API is dependent on:

https://blueprints.launchpad.net/glance/+spec/v2-additional-filtering

Testing
=======

The existing tempest tests will validate the Glance v2 API support, as the
default will move to Glance v2.

However, we should also make sure one of the gate jobs still tests the Glance
v1 only to avoid breaking existing deployments.


Documentation Impact
====================

* Glance API version configuration option needs to be documented
* Release Notes should note the partial deprecation of Glance v1 support
* Release Note should warn about any virt drivers that are unable to run with
  Glance v2.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
