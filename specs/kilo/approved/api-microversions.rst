..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
REST API Microversion Support
==========================================

https://blueprints.launchpad.net/nova/+spec/api-microversions

We need a way to be able to introduce changes to the REST API to both
fix bugs and add new features. Some of these changes are backwards
incompatible and we currently have no way of doing this.

Problem description
===================

As a community we are really good at evolving interfaces and code over
time via incremental development. We've been less good at giant big
bang drops of code. The Nova API has become sufficiently large, and
constantly growing through new extensions, that it's not likely to be
able to ever do a new major version of the API because of the impact
on users and overhead for developers of supporting multiple
implementations.

At the same time the current situation where we allow innovation in
the API through adding extensions, has grown to the point where we now
have extensions to extensions, under the assumption that the extension
list is a poor man's versioning mechanism. This has led to large
amounts of technical debt. It prevents us from making certain changes,
like deprecating pieces of the API that are currently non sensible or
broken. Or fixing other areas where incremental development has led to
inconsistencies in the API which is confusing for new users.

We must come up with a better way that serves the following needs:

- Makes it possible to evolve the API in an incremental manner, which
  is our strength as a community.
- Provides backwards compatibility for users of the REST API.
- Provides cleanliness in the code to make it less likely that we'll
  do the wrong thing when extending or modifying the API.

A great interface is one that goes out of it's way to makes it hard to
use incorrectly. A good interface tries to be a great interface, but
bends to the realities of the moment.

Use Cases
----------

* Allows developers to modify the Nova API in backwards compatible
  way and signal to users of the API dynamically that the change is
  available without having to create a new API extension.

* Allows developers to modify the Nova API in a non backwards
  compatible way whilst still supporting the old behaviour. Users of
  the REST API are able to decide if they want the Nova API to behave
  in the new or old manner on a per request basis. Deployers are able
  to make new backwards incompatible features available without
  removing support for prior behaviour as long as there is support
  to do this by developers.

* Users of the REST API are able to, on a per request basis, decide
  which version of the API they want to use (assuming the deployer
  supports the version they want).

Project Priority
-----------------

The kilo priorities list is currently not defined. However under the
currently proposed list of priorities it would fall under "User
Experience" as it significantly increases the ability for us to
improve the Nova API.

Proposed change
===============

Design Priorities:

* How will the end users use this, and how to we make it hard to use
  incorrectly

* How will the code be internally structured. How do we make it:

    * Easy to see in the code that you are about to break API compatibility.
    * Make it easy to make backwards compatible changes
    * Make it possible to make backwards incompatible changes
    * Minimise code duplication to minimise maintenance overhead

* How will we test this both for unittests and in integration. And
  what limits does that impose.

Versioning
----------

For the purposes of this discussion, "the API" is all core and
optional extensions in the Nova tree.

Versioning of the API should be a single monotonic counter. It will be
of the form X.Y where it follows the following convention:

* X will only be changed if a significant backwards incompatible
  API change is made which affects the API as whole. That is, something
  that is only very very rarely incremented.
* Y when you make any change to the API. Note that this includes
  semantic changes which may not affect the input or output formats or
  even originate in the API code layer. We are not distinguishing
  between backwards compatible and backwards incompatible changes in
  the versioning system. It will however be made clear in the
  documentation as to what is a backwards compatible change and what
  is a backwards incompatible one.


Note that groups of similar changes across the API will not be made
under a single version bump. This will minimise the impact on users as
they can control changes that they want to be exposed to.

A backwards compatible change is defined as one which would be allowed
under the OpenStack API Change Guidelines

http://wiki.openstack.org/wiki/APIChangeGuidelines

A version response would look as follows

::

    GET /
    {
         "versions": [
            {
                "id": "v2.1",
                "links": [
                      {
                        "href": "http://localhost:8774/v2/",
                        "rel": "self"
                    }
                ],
                "status": "CURRENT",
                "version": "5.2"
                "min_version": "2.1"
            },
       ]
    }

