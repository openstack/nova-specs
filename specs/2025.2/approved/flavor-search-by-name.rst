..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Search flavors by name
======================

https://blueprints.launchpad.net/nova/+spec/flavor-search-by-name

Allow users to search for flavor by name server-side.

Problem description
===================

Currently, there is no mechanism to filter flavors by flavor name using the
API. Instead, you must retrieve all flavors and filter manually. This can be
expensive, particularly when "flavor explosion" is taken into account. We would
like to resolve this by adding support for a ``name`` filter.

Use Cases
---------

* As a developer of client tooling, I would like to do as much filtering
  server-side as possible, in order to improve performance and reduce
  unnecessary network traffic.

Proposed change
===============

Modify the ``GET /flavors`` API to add support for a new ``name`` query string
filter parameter. This will support regex-style syntax, similar to many other
existing APIs such as ``GET /servers``. As with those APIs, this will default
to partial matches and a regular expression must be used to get exact matches.
For example:

.. code-block:: python

    >>> import openstack
    >>> conn = openstack.connect('devstack')
    >>> conn.compute.get('/flavors')
    >>>
    >>> [f['name'] for f in conn.compute.get(r'/flavors').json()['flavors']]
    ['m1.small', 'ci.m1.small', 'm1.medium', 'ci.m1.medium', 'm2.small', 'ds512M', 'ds1G']
    >>>
    >>> [f['name'] for f in conn.compute.get(r'/flavors?name=m1').json()['flavors']]
    ['m1.small', 'ci.m1.small', 'm1.medium', 'ci.m1.medium']
    >>>
    >>> [f['name'] for f in conn.compute.get(r'/flavors?name=^m1').json()['flavors']]
    ['m1.small', 'm1.medium']

This will be implemented by reusing the logic currently used for instances in
the ``_regex_instance_filter``, seen `here`__.

While we are introducing a new microversion, we will also take the opportunity
to address some other tech debt with the schema:

- We will set ``additionalProperties`` to ``False`` for the flavor show (``GET
  /flavors/{flavor_id}``) API

- We will remove the ``rxtx_factor`` field from the flavor create (``POST
  /flavors``), flavor list with details (``GET /flavors/detail``) and flavor
  show (``GET /flavors/{flavor_id}``) APIs. We will also remove ``rxtx_factor``
  from the list of valid sort keys for the flavor list (``GET /flavors``) and
  flavor list with details (``GET /flavors/detail``) APIs. This field was only
  supported by the long since removed XenAPI driver and is a no-op in modern
  Nova.

- We will remove the ``OS-FLV-DISABLED:disabled`` field from the flavor list
  with details (``GET /flavors/detail``) and flavor show (``GET
  /flavors/{flavor_id}``) APIs. There has never been a way to set this field,
  making it a no-op.

Finally, we will build on one of the above items and address some tech debt
with other schemas:

- We will set ``additionalProperties`` to ``False`` for all query string
  schemas.

- We will restrict all action bodies to ``null`` values except those where a
  value is actually expected.

.. __: https://github.com/openstack/nova/blob/41773f8c6515021eb037e6d9d385b34e89191c8c/nova/db/main/api.py#L1999-L2028

Alternatives
------------

We currently have to do this stuff client-side, which is less performant. We
could continue to do so.

Rather than supporting a regex syntax, we could opt for a simple partial match
filter, implemented using the SQL ``LIKE`` operator. This is currently used for
the ``hypervisor_hostname_pattern`` filter of the ``GET /os-hypervisors`` API
(ultimately by the ``compute_node_search_by_hypervisor`` DB API). This would be
slightly more performant, but it would be less expressive and would result in a
potentially surprising difference in behavior compared to most other APIs.

Regex support varies between our officially supported database backends,
MySQL/MariaDB and PostgreSQL, resulting in potential API behavioral differences
across deployments. We could investigate a subset of regex support that is
common across these backends and opt to support only this subset of patterns.
However, this is likely to be an involved, potentially complicated task that
would yield minimal benefit, given the `long-standing bias towards MySQL in
production deployments`__ and absence of perceived issues with other APIs that
already suffer from this issue. Deferring to the backend's regex support is
"good enough".

.. __: https://opendev.org/openstack/governance/commit/7999c374a391b6c702b9baafc6282649653e75a0

Data model impact
-----------------

None. The ``name`` field of the ``Flavors`` model already has a `unique
constraint`__ and is therefore indexed. In addition, we do not plan to remove
the ``rxtx_factor`` field from the ``Flavor`` o.v.o. We may wish to remove the
field from the ``Flavors`` model but that should likely be done in a future
release.

.. __: https://github.com/openstack/nova/blob/64ca204c9cf497b0dcfff2d3a24b0dd795a57d1d/nova/db/api/models.py#L231

REST API impact
---------------

* The ``GET /flavors`` API will be modified to add support for a new ``name``
  query string filter parameter in requests
* The ``POST /flavors`` API will be modified to remove support for the
  ``rxtx_factor`` parameter in requests.
* All flavors API will be modified to remove the ``rxtx_factor`` and
  ``OS-FLV-DISABLED:disabled`` fields from responses.
* All API that currently accept an unrestricted set of query string parameters
  will be modified to restrict these.
* All action APIs that currently restrict an unrestricted value in request
  bodies will be modified to only accept ``null``.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

openstackclient and third-party clients can take advantage of this when
filtering flavors.

Performance Impact
------------------

None. Clients will be faster since they can take advantage of server-side
filtering, but there should be no impact on the server itself since the field
is indexed.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephen.finucane

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  stephen.finucane

Work Items
----------

* Extend API and rework schemas as described above

Dependencies
============

None.

Testing
=======

We will provide new unit and functional tests, including API sample tests.

We will extend the Compute API schemas used in Tempest to reflect these
changes.

Documentation Impact
====================

Update API ref.

References
==========

None.
