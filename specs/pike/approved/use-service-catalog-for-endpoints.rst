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
when Nova interacts with Cinder, Glance and Neutron.

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
endpoint URL. Each service has url param in ``nova.conf`` which represents
service endpoint. For example, in ``nova.conf``, there are many endpoints
like::

   [glance]
   api_servers = http://127.0.0.1:9292
   [neutron]
   url = http://127.0.0.1:9696

Keystoneauth provides a simple and consistent way to get API endpoints from
the Keystone service catalog instead of configuring it in a conf file.

For example, the ``catalog_info = volume:cinder:publicURL`` in nova.conf
is a configuration setting to set the info to match when looking for cinder
in the service catalog. Format used here is::

   <service_type>:<service_name>:<endpoint_type>

To make retrieving API endpoint consistent, we can add a new method
``get_service_url()`` in Nova. To establish communication with any other
service, Nova will call this method to find API endpoints.

The method will first look at the existing configuration options such as
``[glance]api_servers`` and use these options if they exist in the
configuration file. This is to ensure backwards compatibility and a smooth
upgrade experience. If the existing configuration option is *not* found or has
no value, then the method will look up a specified API endpoint from the
Keystone service catalog for a particular service type using ``keystoneauth``.
However, the old style options will be deprecated in Pike and setting them will
result in a warning being logged. The old deprecated endpoint options will be
removed in the Queens release.

By adding this change, we will have consistent way to connect with other
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

The old cinder/neutron/glance endpoint configuration options will be deprecated
in Pike and removed in Queens.

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

* Add a utility method in Nova to get endpoint from service catalog.

Dependencies
============

None

Testing
=======

* Functional tests need to be added.

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