This specifies the min and max version that the server can
understand. min_version will start at 2.1 representing the v2.1 API
(which is equivalent to the V2.0 API except for XML support). It may
eventually be increased if there are support burdens we don't feel are
adequate to support.

Client Interaction
-----------------------

A client specifies the version of the API they want via the following
approach, a new header::

  X-OpenStack-Nova-API-Version: 2.114

This conceptually acts like the accept header. This is a global API
version.

Semantically this means:

* If X-OpenStack-Nova-API-Version is not provided, act as if min_version was
  sent.

* If X-OpenStack-Nova-API-Version is sent, respond with the API at that
  version. If that's outside of the range of versions supported,
  return 406 Not Acceptable.

* If X-OpenStack-Nova-API-Version: latest (special keyword) return
  max_version of the API.

This means out of the box, with an old client, an OpenStack
installation will return vanilla OpenStack responses at v2. The user
or SDK will have to ask for something different in order to get new
features.

Two extra headers are always returned in the response:

X-OpenStack-Nova-API-Version: version_number, experimental
Vary: X-OpenStack-Nova-API-Version

The first header specifies the version number of the API which was
executed. Experimental is only returned if the operator has made a
modification to the API behaviour that is non standard. This is only
intended to be a transitional mechanism while some functionality used
by cloud operators is upstreamed and it will be removed within a small
number of releases..

The second header is used as a hint to caching proxies that the
response is also dependent on the X-Openstack-Compute-API-Version and
not just the body and query parameters. See RFC 2616 section 14.44 for
details.

Implementation design details
-----------------------------

On each request the X-OpenStack-Nova-API-Version header string will be
converted to an APIVersionRequest object in the wsgi code. Routing
will occur in the usual manner with the version object attached to the
request object (which all API methods expect). The API methods can
then use this to determine their behaviour to the incoming request.

Types of changes we will need to support::

* Status code changes (success and error codes)
* Allowable body parameters (affects input validation schemas too)
* Allowable url parameters
* General semantic changes
* Data returned in response
* Removal of resources in the API
* Removal of fields in a response object or changing the layout of the response

Note: This list is not meant to be an exhaustive list

Within a controller case, methods can be marked with a decorator
to indicate what API versions they implement. For example::

::

>  @api_version(min_version='2.1', max_version='2.9')
>  def show(self, req, id):
>     pass
>
>  @api_version(min_version='3.0')
>  def show(self, req, id):
>     pass

An incoming request for version 2.2 of the API would end up
executing the first method, whilst an incoming request for version
3.1 of the API would result in the second being executed.

For cases where the method implementations are very similar with just
minor differences a lot of duplicated code can be avoided by versioning
internal methods intead. For example::


>   @api_version(min_version='2.1')
>   def _version_specific_func(self, req, arg1):
>      pass
>
>   @api_version(min_version='2.5')
>   def _version_specific_func(self, req, arg1):
>      pass
>
>   def show(self, req, id):
>      .... common stuff ....
>      self._version_specific_func(req, "foo")
>       .... common stuff ....


Reducing the duplicated code to a minimum minimises maintenance
overhead. So the technique we use would depend on individual
circumstances of what code is common/different and where in the method
it is.

A version object is passed down to the method attached to the request
object so it is also possible to do very specific checks in a
method. For example::

> def show(self, req, id):
>    .... stuff ....
>
>    if req.ver_obj.matches(start_version, end_version):
>      .... Do version specific stuff ....
>
>    ....  stuff ....


Note that end_version is optional in which case it will match any
version greater than or equal to start_version.

Some prototype code which explains how this work is available here:

https://github.com/cyeoh/microversions_poc

The validation schema decorator would also need to be extended to support
versioning

@validation.schema(schema_definition, min_version, max_version)

Note that both min_version and max_version would be optional
parameters.

A method, extension, or a field in a request or response can be
removed from the API by specifying a max_version.

