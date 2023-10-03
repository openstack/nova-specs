..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Tooling and Docs for Unified Limits
===================================

https://blueprints.launchpad.net/nova/+spec/unified-limits-nova-tool-and-docs

In the Yoga release support for Unified Limits was added in Nova as an
experimental feature to get early feedback and fix issues that were found by
operators trying it out. Now that a few releases have passed, we want to go
ahead and formalize the unified limits quota driver by creating a tool to help
operators copy their existing legacy quota limits from Nova to unified limits
in Keystone, publish official documentation in the Nova quota documentation,
and removing the note on the ``[quota]driver=nova.quota.UnifiedLimitsDriver``
config option indicating its experimental status.

.. note::

   There are no immediate plans to deprecate legacy quota system in Nova at
   this time. The objective of this work is to provide a better experience for
   users who are opting in to using unified limits in Nova.

Problem description
===================

Currently there is no documentation in the Nova docs about unified limits and
there isn't any automated tool for generating unified limits in Keystone from
existing Nova legacy quota limits.

Use Cases
---------

* As an operator, I would like to use a tool to automatically copy my existing
  legacy quota limits from Nova to unified limits in Keystone.

* As an operator, I would like formal documentation for unified limits quotas
  to be available.

Proposed change
===============

We propose to create an automated tool, for example,
``nova-manage limits migrate_to_unified_limits`` that will read existing legacy
quota limits from the Nova database and config options and create equivalent
unified limits for them in Keystone using the Keystone REST API. It will be
able to migrate both default limits and project-scoped limits. It will not
migrate user-scoped limits as they are not supported by unified limits.

The ``nova-manage`` command will follow the precedence for `checking quota`_
and:

#. Check the ``nova_api.quotas`` database table and for each row call the
   Keystone ``POST /limits`` API with the project_id, resource name, and
   resource_limit. These are the project-scoped limits.

#. Check the ``nova_api.quota_classes`` database table to see if there are rows
   with class_name ``default``. If there are, for each row with class_name
   ``default`` call the Keystone ``POST /registered_limits`` API with the
   resource_name and default_limit. These are the default limits that apply to
   all projects.

#. Check the following config options:

   .. code-block:: ini

      [quota]
      instances
      cores
      ram
      metadata_items
      injected_files
      injected_file_content_bytes
      injected_file_path_length
      key_pairs
      server_groups
      server_group_members

   For each config option, use its set value or default value to call the
   Keystone ``POST /registered_limits`` API with the resource_name and
   default_limit, if the resource_name does not already have a registered limit
   in Keystone. These are default limits that apply to all projects.

#. The ``nova_api.project_user_quotas`` database table will be ignored because
   user-scoped limits are not supported by unified limits.

.. _checking quota: https://docs.openstack.org/nova/latest/admin/quotas.html#checking-quota

We will add formal docs about unified limits to the Nova docs and remove the
note on the ``[quota]driver`` config option about the
``nova.quota.UnifiedLimitsDriver`` being in a development state.

Alternatives
------------

Operators can create unified limits using the ``openstack limit`` openstack
client commands without a provided tool.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

End users will be able to read documentation about how quotas work with unified
limits.

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers will have the option of using the quota limit migration tool to copy
existing legacy Nova quota limits into Keystone unified limits instead of using
openstackclient commands or otherwise calling the Keystone REST API manually.

Developer impact
----------------

None

Upgrade impact
--------------

There is no upgrade impact with the quota limit migrate tool in that there is
no restriction on when operators can run the tool. They can copy quota limits
into Keystone at any time, unrelated to an upgrade. The only requirements are
that the Keystone API needs to be available and ``nova-manage`` must have
access to a Nova config that has ``[api_database]connection`` configured so
that it can access the Nova quota database tables.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  melwitt

Work Items
----------

* Develop a ``nova-manage limits migrate_to_unified_limits`` command to copy
  existing legacy Nova quota limits from the Nova database and config options
  to unified limits by calling the Keystone REST API

* Write documentation for unified limits in Nova

* Remove note from ``[quota]driver=nova.quota.UnifiedLimitsDriver`` about the
  driver being in a development state

* Collaborate with Keystone team to remove the docs warning in
  https://docs.openstack.org/keystone/latest/admin/unified-limits.html
  about the unified limits API labeled as experimental

Dependencies
============

* https://specs.openstack.org/openstack/nova-specs/specs/yoga/implemented/unified-limits-nova.html

Testing
=======

Unit and/or functional testing for the quota limit migrate tool wil be added.

We can also test the quota limit migrate tool alongside the existing
nova/tools/hooks/post_test_hook.sh unified limits coverage in the nova-next CI
job.

Documentation Impact
====================

Operators will be most affected by the addition of Nova unified limits
documentation. The following docs will need to be updated:

* https://docs.openstack.org/nova/latest/user/quotas.html

* https://docs.openstack.org/nova/latest/admin/quotas.html

* https://docs.openstack.org/nova/latest/cli/nova-manage.html

References
==========

* https://etherpad.opendev.org/p/nova-bobcat-ptg#L415

* https://docs.openstack.org/keystone/latest/admin/unified-limits.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.2 Bobcat
     - Introduced
