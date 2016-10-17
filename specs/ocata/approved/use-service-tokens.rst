..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Use service token for long running tasks
========================================

https://blueprints.launchpad.net/nova/+spec/use-service-tokens

Make use of new Keystone feature where if service token is sent along with the
user token,then it will ignore the expiration of user token. It stop issues
with user tokens expiring during long running operations, such as
live-migration.

Problem description
===================

Some operations in Nova could take a long time to complete. During this
time user token associated with this request could expire. When Nova tries
to communicate with Cinder, Glance or Neutron using the same user token,
Keystone fails to validate the request due to expired token.
Refer to Bug 1571722.

Use Cases
---------

Most failure cases are observed during live migration case, but are not
limited to that:

* User kicks off block live migration. Depending upon the volume size it
  could take long time to move this volume to new instance and user token
  will expire. When Nova calls Cinder to update the information of this
  volume by passing a user token, the request will be failed by Keystone due to
  expired token.
* User kicks off live migration. Sometimes libvirt could take a while to move
  that VM to new host depending upon the size and network bandwidth. User
  token can expire and any subsequent call to Neutron to update port binding
  will be failed by Keystone.
* User start snapshot operation in Nova. User token expires during this
  operation. Nova call Glance to update final bits and that request is failed
  by Keystone due to expired user token.

Note: Periodic tasks and the user of admin tokens will not be discussed in the
this spec. That will be in a follow on spec.

Proposed change
===============

Keystone/auth_token middleware now support that if a expired token is submitted
to it along with an “X-Service-Token” with a service role, it will validate
that token and ignore the expiration on the user token. Nova needs to use
this functionality to avoid failures in long running operations like live
migration.

Keystone details can be found here:
https://specs.openstack.org/openstack/keystone-specs/specs/keystone/ocata/allow-expired.html

* Pass service token to Cinder.
* Pass service token to Neutron, but only for non-admin cases.
* Pass service token to Glance

Note: Defer passing service tokens to other services until required.

OpenStack services only communicate with each other over the public REST APIs.
While making service to service requests, Keystone auth_token middleware
provides a way to add both the user and service token to the requests using a
service token wrapper.

Addition of service token for service to service communication is configurable.
There will be a new configuration group called "service_user" that is
registered using register_auth_conf_options from keystoneauth1.

A configuration option ``send_service_user_token`` which defaults to ``False``
can be used to validate request with service token for interservice
communication.

Service to service communication will now include a service token which is
validated separately by keystoneauth1. At this time, keystone does not support
mutiple token validation. So, this will be another validation request which
will result in additional API calls to keystone.  Rally benchmark tests will
be ran with and without the "service_user" config options set to compare the
results for long running tasks like snapshot or live migration.

Alternatives
------------

* One alternative is to set longer expiration on user tokens so they don't
  expire for long running operations. But most of the times, short-lived
  tokens are preferred as keystone provides bearer tokens which are security
  wise very weak. Short expiration period limits the time an attacker can
  misuse a stolen token.

* Or we can have same implementation as proposed above with a separate service
  token for each service. This will not expose access to all service if one of
  the token gets compromised.

* In future, service token request validation can be made cacheable within
  neutron, cinder or glance clients to reduce extra API calls to keystone.

Data model impact
-----------------

None

REST API impact
---------------

None.

Security impact
---------------

Service token will be passed along with user token when communicating with
Cinder and Neutron in case of live migration.

Notifications impact
--------------------

None

Other end user impact
---------------------

None.

Performance Impact
------------------

* There will be extra API calls to keystone to generate the service token for
  every request we send to external services.
* The external services keystone auth middlewere also now needs to validate
  both user and service tokens, creating yet more keystone load.

Other deployer impact
---------------------

* Keystone middleware upgrading required on the services we sent the tokens
  to if we want to make use of service token validation.
* The deployer needs to know about the new configuration values added. It
  should be documented in the upgrade section.

Developer impact
----------------

Cross service communication using service tokens should be understood by all
services. Need to document use of service tokens in developer docs so others
know whats going on.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sarafraj Singh (raj_singh)

Other contributors:
  Pushkar Umaranikar (pumaranikar)
  OSIC team

Work Items
----------

* Pass service token to Cinder.
* Pass service token to Neutron, but only for non-admin cases.
* Pass service token to Glance
* Depends on the DevStack change to create service users and config updates
* Update CI jobs which depends on devstack change.

Dependencies
============

* https://specs.openstack.org/openstack/keystone-specs/specs/keystone/ocata/allow-expired.html
  This has been mostly implemented.
  Need to use updated keystone middlewere to start fixing the expired tokens.

Testing
=======

* Existing functional tests will cover this new flow.
* Test service to service communication with and without service token
  validation.

Documentation Impact
====================

* Updating developer doc
* updating admin guide to configure and use service user group.

References
==========

Keystone spec:

* https://specs.openstack.org/openstack/keystone-specs/specs/keystone/ocata/allow-expired.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
