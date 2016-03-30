..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Allow user to set and retrieve the server Description
=====================================================

The launchpad blueprint is located at:

https://blueprints.launchpad.net/nova/+spec/user-settable-server-description

Allow users to set the description of a server when it is created, rebuilt,
or updated. Allow users to get the server description.

Problem description
===================

Currently, when a server is created, the description is hardcoded to be the
server display name. The description cannot be set on a server rebuild.

Users cannot set the description on the server or retrieve the description.
Currently, they need to use other fields, such as the server name or meta-data,
to provide a description. These are overloading the name and meta-data
fields in a way for which they were not designed.  A better way to provide
a long human-readable description is to use a separate field.  The description
can be easily viewed in a server list display.

Use Cases
----------

* The End User wishes to provide a description when creating a server.
* The End User wishes to provide a description when rebuilding a server.
  If the user chooses to change the name, a new description may be needed
  to match the new name.
* The End User wishes to get the server's description.
* The End User wishes to change the server's description.

Proposed change
===============

* Nova REST API

  * Add an optional description parameter to the Create Server, Rebuild Server,
    and Update Server APIs.

    * No default description on Create Server (set to NULL in the database).
    * If a null description string is specified on the server update or
      rebuild, then the description is set to NULL in the database
      (description is removed)
    * If the description parameter is not specified on the server update
      or rebuild, then the description is not changed.
    * An empty description string is allowed.

  * The Get Server Details API returns the description in the JSON response.
    This can be NULL.
  * The List Details for Servers API returns the description for each server.
    A description can be NULL.

* Nova V2 client

  * Add an optional description parameter to the server create method.
  * Add an optional description parameter to the server rebuild method.
  * Add new methods for server set and clear the description. These will
    implement a new CLI command "nova describe" with the following
    positional parameters:

      * server
      * description (Pass in "" to remove the description)

  * Return the description on server show method. This can be null.
  * If detail is requested, return the description on each server
    returned by the server list method.   A description can be null.

* Openstack V2.1 compute client

  * NOTE:  Changes to the Openstack V2 compute client will be
    implemented under a bug report, and not under this spec.
  * Add an optional description parameter to CreateServer.
  * Add an optional description parameter to RebuildServer.
  * Add an optional description parameter to SetServer and
    UnsetServer.
  * Return the description on ShowServer.  This can be null.
  * If detail is requested, return the description on each server
    returned by the ListServer.   A description can be null.

Note: A description field already exists in the database, so the change is
to add API/CLI support for setting and getting the description.

Other projects possibly impacted:

* Horizon could be changed to set and show the server description.


Alternatives
------------

None

Data model impact
-----------------

None.  The database column for description already exists as 255 characters,
and is nullable.


REST API impact
---------------

Add the following parameter validation:

::

    valid_description_regex_base = '[%s]*'
    valid_description_regex = valid_description_regex_base % (
        re.escape(_get_printable()))

    description = {
        'type': ['string', 'null'], 'minLength': 0, 'maxLength': 255,
        'pattern': valid_description_regex,
    }


Change the following APIs under a new microversion:

`Create Server <http://developer.openstack.org/api-ref-compute-v2.1.html#createServer>`_
........................................................................................

New request parameter:

+---------------------+------+-------------+-----------------------+
|Parameter            |Style |Type         | Description           |
+=====================+======+=============+=======================+
|description(optional)|plain | csapi:string|The server description |
+---------------------+------+-------------+-----------------------+

Add the description to the json request schema definition:

::

    base_create = {
        'type': 'object',
        'properties': {
            'server': {
                'type': 'object',
                'properties': {
                    'name': parameter_types.hostname,
                    'description': parameter_types.description,
                    'imageRef': parameter_types.image_ref,
                    'flavorRef': parameter_types.flavor_ref,
                    'adminPass': parameter_types.admin_password,
                    'metadata': parameter_types.metadata,
                    'networks': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'fixed_ip': parameter_types.ip_address,
                                'port': {
                                    'type': ['string', 'null'],
                                    'format': 'uuid'
                                },
                                'uuid': {'type': 'string'},
                            },
                            'additionalProperties': False,
                        }
                    }
                },
                'required': ['name', 'flavorRef'],
                'additionalProperties': False,
            },
        },
        'required': ['server'],
        'additionalProperties': False,
    }

Error http response codes:

* 400 (BadRequest) if the description is invalid unicode,
  or longer than 255 characters.


`Rebuild Server <http://developer.openstack.org/api-ref-compute-v2.1.html#rebuildServer>`_
..........................................................................................

New request parameter:

+---------------------+------+-------------+-----------------------+
|Parameter            |Style |Type         | Description           |
+=====================+======+=============+=======================+
|description(optional)|plain | csapi:string|The server description |
+---------------------+------+-------------+-----------------------+

