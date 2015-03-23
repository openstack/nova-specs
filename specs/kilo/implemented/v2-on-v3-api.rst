..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Implement the v2.1 API on the V3 API codebase
=============================================

https://blueprints.launchpad.net/nova/+spec/v2-on-v3-api

Implement v2 compatible API based on v3 API infrastructure.

Problem description
===================

On v3 API development, we have improved API infrastructure such as API
plugin loading, input validation, policy check, etc. In addition, to fix
inconsistent interfaces of v2 API, we have made a significant number of
backwards incompatible changes of the Nova API (Change success status
codes, API attribute names, and API URLs). There is a comprehensive
description of the problems with the v2 API for users, operators and
developers here:
http://ozlabs.org/~cyeoh/V3_API.html

However, there have been intensive discussions over the future of Nova
and the maintenance overhead implications from having to support two
APIs such as v2 and v3 simultaneously for a long period of time.


Use Cases
---------

This is primarily API infrastructure cleanup work which will
eventually allow us developers to remove the old V2 API codebase which
is fragile and does not support the features of the V3 API
framework. It also is required work in order to support microversions
in the future. The impact on users and deployers is described in the
following sections.

Project Priority
-----------------

The kilo priorities list is currently not defined. However under the
currently proposed list of priorities it would fall under "User
Experience" as it paves the way for microversions and the ability for
us to improve the Nova API.

Proposed change
===============

Through a lot of discussions, we have understood the advantages of v3 API
infrastructure (API plugin loading, input validation, policy check, etc).
However, their backwards incompatible interfaces seem a little premature at
this time, because now we aren't sure that current v3 API is the best.
That means we cannot be sure that any more backwards incompatible changes
are unnecessary even if switching to current v3 API.

