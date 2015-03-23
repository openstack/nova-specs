..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support JSON-Home for API discoverability
==========================================

https://blueprints.launchpad.net/nova/+spec/nova-api-json-home

Nova needs to provide a standard API discovery way to clients.
This spec proposes JSON-Home as the way.

Problem description
===================

Now Nova API provides available API list via "list extensions" API, but the
way is Nova-specific and that is not a standard way. In addition, clients
cannot know available API resource URLs from the result of "list extensions"
only and client developers need to investigate Nova implementation, because
the result doesn't show available API resource URLs directly.
From the point of view of whole OpenStack projects, the ways are not consistent
and application programmers should write an application for handling these APIs
by different ways.

Use Cases
----------

End users can know what APIs are available on a cloud service and how to access
these features by a common way. For example, end users can get available REST
URLs(v2/{project-id}/servers, etc) by passing 'application/json-home' in an
accept header with GET method.
Developers can get full set of REST URLs including details such as available
methods (GET/POST/PUT etc) and create API documents based on the information.
Ideally it is the best to generate API documents automatically from this
feature.

Project Priority
-----------------

None.

Proposed change
===============

JSON-Home is a standard, and Keystone has already implemented JSON-Home on
Keystone REST API [1]_. This spec/blueprint proposes JSON-Home support for Nova
v2.1 API.

On JSON-Home spec [2]_, JSON-Home works only if passing 'application/json-home'
in an accept header. If nova-api receives it, nova-api provides available REST
URLs to a client with JSON-Home format. For example, nova-api will provide
the following data if a client "GET /v2.1" with an accept header
'application/json-home':

::

 {
   "resources": {
     "http://docs.openstack.org/api/openstack-compute/2.1/rel/servers": {
       "href-template": "/v2.1/{project_id}/servers",
       "href-vars": {
         "project_id": "http://docs.openstack.org/api/openstack-compute/2.1/param/project_id"
       }
     },
     "http://docs.openstack.org/api/openstack-compute/2.1/rel/flavors": {
       "href-template": "/v2.1/{project_id}/flavors",
       "href-vars": {
         "project_id": "http://docs.openstack.org/api/openstack-compute/2.1/param/project_id"
       }
     },
     [..]
   }
 }

The keys of the resources property are link relationship types. A relationship
type needs to be chosen for the key. There are several relationship types
registered with IANA, but there's none designated for compute API resources.
If a group doesn't want to register a relation with IANA (see section 4.2
"Extension Relation Types" in RFC 5988 [3]_ ), they can use some unique URL
instead.
An application could potentially fetch this URL to get information about the
relationship, so we should pick one that could potentially be used to serve up
some info about what the relationship is and describe the resource.
Keystone publishes http://docs.openstack.org/api/openstack-identity/3/rel as
it. In addition, Nova has already published its XSD files at
http://docs.openstack.org/api/openstack-compute/2/xsd. So Nova should publish
a similar location for consistency. For v2.1 resources, the relationship type
link will be http://docs.openstack.org/api/openstack-compute/2.1/rel as the
above sample. On v2.1 API + microversions, we will continue using the same
endpoint(/v2.1) and we can use the same link for all microversions.

If querying against a specific URL(eg. GET /v2.1/{project_id}/servers), client
can get more detail information(available HTTP methods, format) on "hints"
attribute like:

::

 {
   "resources": {
     "http://docs.openstack.org/api/openstack-compute/2.1/rel/servers": {
       "href-template": "/v2.1/{project_id}/servers",
       "href-vars": {
         "project_id": "http://docs.openstack.org/api/openstack-compute/2.1/param/project_id"
       },
       "hints": {
         "allow": ["GET", "POST", "PUT", "DELETE"],
         "formats": {
             "application/json": {}
         },
         "accept-post": ["application/json"],
         "accept-put": ["application/json"]
       }
     }
   }
 }

"hints" attributes can contain "status" also and that would be useful for
backwards incompatible changes because "status" can show "deprecated".
For example, the following case is we want to change API URL from
"/v2.1/{project_id}/old-resource" to "/v2.1/{project_id}/new-resource":

