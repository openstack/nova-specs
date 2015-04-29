..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Show 'reserved' status in os-fixed-ips API
==========================================

https://blueprints.launchpad.net/nova/+spec/show-reserved-status-in-os-fixed-ips-api

Show the 'reserved' status on a FixedIP object in the os-fixed-ips API
extension. The extension allows one to reserve and unreserve a fixed IP but the
show method does not report the current status.


Problem description
===================

The os-fixed-ips API extension currently allows one to set the 'reserved'
field on a FixedIP object in the database but the show method does not return
the current value so if you want to write an application to reserve/unreserve
fixed IPs today, you have to keep track of this information externally or get
it from the database yourself.

Use Cases
---------

As a cloud administrator, I want to reserve/unreserve fixed IPs but I need to
know the current reserved status on a given fixed IP before I can act on it.

Project Priority
----------------

None

Proposed change
===============

Add a new API microversion to the os-fixed-ips API extension such that if the
version on the API GET request satisfies the minimum version required, include
the 'reserved' status in the fixed_ip response data.

Alternatives
------------

We could add this information to the 'nova-manage fixed list' output but the
nova-manage CLI is mostly deprecated for things that should be done through the
Nova API service.

Data model impact
-----------------

None

REST API impact
---------------

The proposed change just updates the GET response data in the os-fixed-ips
API extension to include the 'reserved' boolean field if the request has a
minimum supported version.

* Specification for the method

  * Shows information for a specified fixed IP address.

  * Method type: GET

  * Normal http response code(s): 200

  * Expected error http response code(s):

    * 400: If the address on the request is invalid.
    * 404: If the address on the request does not match a FixedIP entry in the
      database.

  * ``/v2.1/​{tenant_id}​/os-fixed-ips/​{fixed_ip}​``

  * Parameters which can be passed via the url: The fixed IP address

  * JSON schema definition for the response data:

::

   get_fixed_ip = {
       'status_code': [200],
       'response_body': {
           'type': 'object',
           'properties': {
               'fixed_ip': {
                   'type': 'object',
                   'properties': {
                       'address': {
                           'type': 'string',
                           'format': 'ip-address'
                       },
                       'cidr': {'type': 'string'},
                       'host': {'type': 'string'},
                       'hostname': {'type': 'string'},
                       'reserved': {'type': 'boolean'}
                   },
                   'required': ['address', 'cidr', 'host',
                                'hostname', 'reserved']
               }
           },
           'required': ['fixed_ip']
       }
   }

* Example use case:

Request:

GET --header "X-OpenStack-Nova-API-Version: 2.4" \
http://127.0.0.1:8774/v2.1/e0c1f4c0b9444fa086fa13881798144f/os-fixed-ips/\
192.168.1.1

Response:

::

   {
       "fixed_ip": {
           "address": "192.168.1.1",
           "cidr": "192.168.1.0/24",
           "host": "host",
           "hostname": "openstack",
           "reserved": false
       }
   }

* There should not be any impacts to policy.json files for this change.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

* The v2.1 python-novaclient fixed-ip-get command could be updated to show the
  'reserved' status in it's output if 'fixed_ip' dict response has the
  'reserved' key in it.

Performance Impact
------------------

None

Other deployer impact
---------------------

None; if a deployer is using the required minimum version of the API to get
the 'reserved' data they can begin using it, otherwise they won't see a change.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem@us.ibm.com>

Work Items
----------

* Add a new microversion and change nova/api/openstack/plugins/v3/fixed_ips.py
  to use it to determine if the 'reserved' attribute on the FixedIP object
  should be returned.


Dependencies
============

None


Testing
=======

* Unit tests and possibly API samples functional tests in the nova tree.
* There are currently not any compute API microversions tested in Tempest
  beyond v2.1. We could add support for testing the new version in Tempest
  but so far the API is already at least at v2.3 without changes to Tempest.


Documentation Impact
====================

The nova/api/openstack/rest_api_version_history.rst document will be updated.


References
==========

* Originally reported as a bug: https://bugs.launchpad.net/nova/+bug/1249526

* Old ML thread for the bug:

http://lists.openstack.org/pipermail/openstack-dev/2013-November/019506.html

* Proof of concept code change: https://review.openstack.org/#/c/168966/
