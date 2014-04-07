..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Create JSON Schema definitions for Nova v3 API
==============================================

https://blueprints.launchpad.net/nova/+spec/v3-api-schema

Complete JSON Schema definitions for Nova v3 API request bodies.

Problem description
===================

Nova contains a lot of RESTful API, but not all API parameters of a request
body are completely validated. To validate all parameters, an API validation
framework has been implemented with JSON Schema library.
After that, we needed to add JSON Schema definitions for each API but we could
not complete them in Icehouse cycle.
In Juno cycle, we need to implemented strong validation for v2.1 API as the
design summit discussion. That means we need to implement strong validation
for v3 API because v2.1 API is implemented on the top of v3 API implementation.

Proposed change
===============

Each API definition should be added with the following ways:

* Create definition files under ./nova/api/openstack/compute/schemas/v3/.
* Each definition should be described with JSON Schema.
* Each parameter of definitions(type, minLength, etc.) can be defined from
  current validation code, DB schema, unit tests, Tempest code, or so on.
* Reuse the existing predefined parameter types(name, hostname, boolean, etc.)
  in nova/api/validation/parameter_types.py as possible.

Alternatives
------------

Before the API validation framework, we needed to add the validation code into
each API method in ad-hoc. These changes would make the API method code dirty
and we needed to create multiple patches due to incomplete validation.
For example, "create a flavor extraspec" API has been changed twice in Icehouse
for its validation:

* Enforce FlavorExtraSpecs Key format.
  http://git.openstack.org/cgit/openstack/nova/commit/?id=050ce0e5891ba816baaef

* Fix the validation of flavor_extraspecs v2 API
  http://git.openstack.org/cgit/openstack/nova/commit/?id=8010c8faf9f030d2c0264

If using JSON Schema definitions instead, acceptable request formats are clear
and we don't need to do this ad-hoc works in the future.

* Why not Pecan

  Some projects(Ironic, Ceilometer, etc.) are implemented with Pecan/WSME
  frameworks and we can get API documents automatically from the frameworks.
  In WSME implementation, the developers should define API parameters for
  each API. Pecan would make the implementations of API routes(URL, METHOD)
  easy. And API documentation is generated from the combinations of these
  definitions.
  In Icehouse summit, Nova team decided to pick Pecan as Nova v3 API framework
  with JSONSchema instead of WSME. because Nova contains complex APIs (API
  extensions) and WSME could not cover them. In addition, Pecan implementation
  (https://blueprints.launchpad.net/nova/+spec/v3-api-pecan) also was difficult
  in the development and not completed. So now, Nova v3 API is implemented with
  Nova's original WSGI framework and JSONSchema, we cannot use Pecan.

Data model impact
-----------------

None

REST API impact
---------------

By applying strict validation to every APIs, some values which are accepted
in v2 API will be denied in v3 API. For example, here picks the server name
of "create a server" API up.
The string pattern of the server name is not validated in v2 API at all. We
can specify UTF-8(non-ascii) characters as a server name through v2 API now.
For strong/comprehensive validation, we will apply the predefined parameter
type "name" to the server name also. The types allows "a-zA-Z0-9. _-" only as
the string pattern and denies UTF-8 characters. In the worst cases we could
relax input validation for names.

Security impact
---------------

Better up front input validation will reduce the ability for malicious user
input to exploit security bugs.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Nova will need some performance cost for this comprehensive validation, because
the checks will be increased for API parameters which are not validated now.
However, I believe this is necessary cost for public REST APIs and we need to
pay it.

Other deployer impact
---------------------

None

Developer impact
----------------

Developers, who implement a new REST API, need to add JSON Schema definitions
as the part of an API implementation.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  oomichi

Other contributors:
  aikawa
  takada-yuiko
  xu-haiwei

Work Items
----------

This task requires a lot of patches, and the progress management is the key.
They are tracked on https://etherpad.openstack.org/p/nova-v3-api-validation
Now the implementations of most APIs have been done except some new APIs (
instance-group and server-external-events) and we need to review them.


Dependencies
============

* If porting nova-network to v3 API, we need to create some JSON Schema patces
  for it.


Testing
=======

Through this implementation, we need to improve the unit test coverage from
the viewpoint of negative request cases. Current unit tests don't cover every
negative cases and we will be able to add them because of making valid request
format clear.
In addition, we will be able to find original unit test bugs through this work.
We have fixed some bugs of unit tets in Icehouse:

* Fix the sample and unittest params of v3 scheduler-hints
  http://git.openstack.org/cgit/openstack/nova/commit/?id=b699c703e00eda1c8368b

* Fix the flavor_ref type of unit tests
  http://git.openstack.org/cgit/openstack/nova/commit/?id=5191576c279dc9905e881

* Change evacuate test hostnames to preferable ones
  http://git.openstack.org/cgit/openstack/nova/commit/?id=9888f61128ed82d15d074

Now Tempest contains the negative test generator. The generator operates the
negative tests automatically based on the API definitions which are described
with JSON Schema. By porting the API definitions of this blueprint from Nova
to Tempest, we can improve the test coverage of Tempest also.


Documentation Impact
====================

In long term, I hope this API definitions are used for API specification
document auto-genaration also. We can get the trustable API document and
it would be good for users and developers.
As the first step, I have submitted the blueprint for generating API sample
files from the API definitions. This is out of the scope of this description
but I pick it up as a useful sample:
https://blueprints.launchpad.net/nova/+spec/generate-api-sample-from-api-schema

* Why not current template files

  API samples are generated from template files which are fixed format like::

    {
        "evacuate": {
            "host": "%(host)s",
            "admin_password": "%(adminPass)s",
            "on_shared_storage": "%(onSharedStorage)s"
        }
    }

  API developers should write this kind of template file for API implementation
  and they should generate API sample files from them.
  As the result, API implementation review has many files and sometime these
  files were wrong at broken indents, non-existent parameters(typo, etc.).
  To improve this situation, I proposed to use JSONSchema definitions instead
  of the template files. After that, we can remove the template files and
  reviews will be more easy.

References
==========

* Links to mailing list

  * [Nova] What validation feature is necessary for Nova v3 API
    http://lists.openstack.org/pipermail/openstack-dev/2013-October/016649.html

* Links to notes from a summit session

  * API Validation for the Nova V3 API
    https://etherpad.openstack.org/p/icehouse-summit-nova-pecan-wsme
