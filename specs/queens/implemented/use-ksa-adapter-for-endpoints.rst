..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Use keystoneauth1 Adapter for endpoints
=======================================

`<https://blueprints.launchpad.net/nova/+spec/use-ksa-adapter-for-endpoints>`_

Endpoint and version discovery via keystoneauth1.Adapter have come
together in baked and usable form as of keystoneauth1 release 3.x.x, and
there is a drive to use these mechanisms consistently any time endpoint
discovery is needed. This effort aims to take advantage of Adapters to
make endpoint discovery consistent across Nova for the various services
it uses: identity (keystone), image (glance), block-storage (cinder),
network (neutron), baremetal (ironic), and placement.

.. note:: This is an evolving continuation of the effort begun via
          `blueprint use-service-catalog-for-endpoints`_.

Problem description
===================

Nova uses configuration parameters for API endpoints from the ``nova.conf``
file to communicate with other services within an OpenStack deployment.
This set of services includes:

* identity (keystone)
* image (glance)
* block-storage (cinder)
* network (neutron)
* baremetal (ironic)
* key-manager (barbican)
* placement

Today, there are a number of disparate ways in which service endpoints
are discovered and configured.  For example, different services use
different configuration keys for the same endpoint characteristic; e.g.
the endpoint URL can be specified to:

* baremetal as a single URIOpt called ``[ironic]api_endpoint``
* network as a single URIOpt called ``[neutron]url``
* image as a ListOpt of URL strings called ``[glance]api_servers``
  (which is in fact the *only* way the image service endpoint can be
  set)
* block-storage by a StrOpt template interpolated with values from the
  context object (``[cinder]endpoint_template``)
* key-manager as a single StrOpt called ``[barbican]barbican_endpoint``
* placement and identity not at all (no endpoint override is allowed)

The purpose of this effort is to expose within Nova a clean, consistent
mechanism for endpoint discovery; and to use that mechanism for all of
the services with which Nova communicates.

Use Cases
---------

As an Operator, I want a consistent way to configure endpoint discovery
for my services.

As a Developer maintaining code, I only want to learn one paradigm for
service endpoint setup and configuration.

As a Developer creating code that communicates with a new service, I
want to be able to employ the same paradigm as is used for other
services.

Proposed change
===============

The keystoneauth1 library provides a simple and consistent way to
configure endpoint discovery for a service.  A consumer of keystoneauth1
takes the following steps:

# In ``oslo_config`` setup, register conf options for keystoneauth1
  auth, Session, and Adapter objects via
  ``keystoneauth1.loading.register_*_conf_options``.
# Create an Adapter at runtime by chaining
  ``keystoneauth1.loading.load_*_from_conf_options`` for auth, Session,
  and Adapter, supplying those methods with the registered conf group.
  (Alternatively, an existing auth and/or Session may be supplied to the
  Adapter loader.)
# Use the resulting Adapter's discovery methods, such as
  ``get_endpoint``, as needed.

.. note:: It is also possible to use the Adapter directly for
          communication with the REST service via standard methods
          (``get``, ``post``, etc.).  Future efforts may be undertaken
          to eliminate custom per-service clients in favor of this
          mechanism.

From the Operator's perspective, this exposes a consistent way to
configure service endpoints.  For each service type, the configuration
options have the same names and semantics.  (For some service types, it
may be possible to obtain auth from context, thereby eliminating the
need for auth configuration.)

To make the Developer experience consistent, we propose to add a new
method ``get_ksa_adapter()`` in Nova.  To establish communication with
any other service, Nova will call this method and use the resulting
Adapter to discover endpoint data.  This method will use the
`service-types-authority`_ via `os-service-types`_ to map service type
names to their respective conf groups based on project name (e.g.
service type ``image`` maps to the ``glance`` project and therefore the
``[glance]`` conf group).

.. note:: At some point in the future, there should be an effort to
          rename conf groups from project names to their respective
          service type names.  That is outside the scope of this
          blueprint.

In the Queens cycle, the existing configuration options and discovery
mechanisms will continue to be supported.  If the legacy configuration
option is specified, it will take precedence; otherwise, the new
mechanism will be used.  This is to ensure backwards compatibility and a
smooth upgrade experience.  However, the old style options will be
deprecated in Queens and setting them will result in a warning being
logged. The deprecated legacy endpoint options will be removed in the
Rocky release.

