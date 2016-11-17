..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Consistent Query Parameters Validation
======================================

https://blueprints.launchpad.net/nova/+spec/consistent-query-parameters-validation

Currently query parameters are validated ad-hoc in each API method in
inconsistent ways. It makes the API code hard to maintain and error-prone.
This spec aims to propose one consistent mechanism to validate query
parameters.

Problem description
===================

The API layer supports validating the input body of a request with json-schema.
There are mechanisms to support microversions of the schemas. There is no
centralized support, however, for validating query parameters leading to
inconsistent handling.

* Inconsistent query parameter validation in the API method. The similar query
  parameter have different validation. Or some query parameters are without any
  validation. For example, there are parameters that accept different datetime
  format between servers list API and simple_tenant_usage API. The
  `changes-since` in the server list accepts datetime with `ISO 8601 format`
  [1]. The `start`/`end` in the simple_tenant_usage accepts some custom
  format [2].

* Without looking deep into the code, the developers and users can't know which
  query parameters are supported by the API. And there are some query
  parameters that are just passed into the SQL query directly. For example, the
  value of `sort_key` for the server list API are pass into the DB layer
  directly.[3]

* The DB schema expose to the REST API directly. When the DB schema change,
  the API will be changed also. The same example as above. The value of
  `sort_key` passed to the DB layer directly, it leads to the internal
  attribute `__wrapper__` of DB object expose to the REST API.

Use Cases
---------

This is an effort about the refactor of the API layer code. It aims to ease the
burden of maintaining API code. The use-cases are for the developers of Nova:

* The developers need a consistent validation for the query parameters.
* The developers don't want to mix the validation code with the other API code
  together.
* The developers need a central place to declare the supported query
  parameters.

Finally the end-user will get benefits as below:

* Consistent query parameter validation.
* Stable API, the API won't be changed by under-layer DB schema change anymore.

Proposed change
===============

This spec proposes to use JSON-schema to extract the validation of query
parameters out of API code.

The JSON-schema is a familiar tool for the developers also, so it's good to
build new mechanism based on that.

For using JSON-schema to validate the query parameters, it needs to convert
the query parameters to a flat JSON data. For example, there are three
query parameters:

* `name` accepts a regex string. It only can be specified one times.
* `sort_key` can accept a string, the valid string are `created_at` and
  `updated_at`. It can be specified multiple times.
* `deleted` is boolean value and only can be specified one times.

The request as below::

    The request:
     GET http://openstack.example.com/v2.1/servers?name=abc&sort_key=created_at&sort_key=updated_at&deleted=True

The query parameters convert to a flat JSON data::

    {
        'name': ['^abc'],
        'sort_key': ['created_at', 'updated_at']
        'deleted': ['True']
    }

This flat JSON data can be validated by the JSON-schema directly, the
corresponding JSON-schema as below::

    {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'array',
                'items': {'type': 'string', 'format': 'regex'},
                'maxItems': 1
            }
            'sort_key': {
                'type': 'array',
                'items': {'type': 'string',
                          'enum': ['created_at', 'updated_at']}
            },
            'deleted': {
                'type': 'array',
                'items': parameter_types.boolean,
                'maxItems': 1
        }
        'additionalProperties': False,
    }


For reducing the copy/paste, two macro functions are introduced::

    {
        'type': 'object'
        'properties': {
            'name': single_param({'type': 'string', 'format': 'regex'})
            'sort_key': multi_params({'type': 'string', 'enum': ['created_at', 'updated_at']}),
            'deleted': single_param(parameter_types.boolean)
        }
        'additionalProperties': False
    }

The schema will be attached to each API by an new decorator::

    @validation.query_params_schema(schema, min_version, max_version)

The supported microversion range for a given json-schema can be specified in
the decorator. The usage of decorator is same with the body jsons-schema
decorator.

If there is schema matched the request version, the 400 will be returned when
validation failed.

The behaviour `additionalProperties` as below:

* When the value of `additionalProperties` is `True` means the extra query
  parameters are allowed. But those extra query parameters will be stripped
  out.
* When the value of `additionalProperties` is `False` means the extra query
  aren't allowed.

The value of `additionalProperties` will be `True` until we decide to restrict
the parameters in the future, and it will be changed with new microversion. For
now we still need to enable the random input in the query string. But the
extra parameters will be stripped out for protecting the system. Also for
matching the current behaviour, we need to enable multiple values for all the
parameters(using the macro function 'multi_params' to extract the schema for
multiple values). For the legacy v2 API mode, the value of
`additionalProperties` should be `True` also, it makes the legacy v2 API mode
under the protection also.

The current API only accepts one value for single value parameter when the
API user specified multiple values in the request. Only the accepted value
will be validated. The new validation mechanism supports multiple value
parameters. The difference is that the new mechanism will validate all the
values even only one accepted. But thinking of this is rare case, so it is
acceptable.

Alternatives
------------

If we keep everything as before, the code of query parameter validation will
be hard to maintain. It leads to hide the bug for query parameters.

Data model impact
-----------------

None

REST API impact
---------------

This proposal will use the keypairs API as example. For using the json-schema
to validate query parameters for other APIs will be in other proposal.

In the keypairs API,new query parameters were added in Microversion 2.10
and 2.35. For example, the decorator will be added for index method as below::

    schema_v2_1 = {
        'type': 'object',
        'properties': { }
        'additionalProperties': True
    }

    schema_v2_10 = copy.deepcopy(schema_v2_1)
    schema_v2_10['properties'] = {'user_id': multi_params({'type': 'string'}}

    schema_v2_35 = copy.deepcopy(schema_v2_10)
    schema_v2_35['properties']['limit'] = multi_params(
        {'type': 'string', 'format': 'integer'})
    schema_v2_35['properties']['marker'] = multi_params({'type': 'string'})
    @validation.query_params_schema(schema_v2_35, '2.35')
    @validation.query_params_schema(schema_v2_10, '2.10', '2.34')
    @validation.query_params_schema(schema_v2_1, '2.0', '2.9)
    def index(req):
        ....

The Keypairs API behaviour is as below:

For `GET /keypairs?user_id=1&user_id=2`

* Past: accept, but we ignore the `user_id=2`
* Now: accept, but we ignore `user_id=2`
* Future: return 400 after new microversion added

For `GET /keypairs?limit=abc`

* Reject, the value should be integer

For `GET /keypairs?limit=abc&limit=1`

* Past: accept, ignore the `limit=abc`
* Now: reject, all the values of `limit` should be integer
* Future: reject, only single value can be specified.

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

This proposal improves the maintainability of the API code.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Alex Xu <hejie.xu@intel.com>

Other contributors:
  ZhenYu Zheng <zhengzhenyu@huawei.com>

Work Items
----------

* Introduce the new decorator to enable the json-schema for query parameters
* Use json-schema for query parameters validation in the keypairs API.

Dependencies
============

None

Testing
=======

The unittest and function test are required to ensure the new mechanism work
as expected. When using the new mechanism instead of the existed query
parameters process, the existed unitest and function still can pass the tests.

Documentation Impact
====================

The developer reference needs to describe how to use the new mechanism.

References
==========

[1] https://github.com/openstack/nova/blob/00bc0cb53d6113fae9a7714386953d1d75db71c1/nova/api/openstack/compute/servers.py#L244

[2] https://github.com/openstack/nova/blob/00bc0cb53d6113fae9a7714386953d1d75db71c1/nova/api/openstack/compute/simple_tenant_usage.py#L178

[3] https://github.com/openstack/nova/blob/00bc0cb53d6113fae9a7714386953d1d75db71c1/nova/api/openstack/common.py#L145

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
