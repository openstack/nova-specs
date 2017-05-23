..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Use service catalog to get endpoint URLs
========================================

`<https://blueprints.launchpad.net/nova/+spec/use-service-catalog-for-endpoints>`_

Make use of service catalog to find endpoint URLs instead of reading
from nova configuration file.


Problem description
===================

Nova uses configuration parameters for API endpoints from the ``nova.conf``
file to communicate with other services within an OpenStack deployment.
This set of services primarily includes service like Glance, Cinder and
Neutron.

Ideally, these API endpoints should not be hardcoded. We should have a simple
and consistent way to retrieve these endpoint URLs in Nova.

This spec focuses on using the Keystone service catalog to get API endpoints
when Nova interacts with Cinder, Glance, Neutron, and others.

The service catalog is composed of a list of services which represent services
in an OpenStack deployment. Each service has one or more endpoints associated
with it.

Use Cases
---------

As an operator, I want to configure the service catalog and have my services
use that to interact with each other so I don't have to individually manage
inter-project connections separately.

Proposed change
===============

The service catalog offers list of all available services along with
additional information about regions, API endpoints and API versions.
It is useful to efficiently find information about services such as how to
configure communication between services.

Currently, Nova uses configuration settings from ``nova.conf`` file to get
endpoint URLs. Each service has options in ``nova.conf`` which represent
service endpoints or (e.g. in the case of cinder) ways to discover them.
The option names and formats are different for each group. For example,
in ``nova.conf``, there are options like::

   [glance]
   api_servers = http://127.0.0.1:9292,http://glance2:9292
   [neutron]
   url = http://127.0.0.1:9696
   [ironic]
   api_endpoint = http://127.0.0.1:6385
   [cinder]
   catalog_info = volumev3:cinderv3:publicURL

Keystoneauth provides a simple and consistent way to get API endpoints from the
Keystone service catalog instead of configuring it in a conf file.

To make retrieving API endpoints consistent, we can add a new method
``get_service_url()`` in Nova. To establish communication with any other
service, Nova will call this method to find API endpoints.

The method will first look at the existing configuration options such as
``[neutron]url`` and use these options if they exist in the configuration file.
This is to ensure backwards compatibility and a smooth upgrade experience.
However, the old style options will be deprecated in Pike and setting them will
result in a warning being logged. The old deprecated endpoint options will be
removed in the Queens release.

The exception is ``[glance]api_servers``, which will continue to be supported.
Glance needs a way to specify a *list* of service endpoints, and there is no
such mechanism available via the service catalog.

If the existing configuration option is *not* found or has no value, then the
method will look up the API endpoint corresponding to the conf group from the
Keystone service catalog using ``keystoneauth``.

Conf groups supporting ``get_service_url()`` will include the following set of
options, based on ``keystonauth1.adapter.Adapter``:

- ``service_type``
- ``service_name``
- ``interface``
- ``region_name``
- ``endpoint_override``

If ``service_type`` is not supplied, a mapping from conf group name to
corresponding service types will be consulted, and each will be tried
successively until a result is found. (This mapping may be hardcoded
initially, but should ultimately move to using ``os-client-config`` or
``service-types-authority``.)

For example, a subset of the default mapping might be::

  {
      'glance': ['image'],
      'cinder': ['block-storage', 'volumev3', 'volumev2', 'volume'],
      'ironic': ['baremetal'],
      'neutron': ['network'],
  }

If ``get_service_url()`` is invoked for conf group ``cinder`` and
``[cinder]service_type`` is empty or missing from the conf, the method will
attempt lookup with ``service_type='block-storage'``, then
``service_type='volumev3'``, etc.

If ``interface`` is not supplied, ``internal``, ``admin``, and
``public`` will be tried successively until a result is found. (It
should be noted that ``publicURL`` is the form that has been used up
until now, but ``public`` is the keystone v3 version of interface. The
config should accept both, but documentation should be updated to show
examples using ``public``.)

Conf groups must also include keystone auth and session options, or may pass
existing auth and/or session objects to ``get_service_url()``.

By adding this change, we will have a consistent way to connect with other
services from Nova.


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

None

Other deployer impact
---------------------

The old endpoint configuration options, except for ``[glance]api_servers``,
will be deprecated in Pike and removed in Queens.

Developer impact
----------------

None

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

- Add methods in ``keystoneauth1.loading`` to register and list ``Adapter``
  conf options in a manner similar to those existing for session and auth.
- Add a utility method in Nova to get endpoint from service catalog.
- Update conf groups to include the ``Adapter`` conf options.
- Update conf groups (except Glance) to deprecate existing endpoint-related
  options.
- Update Nova code using endpoints to exploit the new utility method if the
  legacy conf options are not specified.
- (Queens) Remove deprecated endpoint-related conf options, and the code
  branches that use them.

Dependencies
============

* Changes need to be coordinated between ``keystoneauth`` and ``nova``.

Testing
=======

* Unit tests need to be added.

Documentation Impact
====================

* Updating admin guide for configuration related changes.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
