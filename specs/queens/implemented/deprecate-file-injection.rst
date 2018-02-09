..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Deprecate file injection
========================

`<https://blueprints.launchpad.net/nova/+spec/deprecate-file-injection>`_

Deprecate "personality files", otherwise known as file injection,
from the compute REST API. This is something we have talked about
for several years since file injection is insecure, not very user
friendly, and we have alternatives.

Problem description
===================

There are a few issues with nova's file injection support.

#. It is not discoverable by the end user

   As noted in [1]_, depending on how the compute host is configured, the
   user request to inject personality files may be silently ignored. For the
   libvirt driver, file injection is disabled by default via the
   ``[libvirt]/inject_partition`` configuration option, so the default
   behavior is to not honor the user request, at least when using libvirt
   which is by far the most widely deployed compute driver in nova. Note
   that the ``[libvirt]/inject_partition`` configuration option default value
   has been to disable file injection `since the Icehouse release`_.

.. _since the Icehouse release: https://review.openstack.org/#/c/70239/

#. It is not secure

   When injecting files, if **libguestfs** is not available on the compute
   host, then the **VFSLocalFS** code is used to inject files via the host.
   This means malicious images could exploit the host. This was also discussed
   in the mailing list [2]_. This was originally a hack to workaround an
   issue in older versions of Ubuntu and is going to be removed regardless
   of the changes proposed in this spec. [3]_

#. It is not persisted

   Personality files are not persisted in the database which means they cannot
   be retrieved via the metadata service API nor are they available during
   operations like evacuate where the server instance is rebuilt on a different
   compute host because the source host failed.

#. There are better alternatives available

   The configuration drive is the standard way for users to inject user data
   into their server instance. The supplied ``user_data`` is persisted with
   the instance so it is available from the metadata service API and is
   available when rebuilding the configuration drive on another host. There are
   three ways to tell nova to create a configuration drive for an instance:

   - The image can have metadata indicating a configuration drive is required.
   - The operator can configure the ``force_config_drive`` option in nova.conf.
   - The end user can request a configuration drive via the ``config_drive``
     parameter in the ``POST /servers`` API.

   Note that failure to build a config drive during instance create will result
   in the build request getting rescheduled to another compute host. The same
   cannot be said for file injection being disabled on the host.

Use Cases
---------

As a user, I want a predictable way to inject data into my server instance.

As a nova developer, I do not want to maintain legacy code flows for which
there are better alternatives.

Proposed change
===============

There are a few changes to the REST API in a new microversion:

#. Deprecate the ``personality`` parameter from the ``POST /servers`` create
   server API and the ``POST /servers/{server_id}/action`` rebuild server API.

   Specifying the ``personality`` parameter in the request body to either API
   will result in a `400 Bad Request` error response.

#. We will add support to pass ``user_data`` to the rebuild server API as a
   result of this change. Several people said this would be useful for their
   users in a related mailing list thread. [4]_

#. Stop returning ``maxPersonality`` and ``maxPersonalitySize`` values from
   the ``GET /limits`` API. Since we want to stop accepting ``personality``
   files when creating or rebuilding a server instance, we should also stop
   reporting the quota limits on those resources in the new microversion.

#. Stop accepting and returning ``injected_files``,
   ``injected_file_path_bytes``, ``injected_file_content_bytes`` from the
   ``os-quota-sets`` and ``os-quota-class-sets`` APIs.

.. note:: There are configurable quota limits on ``injected_files``,
   ``injected_file_content_bytes`` and ``injected_file_path_length``. There is
   no quota on the ``user_data`` that is supplied with an instance. The only
   limitation on user data is the size of the field in the database, which is
   ~16MiB with MySQL. With the default file injection quota values, the limit
   is less than 1MiB per request, so we have ample space in the database for
   storing in ``user_data`` what otherwise would have been specified with
   personality files.

Since personality file injection will still be supported with older
microversions, there will be nothing removed from the backend compute code
related to file injection (except for the insecure VFSLocalFS code as noted
already). Nor will there be any deprecation of related configuration options
for file injection. The point of this microversion is really to signal that
users should not be using this legacy part of the compute API, and to set a
timer on when it could be removed if nova ever starts requiring a higher
minimum supported microversion in the distant future.

Alternatives
------------

Persist the supplied personality files, but this is essentially duplicating
``user_data`` which is already persisted and made available to the config
drive and via the metadata service API and does not solve the security or
end user discoverability issues.

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion:

#. Deprecate the ``personality`` parameter from ``POST /servers`` create server
   API and ``POST /servers/{server_id/action`` rebuild server API. Specifying
   that parameter after the microversion will result in a `400 Bad Request`
   error response.

#. Support passing ``user_data`` to the rebuild server action API. The schema
   would be the same as the ``POST /servers`` server create API::

    'user_data': {
        'type': 'string',
        'format': 'base64',
        'maxLength': 65535
    }

#. Deprecate the ``maxPersonality`` and ``maxPersonalitySize`` response
   parameters from the ``GET /limits`` API.

#. Deprecate the ``injected_files``, ``injected_file_path_bytes``,
   ``injected_file_content_bytes`` parameters from the following APIs:

   - ``GET /os-quota-sets/{tenant_id}``
   - ``PUT /os-quota-sets/{tenant_id}``
   - ``GET /os-quota-sets/{tenant_id}/defaults``
   - ``GET /os-quota-sets/{tenant_id}/detail``
   - ``GET /os-quota-class-sets/{id}``
   - ``PUT /os-quota-class-sets/{id}``

Security impact
---------------

Removing the ``VFSLocalFS`` fallback code will actually be good for security.

Notifications impact
--------------------

None; personality files were never part of any notifications (thankfully).

Other end user impact
---------------------

Update python-novaclient CLIs and related python API bindings, specifically:

- Deprecate the ``--file`` option from the ``nova boot`` and ``nova rebuild``
  CLIs and API bindings.
- Add ``--user-data`` to the ``nova rebuild`` CLI and API bindings.
- Deprecate the ``maxPersonality`` and ``maxPersonalitySize`` fields from the
  ``nova limits`` and ``nova absolute-limits`` CLIs and API bindings.
- Deprecate ``injected_files``, ``injected_file_content_bytes``, and
  ``injected_file_path_bytes`` from the ``nova quota-show``,
  ``nova quota-update``, ``nova quota-defaults``, ``nova quota-class-show``,
  and ``nova quota-class-update`` CLIs and API bindings.

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
  Matt Riedemann (mriedem) <mriedem.os@gmail.com>

Work Items
----------

- Add a microversion to make the proposed changes to the server create, server
  rebuild, limits, os-quota-sets and os-quota-class-sets APIs.
- Make the related changes in python-novaclient.


Dependencies
============

None


Testing
=======

- Unit tests for negative scenarios.
- Functional API samples tests for the normal API flows with the new
  microversion.


Documentation Impact
====================

- The compute API reference will need to be updated for the new microversion
  impacts.
- The `Manage Compute service quotas`_ doc will need to be updated.

.. _Manage Compute service quotas: https://docs.openstack.org/nova/pike/admin/quotas.html

References
==========

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2016-July/098703.html
.. [2] http://lists.openstack.org/pipermail/openstack-dev/2016-November/107233.html
.. [3] https://review.openstack.org/#/c/324720/
.. [4] http://lists.openstack.org/pipermail/openstack-operators/2017-October/014309.html

More mailing list discussion from Ocata: http://lists.openstack.org/pipermail/openstack-dev/2016-November/107195.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
