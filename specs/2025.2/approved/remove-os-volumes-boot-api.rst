..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Remove ``/os-volumes_boot`` API
===============================

https://blueprints.launchpad.net/nova/+spec/remove-os-volumes-boot-api

Remove the undocumented, unused ``/os-volumes_boot`` API.

Problem description
===================

The ``/os-volumes_boot`` API is an undocumented, likely unknown alias for the
``/servers`` API. It serves no purpose other than to confuse users and clients,
particularly in an era of auto-generated documentation and client tooling. We
should remove it.

Use Cases
---------

* As a developer of client tooling, I do not wish to have to either support or
  special-case ignore an API that is not documented and duplicates existing
  APIs.

Proposed change
===============

The ``/os-volumes_boot`` API and child APIs will be modified so that it returns
``HTTP 410 (Gone)`` for all resources starting from a new API microversion.
While the API will continue to work for older microversions, we will mark
the method with the ``nova.api.openstack.wsgi.removed`` decorator to indicate
that automatic client and documentation generation tooling should ignore the
API.

Alternatives
------------

We could return ``HTTP 410 (Gone)`` for all microversions. This would be even
easier for client tooling, but historically we have only done this out of
necessity (typically because an underlying feature has been removed).

Data model impact
-----------------

None.

REST API impact
---------------

The ``/os-volumes_boot`` API all all child APIs will return HTTP 410 (Gone)
starting in the new API microversion.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None. None of openstackclient, openstacksdk, python-novaclient, or Gophercloud
currently support or use this API.

Performance Impact
------------------

None.

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

* Remove the API

Dependencies
============

None.

Testing
=======

None.

Documentation Impact
====================

We need a release note. The API is not currently documented in the api-ref so
no changes will be needed there.

References
==========

None.
