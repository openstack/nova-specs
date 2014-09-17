..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Allow image to be specified during rescue
==========================================

https://blueprints.launchpad.net/nova/+spec/allow-image-to-be-specified-during-rescue

In this blueprint we aim to add an additional optional parameter to the
instance rescue API. This parameter will be used to specify the image to be
used while rescuing the instance. If the parameter is not specified, the
instance will be rescued using the base image.


Problem description
===================

The custom image used during rescue might be corrupt, leading to errors,
or too large, leading to timeouts.
Also, if the base image is deleted, the image ref on the
instance_system_metadata will be invalid, leading to the rescue operation
failing.
This feature can also be used in the case where the customer wants to rescue
the instance with a specific image, rather the default one. This would provide
more flexibility to the feature.


Proposed change
===============

In order to implement this I propose that we allow the user to specify which
image is to be used for rescue. (could be a default base image or a custom
image)

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

API for specifying image to be used to rescue an instance:

Scenarios:
Case 1: If image_ref is specified as part of the rescue request, that image
will be used.
Case 2: If image_ref is not specified as part of the rescue request,
image_base_image_ref on the system_metadata of the instance will be used.
(Default behavior)

V2 API specification:
POST: v2/{tenant_id}/servers/{server_id}/action

V3 API specification:
POST: v3/servers/{server_id}/action

Request parameters:
* tenant_id: The ID for the tenant or account in a multi-tenancy cloud.
* server_id: The UUID for the server of interest to you.
* rescue: Specify the rescue action in the request body.
* adminPass(Optional): Use this password for the rescued instance.
Generate a new password if none is provided.
* rescue_image_ref(Optional): Use this image_ref for rescue.

JSON request:
{"rescue": {"adminPass": "MySecretPass",
"rescue_image_ref": "848b39fb-6904-46d6-af3c-baa3eefedffc"}}

JSON response:
{"adminPass": "MySecretPass"}

Sample v2 request:
POST: /v2/d1b123/servers/7d14f8123/action -d '{"rescue":
{"rescue_image_ref": "848b39fb-6904-46d6-af3c-baa3eefedffc"}}'

Sample v3 request:
POST: /v3/servers/7d14f8123/action -d '{"rescue":
{"rescue_image_ref": "848b39fb-6904-46d6-af3c-baa3eefedffc"}}'

This would use image with ref "848b39fb-6904-46d6-af3c-baa3eefedffc" to
rescue instance with uuid "7d14f8123"

JSON schema definition::

    rescue = {
        'type': 'object',
        'properties': {
            'rescue': {
                'type': ['object', 'null'],
                'properties': {
                    'admin_password': parameter_types.admin_password,
                    'rescue_image_ref': parameter_types.image_ref,
                },
                'additionalProperties': False,
            },
        },
        'required': ['rescue'],
        'additionalProperties': False,
    }

HTTP response codes:
v2:
Normal HTTP Response Code: 200 on success
v3:
Normal HTTP Response Code: 202 on success
(Will check whether these can be made consistent in v2 and v3 during
implementation.)

Validation:
'rescue_image_ref' must be of a uuid-str format.
Failure Response Code: HTTPBadRequest with "Invalid image ref format" message.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The rescue call in python-novaclient will have to include the additional
optional parameter

Optional argument:
--rescue_image_ref <image_ref> ID of image to be used for rescue

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

The parameter will be optional, so no other code needs to be changed.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
    aditirav

Work Items
----------

* Changes to be made to the compute manager rescue method to use the
  image ref passed in, during the rescue of the instance.
* Add an extension to the V2 API to make rescue take in the optional parameter
  'rescue_image_ref
* Changes to the V3 API to take in the optional parameter 'rescue_image_ref'
* Include tests in tempest to check the behavior of rescue instance with
  the image ref passed in through the API call.


Dependencies
============

None


Testing
=======

Tempest tests to be added to check if rescue of the instance uses the image
specified in the API call.


Documentation Impact
====================

Changes to be made to the rescue API documentation to include the additional
parameter 'rescue_image_ref' that can be passed in.


References
==========

None

