..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Reset the instance keypair while rebuilding
===========================================

Launchpad blueprint:
https://blueprints.launchpad.net/nova/+spec/rebuild-keypair-reset

This spec describes how to implement the new approach for resetting keypair
while rebuilding.

Problem description
===================

Nova now has no way to reset the instance keypair, even during the rebuild
procedure. So, at least, `nova rebuild` will be one approach to reset the
instance key pair.

Use Cases
---------

- As a user, I have lost my key and need to get into my instance but do not
  want to lose my IP address so I need to rebuild with a new key. [1]_

- As a user, I use rebuild to deploy new OS images to my ironic-managed
  machines. I would like to use rebuild in a similar way for keypair
  rotation. [2]_

- As a user, I have created an entire Heat stack and then found out I used the
  wrong key. Rather than recreate the entire stack, I would like to just
  rebuild the instances with the correct key. [3]_

Proposed change
===============

Will add a new parameter to rebuild API input body, which is named
``key_name``. And after rebuild API call, the response body must contain
the updated new instance ``key_name``.

Alternatives
------------

You will need to delete and create a new instance with a different key pair.
And it is worth noting that the new instance will have a new ID which may
cause additional resource tracking records for cloud applications.

Data model impact
-----------------

None

REST API impact
---------------

Will add a new microversion, to nova rebuild API. Then users could reset
the instance key pair by using rebuild API.

.. note:: The lookup of the ``key_name`` will be based on the *current user
          making the request*, which may not be the same user that created
          the instance. This is possible since users within the same project
          can rebuild another users instance, but keys are scoped to a user.
          See the `Security impact`_ section for more details.

* servers schemas:

::

  base_rebuild_vXXX = {
      'type': 'object',
      'properties': {
          'rebuild': {
              'type': 'object',
              'properties': {
                  'name': parameter_types.name,
                  'imageRef': parameter_types.image_id,
                  'adminPass': parameter_types.admin_password,
                  'metadata': parameter_types.metadata,
                  'preserve_ephemeral': parameter_types.boolean,
                  'OS-DCF:diskConfig': parameter_types.disk_config,
                  'accessIPv4': parameter_types.accessIPv4,
                  'accessIPv6': parameter_types.accessIPv6,
                  'personality': parameter_types.personality,
                  'key_name': parameter_types.name,
              },
              'required': ['imageRef'],
              'additionalProperties': False,
          },
      },
      'required': ['rebuild'],
      'additionalProperties': False,
  }

Security impact
---------------

Keys are owned by users (which is the only resource that's true of). Servers
are owned by projects. Because of this a rebuild with a key_name is looking up
the keypair *by the user calling rebuild*. This is probably what people want,
and if things are unexpected, the other user (that originally created the
instance) can just rebuild the instance again. We will make sure to document
this subtlety in the API reference with this microversion change.


Notifications impact
--------------------

Notifications [4]_ for rebuild action will use the new key pair name.

Other end user impact
---------------------

python-novaclient should also add this new ``key_name`` param to the
`nova rebuild` shell command.

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

* LIU Yulong <i@liuyulong.me>

Work Items
----------

* Add ``key_name`` param to rebuild API [5]_ with a new API microversion.
* CLI support.
* Testing.
* Documentation.

Dependencies
============

None

Testing
=======

* Rebuild an instance and see if the key_name and key_data in DB are really
  changed.
* Tempest cases for new microversion. If the rebuilt instance is in ACTIVE
  state, make sure the cloud-init or config drive did the right public key
  setting.


Documentation Impact
====================

Docs needed for new API (rebuild) microversion. These docs will describe new
instance rebuild API request and response.


References
==========

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2017-October/123071.html
.. [2] http://lists.openstack.org/pipermail/openstack-dev/2017-October/123085.html
.. [3] http://lists.openstack.org/pipermail/openstack-dev/2017-October/123090.html
.. [4] `Notifications in Nova <https://docs.openstack.org/nova/latest/reference/notifications.html>`_
.. [5] `Enable reset keypair while rebuilding instance <https://review.openstack.org/#/c/379128/>`_