Add the description to the json request schema definition:

::

    base_rebuild = {
        'type': 'object',
        'properties': {
            'rebuild': {
                'type': 'object',
                'properties': {
                    'name': parameter_types.name,
                    'description': parameter_types.description,
                    'imageRef': parameter_types.image_ref,
                    'adminPass': parameter_types.admin_password,
                    'metadata': parameter_types.metadata,
                    'preserve_ephemeral': parameter_types.boolean,
                },
                'required': ['imageRef'],
                'additionalProperties': False,
            },
        },
        'required': ['rebuild'],
        'additionalProperties': False,
    }


Error http response codes:

* 400 (BadRequest) if the description is invalid unicode,
  or longer than 255 characters.


`Update Server <http://developer.openstack.org/api-ref-compute-v2.1.html#updateServer>`_
........................................................................................

New request parameter:

+---------------------+------+----------------------+-----------------------+
|Parameter            |Style |Type                  | Description           |
+=====================+======+======================+=======================+
|description(optional)|plain |csapi:ServerForUpdate |The server description |
+---------------------+------+----------------------+-----------------------+

Add the description to the json request schema definition:

::

    base_update = {
        'type': 'object',
        'properties': {
            'server': {
                'type': 'object',
                'properties': {
                    'name': parameter_types.name,
                    'description': parameter_types.description,
                },

Response:

* The update API currently returns the details of the updated server.  As part
  of this, the description will now be returned in the json response.


Error http response codes:

* 400 (BadRequest) if the description is invalid unicode,
  or longer than 255 characters.


`Get Server Details <http://developer.openstack.org/api-ref-compute-v2.1.html#getServer>`_
..........................................................................................
Add the description to the JSON response schema definition.

::

        server = {
            "server": {
                "id": instance["uuid"],
                "name": instance["display_name"],
                "description": instance["display_description"],
                "status": self._get_vm_status(instance),
                "tenant_id": instance.get("project_id") or "",
                "user_id": instance.get("user_id") or "",
                "metadata": self._get_metadata(instance),
                "hostId": self._get_host_id(instance) or "",
                "image": self._get_image(request, instance),
                "flavor": self._get_flavor(request, instance),
                "created": timeutils.isotime(instance["created_at"]),
                "updated": timeutils.isotime(instance["updated_at"]),
                "addresses": self._get_addresses(request, instance),
                "accessIPv4": str(ip_v4) if ip_v4 is not None else '',
                "accessIPv6": str(ip_v6) if ip_v6 is not None else '',
                "links": self._get_links(request,
                                         instance["uuid"],
                                         self._collection_name),
            },


Security impact
---------------

None

Notifications impact
--------------------

The notification changes for this spec will be included as
part of the implementation of the Versioned Notification API spec:
https://review.openstack.org/#/c/224755/

* The new versioned notification on instance update will include
  the description.
* The new versioned notification on instance create will include
  the description.
* The new versioned notification on instance rebuild will include
  the description.


Other end user impact
---------------------

Changes to python-novaclient and python-openstackclient as described above.

Horizon can add the description to the GUI.

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
  chuckcarmack75

Other contributors:
  none

Work Items
----------

1) Implement the nova API changes.
2) Implement the novaclient and openstackclient changes.


Dependencies
============

None

Testing
=======

* Nova functional tests

  * Add a description to the tests that use the API to create a server.

    * Check that the default description is NULL.

  * Add a description to the tests that use the API to rebuild a server.

    * Check that the description can be changed or removed.
    * Check that the description is unchanged if not specified on the API.

  * Add a description to the tests that use the API to update a server.

    * Check that the description can be changed or removed.
    * Check that the description is unchanged if not specified on the API.

  * Check that the description is returned as part of server details for
    an individual server or a server list.

* Python nova-client and openstack-client.  For the client tests and
  the CLI tests:

  * Add a description to the tests that create a server.
  * Add a description to the tests that rebuild a server.
  * Set and remove the description on an existing server.
  * Check that the description is returned as part of server details for
    an individual server or a server list.

* Error cases:

  * The description passed to the API is longer than 255 characters.
  * The description passed to the API is not valid printable unicode.

* Edge cases:

  * The description passed to the API is an empty string.  This is allowed.

Documentation Impact
====================

Documentation updates to:

* API spec: http://developer.openstack.org/api-ref-compute-v2.1.html
  including the API samples.
* Client: novaclient and openstackclient

References
==========

The request for this feature first surfaced in the ML:

http://lists.openstack.org/pipermail/openstack-dev/2015-August/073052.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Mitaka
     - Re-submitted to add support for description on Rebuild.

