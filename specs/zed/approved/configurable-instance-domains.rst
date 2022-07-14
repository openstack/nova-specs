..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Configurable instance domains
=============================

https://blueprints.launchpad.net/nova/+spec/configurable-instance-domains

Currently, there is no way for a user booting an instance to tell the
instance's guest operating system what is the domain name of the instance.
Using Fully Qualified Domain Names (FQDN) as the instance hostname was
unintentionally allowed for a period of time, but with the merging of [1] that
ability went away. This spec proposes a new API attribute to enable users to
set the domain name of their instances.

Problem description
===================

There are currently two ways for operators (not users!) to set domain names for
instances. On the Nova side, the ``[api]dhcp_domain`` config option is used by
the metadata API when constructing the hostname to expose in the metadata. This
config option applies to the entire cloud. On the Neutron side, the
``[DEFAULT]dns_domain`` config option is similarly applicable to the entire
deployment.  While it is possible to set the ``dns_domain`` field on a Neutron
network, this information is not currently communicated to the guests in any
way.

Neutron is working on a feature to expose a network's ``dns_domain`` field via
the DHCP agent to the guest operating system [2].  However, if cloud-init is
running in the guest, cloud-init may override the domain name provided by
DHCP. Cloud-init uses the Nova metadata API - specifically the ``hostname``
field - as an information source.

The Domain Names in Metadata spec [3] was originally proposed as a lightweight
way of addressing this gap. It proposed exposing an instance's port(s)'s
``dns_domain`` value(s) in the metadata. However, the only way of intelligently
handling instances with multiple ports with different ``dns_domain`` values is
to expose every port's ``dns_domain`` in its own subsection in the metadata.
This is useless to cloud-init, which needs a unique ``hostname`` field.

This spec is building on the Configurable Instance Hostnames spec [1], and
allows an instance's domain name to be configurable by the user.

Use Cases
---------

As a user, I want to pass my instance's domain name to the guest operating
system.

Proposed change
===============

A new ``Instance.domain`` object field is introduced, with its corresponding
database migration. The value for this field is obtained from a new ``domain``
API attribute. This attribute is added in a new microversion to the create
server(s) (``POST /servers``) and update server (``PUT /servers/{id}``) APIs.
It is also exposed in the list detailed server (``GET /servers/detail``) and
show server details (``GET /servers/{id}``) APIs.

The metadata API will use this new ``Instance.domain`` where it currently
uses the ``[api]dhcp_domain`` config option. If no ``Instance.domain`` is set,
the metadata API will continue to fallback on ``[api]dhcp_domain`` like it
currently does.

For ports auto-created by Nova, the port's ``dns_domain`` value will be kept in
sync with the ``Instance.domain`` value. For other ports attached to instances,
the port's ``dns_domain`` value will not be touched, and ``Instance.domain``
will take prededence over the port's ``dns_domain``. Nova will never touch a
network's ``dns_domain`` value.

Alternatives
------------

The Domain Names in Metadata spec [2] was originally viewed as a more
lightweight mechanism to achieve this spec's purpose, but it proved impossible
to intelligently handle instances with multiple ports. The only source of truth
for an instance's domain is the user.

Data model impact
-----------------

The new ``domain`` field is added to the ``Instance`` object and its database
table.

REST API impact
---------------

A new microversion is introduced, which allows users to optionally pass an
additional ``domain`` field when creating new server(s) (``POST /servers``) and
when updating an existing server (``PUT /servers/{id}``). This ``domain``
attribute has the following constraints:

* It cannot exceed 189 characters in length. This is calculated from the
  maximum domain name length of 253 characters as stated in RFC 1035, minus
  what Nova currently allows for the ``hostname`` field (63 characters), minus
  1 character for the period (``.``) to join them.
* It must consist of alphanumeric characters, dashes (``-``) and at least one
  or more periods (``.``).  Characters outside this set will be rejected.
* The top-level domain, what comes after the last period, must be letters of
  the latin alphabet.

A request for booting multiple instances with the same ``domain`` results in
all the instances receiving that ``domain`` (unlike the display name and
hostname, which use an autoincrementing suffix).

A new ``domain`` attribute is displayed when listing detailed server (``GET
/servers/detail``) and showing server details (``GET /servers/{id}``). This
attribute is optional, and is only displayed if the server has a ``domain``
(either from creation, or set afterwards with an update).

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Openstackclient and openstacksdk are updated to support the new microversion.

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

The new ``Instance.domain`` field and associated database column is optional,
so existing instances are not affected. If no ``Instance.domain`` is set, Nova
will continue to default to ``[api] dhcp_domain`` like it currently does when
generating the metadata.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Feature Liaison
---------------

None.

Work Items
----------

* Add ``domain`` column in the ``instances`` table in the main database.
* Add ``domain`` field to the ``Instance`` object.
* Add the user-facing API changes.

Dependencies
============

None.

Testing
=======

This can be tested with Nova functional tests.

Documentation Impact
====================

Nova's api-ref is updated.

References
==========

[1] https://review.opendev.org/c/openstack/nova/+/764482
[2] https://review.opendev.org/c/openstack/neutron-specs/+/832658
[3] https://review.opendev.org/c/openstack/nova-specs/+/840974
[4] https://specs.openstack.org/openstack/nova-specs/specs/xena/implemented/configurable-instance-hostnames.html
[5] https://review.opendev.org/c/openstack/nova-specs/+/840974

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Zed
     - Introduced
