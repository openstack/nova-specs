..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Remove 'v3' from nova API code tree
==========================================

https://bugs.launchpad.net/nova/+bug/1462901

When trying to work on Nova API code, there are many confusing
concepts in the directory tree which make it harder than it should be
to map what's in the tree to what's in the API.

Example confusions:

* v2.1 code is in ``nova/api/openstack/compute/plugins/v3``. People
  get confused about what v3 is.
* there are both ``plugins`` and ``contrib`` directories
* the v2.0 code is in the top level ``nova/api/openstack/compute``
  even though it's deprecated.

We should clean up the api directory structure to be less confusing so
that it reduces cognitive load in working on the code base, and makes
more sense to new contributors.

Problem description
===================

See above.

Use Cases
----------

None. This is a code tree cleanup for Nova.

Project Priority
-----------------

This is a priority work item under the Nova API in Liberty.

Proposed change
===============

The api directory structure should look something more like this (this
is an example with some key data, not the entire set of moves):

::
   nova/api/openstack/
       compute/ - all the os compute api
           legacy_v2/ - the entry point for all the v2 code. This will
                        make it easier to remove in the future

           servers.py - the v2.1 servers implementation

           flavors.py - the v2.1 flavors implementation

           servers/   - a directory containing code which adds resources
                        to servers

           servers/actions/pause.py (renamed from pause_server.py)

           servers/actions/ - all chunks of code that add actions

           flavors/ - all chuncks of code that extend add things to
                      flavors

           etc...


Basically take all the v2 code, put it in the corner so it's not the
first thing people find.

Then take the rest of the code and make it have no version in its
name, and create a directory structure on disk that mirrors the REST
URI structure as much as possible. Making it simpler to understand
where things fit in the REST strucuture.


* Move the V2 API code which is currently under
  ``nova/api/openstack/compute`` and
  ``nova/api/openstack/compute/contrib`` into
  ``nova/api/openstack/compute/legacy_v2``. The 'V2' API will be
  deprecated in the future.
* The Nova V2.1 REST API refers to the new Nova REST API with
  Microversion.  The evolution of v2.1 will be done by Microversion in
  the future. So the proposal is that the API version won't be
  included in any code path. The V2.1 API which is now under
  ``nova/api/openstack/compute/plugins/v3`` will be moved into
  ``nova/api/openstack/compute``. This means that the V2.1 API will be
  the only compute API supported by Nova. The JSON-Schema used by v2.1
  API moves into ``nova/api/openstack/compute/schemas``.
* Remove any reference to 'v3' from the code, tests, and configuration
  files.  Examples: APIRouterV3, and v3 endpoint entry in
  api-paste.ini, etc.
* Restructure the code on disk for the v2.1 code to more accurately
  reflect the REST uri structure of the resources those components
  represent.
* Note that existing api-paste.ini files refer to the `APIRouter` and
  `APIRouterV21` classes. We will have to maintain these names so that when
  people upgrade we don't break things.

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

* Move all V2 code under 'legacy_v2' directory.
* Update all existing references to 'nova.api.openstack.compute' to point to
  'nova.api.openstack.compute.legacy_v2' instead.
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
