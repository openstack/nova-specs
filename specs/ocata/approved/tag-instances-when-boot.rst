..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Support add tags for instances when booting
===========================================

https://blueprints.launchpad.net/nova/+spec/support-tag-instance-when-boot

This blueprint proposed to add support adding tags for instances when
booting.


Problem description
===================

Tags for servers are supported in microversion 2.26, but currently we can
only add tags to instances that are already existed in the cloud, that is,
we can not set tags to instances when we boot the instances. User will have
to first find the instances and then add tags with another API call. This
is not user-friendly enough when user doing bulk boot, it will be not
practical to add tags for those instances one by one afterwards.

Use Cases
---------

As an user, I would like to add tags to my instances when I boot them,
especially when I doing bulk boot, I may want to add some tags for the
instances created by this call.

Proposed change
===============

Add a new microversion to Servers create API to support adding tags
when booting instances. The number of tags can be added will be limited
by instance.MAX_TAG_COUNT just as what server-tags API does.

Alternatives
------------

Keep the current implementation.

Data model impact
-----------------

None

REST API impact
---------------

* URL:
    * /v2.1/servers:

* Request method:
    * POST

The tags data will be able to add to request payload ::

    {
        ...
        'tags': ['foo', 'bar', 'baz']
        ...
    }

The tags will be also be included in response if setted ::

    {
        ...
        'tags': ['foo', 'bar', 'baz']
        ...
    }

The tags will be an empty list if not setted ::

    {
        ...
        'tags': []
        ...
    }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

User will be able to set tags when boot instances using specific microversion.
python-novaclient will also make modifications to support this feature.

Performance Impact
------------------

None

Other deployer impact
---------------------

A new microversion will be added.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng

Work Items
----------

* Add tag instances support when booting
* Add related tests


Dependencies
============

None


Testing
=======

* Add related unittest
* Add related functional test
* Add related tempest test

Documentation Impact
====================

Add docs that mention the tags can be added when boot instances after
the microversion.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
