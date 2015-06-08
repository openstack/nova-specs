..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Remove 'v3' from nova API code tree
==========================================

https://bugs.launchpad.net/nova/+bug/1462901

The Nova V2.1 REST API was released as part Kilo. But the V2.1 API code still
remains under the old directory 'nova/api/openstack/compute/plugins/v3' with
the old name 'v3'. The V3 API doesn't exist anymore; it is now referred to as
the V2.1 API.

We should cleanup any V3-related stuff, and restructure the nova code tree to
remove the references to V3, to avoid confusion for developers.

Problem description
===================

The V3 API has been replaced by V2.1 API. The word 'v3' in the nova code tree
confuses people a lot.

Use Cases
----------

None. This is a code tree cleanup for Nova.

Project Priority
-----------------

This is a priority work item under the Nova API in Liberty.

Proposed change
===============

* Move the V2 API code which is currently under 'nova/api/openstack/compute'
  and 'nova/api/openstack/compute/contrib' into
  'nova/api/openstack/compute/v2'. The 'V2' API will be deprecated in the
  future.
* The Nova V2.1 REST API refers to the new Nova REST API with Microversion.
  The evolution of v2.1 will be done by Microversion in the future. So the
  proposal is that the API version won't be included in any code path. The V2.1
  API which is now under 'nova/api/openstack/compute/plugins/v3' will be moved
  into 'nova/api/openstack/compute'. This means that the V2.1 API will be the
  only compute API supported by Nova. The JSON-Schema used by v2.1 API moves
  into 'nova/api/openstack/compute/schemas'.
* Remove any reference to 'v3' from the code, tests, and configuration files.
  Examples: APIRouterV3, and v3 endpoint entry in api-paste.ini, etc.

Alternatives
------------

Keep the V2.1 API under current directory until V2 support is removed. But
since all the API improvements in the future will be for the V2.1 API, a lot of
developers would be confused on how to code to the current API. We should get
rid of it now, and avoid confusing developers.

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
  Ed Leafe <ed@leafe.com>
  Alex Xu <hejie.xu@intel.com>

Work Items
----------

* Move all V2 code under 'v2' directory.
* Move all V2.1 code to the toplevel directory.
* Move V2.1's json-schema out of v3 directory.
* Remove v3 endpoint from api-paste.ini.
  Existed effort for this `https://etherpad.openstack.org/p/merge_sample_tests`

Dependencies
============

None

Testing
=======

No new tests are needed, but existing tests will have to be updated to work
with the new code tree.

The v2.1 API sample tests in `nova/tests/functional/v3` moved into
`nova/tests/functional/api_sample_tests`
The v2 API sample tests will be removed by
`https://etherpad.openstack.org/p/merge_sample_tests`

The v2.1 and v2 API unittests already merged. Move them into
`nova/unit/api/openstack/compute`.

Documentation Impact
====================

This is just a code cleanup, and will be invisible to end users.

References
==========

Nova API team work items:
`https://etherpad.openstack.org/p/YVR-nova-liberty-summit-action-items`

History
=======

None