>  @api_version(min_version='2.1', max_version='2.9')
>  def show(self, req, id):

If a request for version 2.11 is made by a client, the client will
receive a 404 as if the method does not exist at all. If the minimum
version of the API as whole was brought up to 2.10 then the extension
itself could then be removed.

The minimum version of the API as a whole would only be increased by a
consensus decision between Nova developers who have the ovehead of
maintaining backwards compatibility and deployers and users who want
backwards compatibility forever.

Because we have a monotonically increasing version number across the
whole of the API rather than versioning individual plugins we will have
potential merge conflicts like we currenty have with DB migration
changesets. Sorry, I don't believe there is any way around this, but
welcome any suggestions!


Client Expectations
-------------------

As with system which supports version negotiation, a robust client
consuming this API will need to also support some range of versions
otherwise that client will not be able to be used in software that
talks to multiple clouds.

The concrete example is nodepool in OpenStack Infra. Assume there is a
world where it is regularly connecting to 4 public clouds. They are
at the following states::

  - Cloud A:
    - min_ver: 2.100
    - max_ver: 2.300
  - Cloud B:
    - min_ver: 2.200
    - max_ver: 2.450
  - Cloud C:
    - min_ver: 2.300
    - max_ver: 2.600
  - Cloud D:
    - min_ver: 2.400
    - max_ver: 2.800

No single version of the API is available in all those clouds based on
the ancientness of some of them. However within the client SDK certain
basic functions like boot will exist, though might get different
additional data based on version of the API. The client should smooth
over these differences when possible.

Realistically this is a problem that exists today, except there is no
infrastructure to support creating a solution to solve it.


Alternatives
------------

One alternative is to make all the backwards incompatible changes at
once and do a major API release. For example, change the url prefix to
/v3 instead of /v2. And then support both implementations for a long
period of time. This approach has been rejected in the past because of
concerns around maintance overhead.

Data model impact
-----------------

None

REST API impact
---------------

As described above there would be additional version information added
to the GET /. These should be backwards compatible changes and I
rather doubt anyone is actually using this information in practice
anyway.

Otherwise there are no changes unless a client header as described is
supplied as part of the request.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

SDK authors will need to start using the X-OpenStack-Nova-API-Version header
to get access to new features. The fact that new features will only be
added in new versions will encourage them to do so.

python-novaclient is in an identical situation and will need to be
updated to support the new header in order to support new API
features.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

This will obviously affect how Nova developers modify
the REST API code and add new extensions.

FAQ
---

* Does adding a new plugin change the version number?
  Yes.

* Do we bump a version number when error status codes change?
  Yes, its is an API change.



Implementation
==============

Assignee(s)
-----------


Primary assignee:
  cyeoh-0

Other contributors:
  <launchpad-id or None>

Work Items
----------

* Implement APIVersions class
* Implement handling of X-OpenStack-Nova-API-Version header
* Implement routing of methods called based on version header.
* Find and implement first API change requiring a microversion bump.


Dependencies
============

* This is dependent on v2.1 v2-on-v3-api spec being completed.

* Any nova spec which wants to make backwards incompatible changes
  to the API (such as the tasks api specification) is dependent on
  on this change. As is any spec that wants to make any API change
  to the v2.1 API without having to add a dummy extension.

* JSON-Home is related to this though they provide different
  services. Microversions allows clients to control which version of
  the API they are exposed to and JSON-Home describes that API
  allowing for resource discovery.

Testing
=======

It is not feasible for tempest to test all possible combinations
of the API supported by microversions. We will have to pick specific
versions which are representative of what is implemented. The existing
Nova tempest tests will be used as the baseline for future API
version testing.

Documentation Impact
====================

The long term aim is to produce API documentation at least partially
automated using the current json schema support and future JSON-Home
support. This problem is fairly orthogonal to this specification
though.

References
==========

* https://etherpad.openstack.org/p/kilo-nova-microversions