This spec proposes the removal of backwards incompatible changes from v3 code.
That means current v3 consistent interfaces would go back to v2 inconsistent
ones like::

  --- a/nova/api/openstack/compute/plugins/v3/servers.py
  +++ b/nova/api/openstack/compute/plugins/v3/servers.py
  @@ -752,7 +752,7 @@ class ServersController(wsgi.Controller):
  The field image_ref is mandatory when no block devices have been
  defined and must be a proper uuid when present.
  """
  - image_href = server_dict.get('image_ref')
  + image_href = server_dict.get('imageRef')

This proposal is painful for v3 API developers because they have worked hard
to make consistent interfaces over a year and v3 interfaces are exactly better
than v2 ones. However, through the discussions, we have known that backwards
incompatible changes are very painful for users and we must pay attention to
these changes.

On this spec, we would provide v2 compatible API with the other v3 advantages
as the first step. After this spec, we will provide consistent interfaces by
defining API rules step by step. These rules will prevent the same backwards
incompatible changes and keep consistent interfaces even if adding a lot of
new APIs in the future. However, that is out of scope from this spec now.

Alternatives
------------

Through these discussions, we got an idea that we could support both v2 API
and v3 API on the top of the v3 API codebase. On this idea, nova translates a
v2 request to v3 request and passes it to v3 API method. After v3 API method
operation, nova translates its v3 response to v2 response again and returns
it to a client.
However, there was an intensive discussion against this idea also because it
would be difficult to debug API problems due to many translations when we have
a lot of backwards incompatible changes in the long term.

Data model impact
-----------------

None

REST API impact
---------------

The V2.1 REST API presented will be identical to the V2 API except as
noted above.

Note however that V2.1 will not support the XML version of the V2 API,
only the JSON one. However the XML version of the V2 API is currently
marked as deprecated.

Security impact
---------------

Better up front input validation will reduce the ability for malicious
user input to exploit security bugs.

Notifications impact
--------------------

None

Other end user impact
---------------------

Potentially it may be advantageous if python novaclient could talk to
/v2.1 instead of /v2 but code changes may not be required to change
this. It may be simpler just to do this through keystone configuration.
The API itself remains identical.

Performance Impact
------------------

More stringent input validation also means more work that is needed to
be done in the API layer but overall this is a good thing.

Other deployer impact
---------------------

If the deployer wanted to export the API as /v2 rather than /v2.1 then
they would need to modify the api-paste.ini file (a couple of line
change to disable the original V2 API and use the APIRouterV21 as
the /v2 API.

The long term goal would be to deprecate and eventually remove the
original V2 API code when deployers and users are satisfied that v2.1
satisfies their requirements.

The process which we would use is:

* V2.1 fully implemented with Tempest verification (including extra
  verification that is being added in terms of response data)
* Verification from multiple sources (cloud providers, users etc) that
  V2.1 is compatible with V2

  * This could be done in various ways

    * Keystone changes so /v2.1 is advertised instead of /v2
    * Exporting the V2.1 as /v2
    * Combined with the possibility of putting V2.1 input validation into
      a log rather than reject mode.

* V2.1 is in an openstack release for N versions
* After widespread confirmation that the V2.1 API is compatible, V2
  would be marked as deprecated

Developer impact
----------------

Long term advantages for developers are:

* All the API implementations are on the new API framework

* Reduction in maintenance overhead of supporting two major API
  versions

* Have a better framework for handling future backwards incompatible
  changes.

In the short term while the old V2 API code exists there will still be
a dual maintenance overhead.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cyeoh-0

Other contributors:
  oomichi
  Alex Xu

Work Items
----------

* Change v3 success status codes to v2 ones.

* Change v3 API routings to v2 ones.

  * Handle API URLs include a project id.
  * Change the API resource paths. (e.g: /keypairs(v3) -> /os-keypairs(v2))
  * Change action names. (e.g: migrate_live(v3) -> os-migrateLive(v2))

* Change v3 API attribute names to v2 ones.

  * Change the API parsers of v3 code.
  * Change the API schemas of input validation.

* Change v3 API behaviors to v2 ones.
  On some APIs, there are different behaviors.
  For example, v3 "create a private flavor" API adds a flavor access for its
  own project automatically, but v2 one doesn't.

The following work item is not mandatory and it is one of wishlist.

* Change v3 plugin code path.
  e.g::

    nova/api/openstack/compute/plugins/v3/servers.py
    -> nova/api/openstack/compute/plugins/servers.py

Dependencies
============

None

Testing
=======

Tempest has already contained a lot of v2 API tests, and that is a good test
coverage now. For this v2.1 API, we need to run v2 API tests for both current
v2 and v2.1 in parallel. As an idea, we will add v2.1 API tests by inheriting
from the existing v2 API test classes and executing them against /v2.1.
A spec for this idea has been already proposed:

https://review.openstack.org/#/c/96661/

Documentation Impact
====================

The documentation for the v2 API will essentially remain the same as the API
will not change except for improvements in input validation. There will need
to be some updates on possible error status codes.

Longer term the improved infrastructure for input validation and the
development of JSON schema for response validation will make it much
easier to automate the generation of documentation for v2 rather relying
on the current mostly manual process.

References
==========

* Juno Mid-Cycle meetup https://etherpad.openstack.org/p/juno-nova-mid-cycle-meetup

* Juno design summit discussion https://etherpad.openstack.org/p/juno-nova-v2-on-v3-api-poc

* Mailing list discussions about the Nova V3 API and the maintenance
  overhead

  * http://lists.openstack.org/pipermail/openstack-dev/2014-March/028724.html
  * http://lists.openstack.org/pipermail/openstack-dev/2014-February/027896.html

* Etherpad page which discusses the V2 on V3 Proof of Concept and
  keeps track of the ongoing work.

  * https://etherpad.openstack.org/p/NovaV2OnV3POC

* Document about the problems with the V2 API

  * http://ozlabs.org/~cyeoh/V3_API.html

* Document describing the current differences between the V2 and V3 API

  * https://wiki.openstack.org/wiki/NovaAPIv2tov3
