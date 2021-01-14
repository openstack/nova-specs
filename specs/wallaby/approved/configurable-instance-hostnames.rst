..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Configurable Instance Hostnames
===============================

https://blueprints.launchpad.net/nova/+spec/configurable-instance-hostnames

Allow users to specify an explicit hostname for their instance when creating
instances.

Problem description
===================

Nova publishes hostnames for instances via the metadata service and config
drives. This hostname is based on a sanitized version of the instance display
name combined with the domain value specified in ``[api] dhcp_domain``. As part
of the discussion around `bug 1581977`__, it was noted that there is currently
no way to explicitly specify a hostname and decouple it from the display name.
We use the instance's hostname when `DNS integration is enabled in neutron`__,
and this can result in a lack of control over hostnames, preventing users doing
reasonable things like naming their instances based on the fully-qualified
domain name that the instance will eventually be available at.

Correct this gap by allowing users to specify an explicit hostname when
creating instances.

__ https://bugs.launchpad.net/nova/+bug/1581977
__ https://docs.openstack.org/neutron/victoria/admin/config-dns-int.html


Use Cases
---------

As a user, I wish to specify an explicit hostname rather than relying on a
(poorly) sanitized version of the display name.


Proposed change
===============

Allow users to pass an additional ``hostname`` field when creating new
server(s) (``POST /servers``) and when updating an existing server
(``PUT /servers/{id}``). This ``hostname`` attribute will have the following
constraints:

- It must be 63 characters or less
- It must consist of alphanumeric characters and dashes (``-``). Periods,
  underscores, and other characters outside this set will be rejected
- It cannot end in a dash

Where multiple instances are requested, hostnames will be suffixed with
``-{idx}``, where ``{idx}`` is a 1-based index. If the combined name and suffix
would exceed the 63 character limit, the name will be rejected.


Alternatives
------------

- Remove support for neutron's DNS integration features and require users
  explicitly create and configure ports with the ``dns_name`` attribute before
  creating the instance. This places extra work on nova and will result in a
  worse user experience.

- Forbid creation of multiple instances when the ``hostname`` attribute is
  provided, similar to how we forbid this when a port is provided. This is
  reasonable but will require a little more effort from users.

- Start rejecting instance names that are not valid hostnames. This is a
  significant breaking change that will impact many users.


Data model impact
-----------------

None. The ``Instance`` object and corresponding database model and table
already have a ``hostname`` field/column.


REST API impact
---------------

A new microversion will be introduced. When this microversion is used,
users will be able to pass an additional ``hostname`` field when creating new
server(s) (``POST /servers``) and when updating an existing server
(``PUT /servers/{id}``). This ``hostname`` attribute will have the following
constraints:

- It must be 63 characters or less
- It must consist of alphanumeric characters and dashes (``-``). Periods,
  underscores, and other characters outside this set will be rejected
- It cannot end in a dash

Where multiple instances are requested, hostnames will be suffixed with
``-{idx}``, where ``{idx}`` is a 1-based index. If the combined name and suffix
would exceed the 63 character limit, the name will be rejected.

When updating the hostname of an existing instance, the ``dns_name`` attribute
of the port(s) in neutron will be updated, as will the ``hostname`` attribute
exposed via the metadata service.

Security impact
---------------

None. Hostnames will be validated by both the nova API and neutron to prevent
invalid hostnames.


Notifications impact
--------------------

None.


Other end user impact
---------------------

The neutron documentation will need to be updated to reflect the changes in
behavior.


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
  stephenfinucane

Other contributors:
  None


Feature Liaison
---------------

Feature liaison:
  stephenfinucane


Work Items
----------

- Make necessary changes to nova
- Update neutron documentation


Dependencies
============

None.


Testing
=======

This can be tested via Tempest tests, though this will likely require the
`designate-tempest-plugin`__ package. The bulk of the lifting will be done
with functional and unit tests.

__ https://github.com/openstack/designate-tempest-plugin


Documentation Impact
====================

Both nova and neutron's documentation will need to be updated to reference this
functionality. The api-ref will be updated to document the new fields allowed
in the API requests.


References
==========

* https://bugs.launchpad.net/nova/+bug/1581977
* https://review.opendev.org/c/openstack/nova/+/764482
* http://lists.openstack.org/pipermail/openstack-discuss/2020-November/019113.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
