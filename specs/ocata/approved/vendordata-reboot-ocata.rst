..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
vendordata reboot, remaining work in Ocata
==========================================

https://blueprints.launchpad.net/nova/+spec/vendordata-reboot-ocata

In Newton, the Nova team implemented a new way for deployers to provide
vendordata to instances via configdrive and metadata server. There
were a few smaller items that didn't land in Newton, which we need
to finalize.

You can read the spec from Newton for more detail about vendordata.
It is at:

http://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/vendordata-reboot.html

Problem description
===================

Please see the Newton specification for a complete description of the
work that was proposed for Newton. In general terms, the following was
implemented:

* the initial implementation of vendordata v2
* functional testing
* support for SSL certificate verification

Use Cases
---------

The items below will be implemented in Ocata, in the order listed in this
document.

Proposed change
===============

Keystone token changes
----------------------

There are some concerns about how the keystone verification between
the Nova metadata service and the vendordata HTTP servers was
implemented. As implemented in Newton, the requesting user's keystone
token is passed through to the external vendordata server if available,
otherwise no token is passed.

Why would the token sometimes not be available? Many metadata operations are
initiated by the instance without a user being associated with them -- for
example cloud-init calling the metadata server on first boot to determine
configuration information. In these cases no keystone token is provided to
the metadata service.

This implementation is flawed because of how the keystone middleware
works. If no token is passed and the keystone middleware is enabled, then
the request will be rejected before the external vendordata server has
a chance to process the request at all.

Additionally, we're authenticating the wrong thing. What we should be ensuring
is that its the Nova metadata service which is calling the external vendordata
server. To do this we should use a Nova service account.

To resolve these issues we will move to passing a Nova service token to the
external vendordata server. This will be a new service token created
specifically for this purpose. This change is considered a bug fix and will
be backported to Newton to ensure a consistent interface for implementators
of external vendordata servers.

Role information from the user's token
--------------------------------------

The only place where we need to use the user's token is for role information.
So that this is available later (and doesn't change if the user's roles
change), we will store this information from the boot request in the Nova
database as system metadata, and then pass that through to the external
vendordata service with each request.

During the summit session it was considered important that we store this role
information so that the results returned for metadata requests do not change
over time -- for example if a user has a role that allows them to start a mail
server at the time of the boot request, the instance should remain a mail
server for all time, regardless of if that user has that role removed from
them.

This is not a bug fix and will not be backported.

Hard failure mode
-----------------

Operators at the summit also requested that they'd like a mode where if an
external vendordata server fails to return a valid response to a request the
instance should be placed into an error state. This is for use cases where
the instance requires configuration information from an external service to be
able to operate correctly.

This is not a bug fix and will not be backported.

Caching
-------

The original specification envisaged caching of responses from the external
vendordata service, but this was not implemented. If time allows in the Ocata
release, we will add this support.

This is not a bug fix and will not be backported.

Alternatives
------------

This work is as discussed at the summit as a follow on. The alternative would
be to leave the new vendordata implementation incomplete.

Data model impact
-----------------

None, apart from extra data being stored in the system metadata table.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers will need to configure an additional service token in order to use
authenticated calls to external metadata services.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mikalstill

Work Items
----------

See proposed changes above.

Dependencies
============

None.


Testing
=======

Unit test


Documentation Impact
====================

These changes are of most interest to deployers, so we should make sure they
are documented in the admin guide.

References
==========

http://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/vendordata-reboot.html

History
=======

The first implementation of this work was in Newton.
