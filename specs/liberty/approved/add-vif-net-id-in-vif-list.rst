..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Add VIF net-id in virtual interfaces list API Response
======================================================

https://blueprints.launchpad.net/nova/+spec/add-vif-net-id-in-vif-list

There is difference in virtual interfaces API response between v2 and v2.1.
VIF net_id is not included in v2.1 response.
This spec proposes to add VIF net_id as microversion in v2.1 API.

Problem description
===================

V2 API has extension for virtual interface 'OS-EXT-VIF-NET' which adds
OS-EXT-VIF-NET:net_id" in virtual interfaces list response.
But during porting the v2 extensions to v2.1, this extension was missed.
Because of this there is difference between v2 and v2.1 response of virtual
interface API.

v2 List virtual interface Response (with all extension enable):

::

  {
    "virtual_interfaces": [
      {
          "id": "%(id)s",
          "mac_address": "%(mac_addr)s",
          "OS-EXT-VIF-NET:net_id": "%(id)s"
      }
    ]
  }

v2.1 List virtual interface Response:

::

  {
    "virtual_interfaces": [
      {
          "id": "%(id)s",
          "mac_address": "%(mac_addr)s"
      }
    ]
  }

Attribute  "OS-EXT-VIF-NET:net_id" is missing in v2.1.
Users who need VIFs' net-id, would not be able to get it from v2.1.

This is bug [1]_ in v2.1 base API but cannot be fixed as bug because v2.1 is
released in kilo and as per API contract its too late to fix this as bug
in v2.1 base API.

Another problem is that v2.1 extension-list also returns 'OS-EXT-VIF-NET'
extension, which gives false message to users that this extension is also
loaded in v2.1 which is actually not true due to problem described above.
Removal of this extension from v2.1 extension list should be done in v2.1
base API and back-ported to stable kilo branch as proposed in [2]_.

Use Cases
----------

User who need VIFs' net-id information and getting the same from v2
APIs, should be able to get from v2.1 API also.

By adding this information, users can determine in which network a vif
is plugged into.

Project Priority
-----------------

None.

Proposed change
===============

This spec propose to fix this bug as microverion by adding
VIF net-id information in virtual interfaces list Response.

v2.1 List virtual interface Response:

Current:

::

  {
    "virtual_interfaces": [
      {
          "id": "%(id)s",
          "mac_address": "%(mac_addr)s"
      }
    ]
  }

After:

::

  {
    "virtual_interfaces": [
      {
          "id": "%(id)s",
          "mac_address": "%(mac_addr)s",
          "net_id": "%(id)s"
      }
    ]
  }

Attribute "net_id" will be added in Response.

NOTE- Attribute name "OS-EXT-VIF-NET:net_id" (in v2) has been changed
to "net_id".
Because this attribute is being added as microversion and as per guidlines
[3]_, we should not add namespace to new attribute name unlike v2 where it
was added as extension.

Alternatives
------------

As alternate we can fix this as bug in v2.1 base without microversion
so that v2.1 will be exactly same as v2. But that breaks API contract
as v2.1 is already released.

Data model impact
-----------------

None.

REST API impact
---------------

New attribute VIF net-id will be added as microversion.

* Specification for the method

  * Description

    * API Virtual Interface List

  * Method type

    * GET

  * Normal http response code

    * 200, no change in response code

  * Expected error http response code(s)

    * No change in error codes

  * URL for the resource

    * 'servers/<server_uuid>/os-virtual-interfaces'

  * JSON schema definition for the body data if allowed

    * A request body is not allowed.

  * JSON schema definition for the response data if any

::

  {
    'status_code': [200],
    'response_body': {
        'type': 'object',
        'properties': {
            'virtual_interfaces': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'mac_address': {'type': 'string'},
                        'net_id': {'type': 'string'}
                    }
                    'required': ['id', 'mac_address', 'net_id']
                }
            }
        }
        'required': ['virtual_interfaces']
    }
  }

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

python-novaclient needs to be updated in order to show VIF 'net_id'
in corresponding command for v2.1 + microversion.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmann

Other contributors:
  None

Work Items
----------

* Add 'net_id' in virtual interfaces list response.
* Modify Sample and unit tests accordingly.

Dependencies
============

None.

Testing
=======

Currently Nova functional test will cover these changes testing.
After discussion of micro version testing in Tempest, these changes
can be tested accordingly.

Documentation Impact
====================

Virtual Interface GET APIs doc will be updated accordingly.

References
==========

.. [1] https://bugs.launchpad.net/nova/+bug/1470690
.. [2] https://review.openstack.org/#/c/198934/ https://review.openstack.org/#/c/198944/
.. [3] https://github.com/openstack/nova/blob/master/doc/source/api_plugins.rst

* https://review.openstack.org/#/c/197822/
