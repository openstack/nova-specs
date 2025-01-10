..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Image properties in server show
===============================

https://blueprints.launchpad.net/nova/+spec/image-properties-in-server-show

This spec proposes to show an instance's embedded image properties in the
server show API. This has lots of uses, but is particularly required for `vTPM
live migration <https://review.opendev.org/c/openstack/nova-specs/+/936775>`_
to show users the vTPM secret security level that is set on their instances.

Problem description
===================

Nova copies the properties of the image into the instance system metadata at
instance create and rebuild to keep this information available even if the
image is changed or deleted later in glance. However the nova API does not
return this authoritative information to the user. As image properties
can affect how the instance is scheduled and what features are enabled for it
in the hypervisor this information is very useful for the user.


Use Cases
---------

* I as the owner of the VM would like to know the image properties used by
  nova when scheduling and building my VM even after the image is changed or
  deleted in glance.

* Especially I as the owner of an existing VM want to see the
  ``hw_vtpm_secret_security`` in the embedded image properties so that I can
  observe the default vTPM security mode applied to of my VM before I consent
  to such security change. See `vTPM live migration <https://review.opendev.org/c/openstack/nova-specs/+/936775>`_.

* I as the owner of the VM want to detect if the admin needed to change
  any image properties in my behalf via ``nova-mange image_property set``.

Proposed change
===============

In a new API microversion return the embedded image properties in the
``GET /server/details`` and ``/server/{server_id}`` responses.

The implementation needs to populate this part of the api response from our
cache of the image details in ``instance.system_metadata``.

Alternatives
------------

Implement separate top level fields for each feature depending on an image
properties.

Data model impact
-----------------

No impact as the image properties are already modelled and persisted today.

REST API impact
---------------
In a new microversion the following API responses are extended:

* ``GET /server/details``
* ``GET /server/{server_id}``

A new ``properties`` subkey will be added under the struct at the existing
``image`` key as a dict where both the keys and the values are following the
schema ``^[a-zA-Z0-9-_:. ]{1,255}$``.

The new subkey will be included in the response with the current default
policy of these APIs, which is ``PROJECT_READER_OR_ADMIN``.

Response example::

    {
      "servers": [
        {
          "id": "65fc9d2f-1d02-4bb0-8602-b505252b17f8",
          "name": "vm1",
          "status": "ACTIVE",
    ...
          "image": {
            "id": "197c0527-f0f8-4f94-9ccc-82759bf0dc21",
            "links": [
    ...
            ],
            "properties": {
              "hw_machine_type": "pc-q35-8.2",
              "hw_vtpm_secret_security": "host",
              "hw_tpm_version": "2.0",
              "hw_tpm_model": "tpm-crb"
    ...
            },
          },
          "locked": false,
    ...
        }
      ]
    }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None, the system_metadata is already loaded from the DB when the API response
is generated `since microversion 2.73 <https://github.com/openstack/nova/blob/a459467899d2b406aa8cf530ae481255eaf3c957/nova/api/openstack/compute/servers.py#L317-L318>`_

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  ?

Feature Liaison
---------------

Feature liaison:
  balazs-gibizer


Work Items
----------

* In a new API microversion extend the API response

Dependencies
============

None


Testing
=======

* Unit test
* API sample functional test

Documentation Impact
====================

* API ref

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.1 Epoxy
     - Introduced