::

 {
   "resources": {
     "http://docs.openstack.org/api/openstack-compute/2.1/rel/old-resource": {
       "href-template": "/v2.1/{project_id}/old-resource",
       "hints": {
         "status": "deprecated",
         "allow": ["GET", "POST", "PUT", "DELETE"],
       },
       [..]
     },
     "http://docs.openstack.org/api/openstack-compute/2.1/rel/new-resource": {
       "href-template": "/v2.1/{project_id}/new-resource",
       "hints": {
         "allow": ["GET", "POST", "PUT", "DELETE"],
       },
       [..]
     }
   }
 }

Current JSON-Home(draft-03) doesn't cover the feature which can provide
request/response body formats. So on this spec, Nova will provide API URLs
and HTTP methods only without these formats.
On openstack-dev ML discussion, we have an idea which provides JSON-Schema
API definitions with "hints" of JSON-Home (JSON-Schema on JSON-Home) as an
OpenStack specific feature. However, the feature is out of scope from this
spec and this spec covers the standard scope of JSON-Home without JSON-Schema.
The feature needs the other spec and we need to discuss it across projects.

The API router class already contains necessary information for JSON-Home,
and we can implement JSON-Home feature just by arranging the information to
JSON-Home format and publishing it to a client.

On v2.1 + microversions, we will be able to add/remove API URLs and request/
response bodies. This JSON-Home feature provides available API URLs of each
microversion which is specified with "X-OpenStack-Nova-API-Version" in a
header. If not specifying a microversion, this feature provides available API
URLs of minimum microversion. "JSON-Schema on JSON-Home" will provide available
request/response bodies of the specified microversion also based on the same
semantic.

Alternatives
------------

There is already "list extensions" API for getting available extension list,
but the list is not common format and it is necessary to pay implementation
cost on client sides if API extension discovery is necessary.

Data model impact
-----------------

None.

REST API impact
---------------

* Specification for the method

  * Description

    * API extension discovery

  * Method type

    * GET

  * Normal http response code

    * HTTP200(OK). This is the same as Keystone's one.

  * Expected error http response code(s)

    * HTTP404(NotFound). If the specified API URL doesn't exist.

  * URL for the resource

    * /v2.1 and under

  * JSON schema definition for the body data if allowed

    * A request body is not allowed.

  * JSON schema definition for the response data if any

::

 {
     'type': 'object',
     'properties': {
         'resources': {
             'type': 'object',
             'patternProperties': {
                 '^http://docs.openstack.org/api/openstack-compute/.*$': {
                     'type': 'object',
                     'properties': {
                         'href': {'type': 'string'},
                         'href-template': {'type': 'string'},
                         'href-vars': {'type': 'object'},
                         'hints': {'type': 'object'}
                     },
                     'oneOf': [
                         {'required': ['href']},
                         {'required': ['href-template']}
                     ],
                     'additionalProperties': False
                 }
             }
         }
     },
     'required': ['resources'],
     'additionalProperties': False
 }

Security impact
---------------

None.
The API URLs is public information.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.
This feature provides static data only to clients, so Nova doesn't need to
pay performance cost.

Other deployer impact
---------------------

None.

Developer impact
----------------

This feature should be implemented from the API routing information which is
stored in API router. So developers don't need to implement any code only for
this feature, the maintenance cost will be nothing for this feature.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  oomichi

Other contributors:
  None

Work Items
----------

* Add a method for translating API routing info to JSON-Home format.
* Add an accept header handling method for a JSON-Home request.

Dependencies
============

None.

Testing
=======

Keystone has already implemented this feature and Keystone team has a plan
to implement Tempest test for JSON-Home.
Ideally, this feature of Nova will use the same Tempest test mechanism as
Keystone and test JSON-Home on the gate. If we do that, we can reduce the
test code on Tempest and verify consistent JSON-Home across projects.

Documentation Impact
====================

None yet.
We can get API URLs, HTTP methods (GET, POST, ..) with this feature, but API
documents needs request/response body formats also and this spec doesn't
cover it as the first step. The feature which provides request/response body
formats will be discussed on the other spec across projects. After that we
will be able to get API documents with the same way on different projects,
that will be ideal situation.

References
==========

.. [1] https://github.com/openstack/keystone-specs/blob/master/specs/juno/json-home.rst
.. [2] http://tools.ietf.org/html/draft-nottingham-json-home-03
.. [3] http://tools.ietf.org/html/rfc5988#section-4.2
