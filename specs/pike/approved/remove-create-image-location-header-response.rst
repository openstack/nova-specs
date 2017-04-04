..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Remove Location header from createImage and createBackup responses
==================================================================

`<https://blueprints.launchpad.net/nova/+spec/remove-create-image-location-header-response>`_

The `createImage` and `createBackup` APIs return a `Location` header in the
response which is a URL pointing at what is most likely an internal Glance API
server, and is therefore not accessible to the end user. The URL is also not
versioned for the Image service, so unless the cloud provides an alias, the URL
is wrong anyway. This spec proposes to replace the Location header with a
simple response body json dict that contains the image_id for the snapshot
image.

Problem description
===================

The `createImage` and `createBackup` APIs return a `Location` header in the
response which is built from the ``CONF.glance.api_servers`` configuration
within Nova that is most likely using internal addresses for Glance, making it
unusable for the end user.

Client code like Tempest [1]_ and python-novaclient [2]_ have always ignored
the Location header in the response and just parsed the URL to get the image ID
and use it for their own ``GET /v2/images/{image_id}`` request.

Also, the URL in the Location header response is unversioned, but reading the
image service API reference docs for the versions document and the examples,
there is always a versioned prefix on the URL, e.g. ``GET /v1/images`` or
``GET /v2/images``. The fact the URL returned from nova is unversioned likely
means this is a legacy artifact before Glance was split out from Nova.

Use Cases
---------

As a user, I want to be able to use an accurate response from the `createImage`
and `createBackup` APIs to poll the status on the created snapshot image in the
Image service.

Proposed change
===============

This blueprint proposes to remove the Location header in the response and just
return the image_id in a response body dict with a new microversion for the
`createImage` and `createBackup` APIs.

Alternatives
------------

We could change the code that generates the Location header URL to use the
`public` interface for the `image` service type in the service catalog. This
would require more work since we would have to likely make the interface to
use configurable. Also, given how many client libraries are already ignoring
the Location header and not using it directly, but instead just parsing the
image ID from the URL, we can create a cleaner break from the broken behavior
of the past by returning a simple json response body with the value consumers
actually care about.

Data model impact
-----------------

None

REST API impact
---------------

In a microversion, the response for the `createImage` and `createBackup` server
action APIs will replace the `Location` header with a json dict response body
that contains a single `image_id` key mapped to the snapshot image ID (uuid)
created.

So rather than return a response with a header like::

  Location: http://172.21.1.10:9292/images/f5d5b63b-e710-4d59-aa12-a9bd42f6652a

We will return a response with a body like::

  {
    'image_id': 'f5d5b63b-e710-4d59-aa12-a9bd42f6652a'
  }

Security impact
---------------

None. This is arguably more secure since we would no longer be leaking internal
Glance API server IPs out of the public compute REST API.

Notifications impact
--------------------

None. There are actually ``compute.instance.snapshot.start`` and
``compute.instance.snapshot.end`` notifications but they do not actually
contain the snapshot image ID, for whatever reason, so there is no impact to
those existing notifications.

Other end user impact
---------------------

python-novaclient will need to be updated to handle the change in response
format in the microversion for the ``nova image-create`` CLI.

The ``nova backup`` CLI in python-novaclient does not currently parse the
Location header from the server response to print the snapshot image ID, so
there are no changes to python-novaclient for the `createBackup` change.

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
  Matt Riedemann (mriedem)

Work Items
----------

* Add the microversion response change to the `createImage` and `createBackup`
  server action APIs.
* Update documentation, including making a note in the API reference docs that
  the Location header in the response before the microversion is likely broken.


Dependencies
============

None


Testing
=======

* Unit and functional (API samples) tests as normal.
* Since the `createImage` and `createBackup` APIs currently do not return a
  response body there is not actually an existing response schema validation
  check in Tempest, so one would have to be added.


Documentation Impact
====================

The `createImage` and `createBackup` API reference documentation will be
updated.

References
==========

This originally came up as a bug: https://bugs.launchpad.net/nova/+bug/1679285

.. [1] https://github.com/openstack/tempest/blob/15.0.0/tempest/api/compute/images/test_images_oneserver.py#L94
.. [2] https://github.com/openstack/python-novaclient/blob/7.1.0/novaclient/v2/servers.py#L1613

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