The exception is ``[glance]api_servers``, which will continue to be
supported.  Operators need a way to specify a *list* of image service
endpoints, and there is no such mechanism available via keystoneauth1
Adapter.

If not otherwise specified via the ``valid_interfaces`` conf option,
keystoneauth1 defaults to trying, in order, ``public``, ``internal``,
``admin``.  The Nova implementation will override the default to trying
``internal``, then ``public``.  (It should be noted that ``publicURL``
is the form that has been used up until now, but ``public`` is the
keystone v3 version of interface. The config should accept both, but
the documentation attached to the conf options as exposed by
keystoneauth1 shows examples using ``public``.)

A Note About Barbican
---------------------
The Barbican configuration options are both supplied by and used from within
the castellan library.  It may be possible to override/deprecate those options
from Nova to shoehorn them into conforming to the standard of the remainder of
this spec.  However, the right way to make this happen is to have the castellan
project itself move toward common keystoneauth configuration.  There will
therefore be no effort in the scope of this specification to "fix" the
``[barbican]`` or ``[key_manager]`` conf sections.

Alternatives
------------

None

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

With some configurations (e.g. if ``endpoint_override`` is not
specified), endpoint discovery may entail additional API calls.  Every
effort will be made to limit these calls by caching the byproducts of
the discovery (the Adapter objects, the resulting clients, etc.) such
that, in the worst case, the impact will be felt once per service type
per endpoint version.

Other deployer impact
---------------------

The old endpoint configuration options, except for ``[glance]api_servers``,
will be deprecated in Queens and removed in Rocky.

Developer impact
----------------

None

Upgrade impact
--------------

A deployer upgrading to Queens is encouraged to transition her
configurations to use the new endpoint discovery mechanisms described in
this spec.  However, not doing so should result in no immediate
functional impacts.  Any existing endpoint-related conf options will
continue to work, but will begin to log deprecation warnings.
Configuration sections with no endpoint related conf options should
begin to use the new mechanisms seamlessly.

A deployer upgrading to Rocky will be *required* to transition to the
new conf mechanisms.  That impact will be further described in the Rocky
follow-on to this effort.

There is no upgrade impact on any database or REST API.  There are no
externally-visible behavior changes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Eric Fried (efried@us.ibm.com)

Other contributors:
  None

Work Items
----------

- Add utilities for consistent conf setup.  This is to centralize e.g.
  the override for ``valid_interfaces``.
- Modify the conf setup files for the existing services to

  - use these utilities and keystoneauth1.loading methods to register
    and list conf options for keystoneauth1 auth, Session, and Adapter
    objects.
  - deprecate the legacy options related to endpoint discovery (except
    for ``[glance]api_servers``).

- Add a utility method in Nova to create a keystoneauth1 Adapter from
  the conf.
- Update Nova code using endpoints to exploit the new utility method if the
  legacy conf options are not specified.
- (Rocky) Remove deprecated endpoint-related conf options, and the code
  branches that use them.

Dependencies
============

* keystoneauth1 3.2.0 or later
* os-service-types_ 1.1.0 or later
* service-types-authority_ (This is the language-agnostic data
  repository backing os-service-types.  It is not a pypi package, and
  has no place in the requirements project or Nova's
  ``requirements.txt``.)

Testing
=======

* Unit tests need to be added.
* Patches will be proposed in devstack and the devstack setup of other
  projects which remove the legacy endpoint-related conf options and/or
  specify the new ones.  These patches passing the various devstack
  gates will stand as proof that the new mechanisms work.  (Some of
  these patches may eventually be merged, though that is not a
  requirement in the scope of this spec.)

Documentation Impact
====================

* The sample conf file will be updated automatically by virtue of the
  changes to the various ``oslo_config`` setup modules.
* The admin, user, and install guides for the affected services will be
  scrubbed for references to the affected configuration options.

References
==========

.. _service-types-authority: https://service-types.openstack.org/
.. _os-service-types: https://github.com/openstack/os-service-types/blob/master/README.rst
.. _`blueprint use-service-catalog-for-endpoints`: https://blueprints.launchpad.net/nova/+spec/use-service-catalog-for-endpoints

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced (as `blueprint use-service-catalog-for-endpoints`_)
   * - Queens
     - Updated to reflect direction towards keystoneauth1 Adapter use
