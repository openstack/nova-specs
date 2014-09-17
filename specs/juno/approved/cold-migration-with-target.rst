
..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Enable cold migration with target host
===========================================

https://blueprints.launchpad.net/nova/+spec/cold-migration-with-target

The aim of this feature is to let operators cold migrate instances with
target host manually.


Problem description
===================

I have a customized HA plugin which automatically performs migrations under
certain conditions, and the HA plugin is able to intelligently pick up
destinations, but only live migrations support specifying destinations.

At the moment cold migration do not support migrate a VM instance with target
host, this blueprint want to add this feature to nova so that above scenario
can be satisified.

It also make cold migration consistent with live-migrate operations as live
migration support migration with and w/o target host.


Proposed change
===============

Modify the current resize_instance flow to let the api can specify the target
host for cold migration.


Alternatives
------------
None

Data model impact
-----------------
None

REST API impact
---------------

* For V2 API, a new extension will be added as:
  alias: os-extended-admin-actions
  name: ExtendedAdminActions
  namespace:
  http://docs.openstack.org/compute/ext/extended_admin_actions/api/v1.1

  When the new extension "os-extended-admin-actions" is loaded, the api of
  _migrate() wil support cold migration with target host.

* For a later microversion of v2.1 API, no new extension needed, the
  existing cold migration API will be updated to support this.

* URL: existed admin actions extension as:
       * /v2/{tenant_id}/servers/actions:
       * /v2.1/servers/actions:

  JSON request body::

    {
        "migrate":
        {
            "host": "fake_host"
        }
    }

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------

python-novaclient will be modified to have target_host argument as
optional.

The user can trigger this feature by:
nova migrate my_server target_host

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jay-lau-513

Work Items
----------

* Add logic to select target host for cold migration
* Add API v2/v2.1
* Set target host optional on nova-client

Dependencies
============

None


Testing
=======

Add unit test in nova to cover the case of cold migration with target host,
also we probably need to think about adding functionnal tests in tempest.


Documentation Impact
====================

* Api Docs to reflect that target host field is optional.
* Client docs ( due to optional arg)
* Admin User Guide on cold migration topic.


References
==========
None
