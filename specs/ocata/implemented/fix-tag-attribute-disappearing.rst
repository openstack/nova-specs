..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Fix tag attribute disappearing
==============================

https://blueprints.launchpad.net/nova/+spec/fix-tag-attribute-disappearing

In the context of virtual device role tagging at instance boot time, a bug [1]_
has caused the tag attribute to no longer be accepted starting with version
2.33 for block_device_mapping_v2 and starting with version 2.37 for networks.
In other words, block devices can only be tagged in 2.32 and network interfaces
between 2.32 and 2.36 inclusively. This spec introduces a new API microversion
that re-adds the tag attribute to both block_device_mapping_v2 and networks.


Problem description
===================

For block_device_mapping_v2, the problem stems from the use of the equality
comparison in [2]_. It causes the Nova API to accept the tag attribute only in
microversion 2.32. The intent was of course to support tags in all versions
greater than or equal to 2.32, but the implementation mistake was missed by the
author, the reviewers, and tests.

In the case of networks, microversion 2.37 introduced a new choice for the
network item in the instance boot request body [3]_. In addition to the
previously allowed dictionary containing one of port, uuid or fixed_ip, a new
string item - either 'auto' or 'none' - became accepted. When writing the
schema for this change, the previous schema had to be copied and included as
one of the two choices. It is this copying that introduced the error: the tag
item was not copied along with the rest of the schema.

Use Cases
---------

As an end user, I want block device role tagging to continue working beyond
microversion 2.32.

As an end user, I want network interface role tagging to continue working
beyond microversion 2.37.

Proposed change
===============

This spec proposes to document the bug in api-ref and reno while at the same
time reintroducing the tag attribute to both block_device_mapping_v2 and
networks in a new API microversion.

In order to prevent future bugs of the same kind, the microversion will be
passed to extensions as an APIVersionRequest object and APIVersionRequest's
__eq__ operator will be removed. This will dissuade future code from doing
version equality comparisons.

One of the reasons the original bug was missed is that functional tests are
only run on the specific microversion they are concerned with. That is, the
tests for 2.32 are only run against 2.32. While having every test class for a
new microversion inherit from the test class for the previous microversion (for
example, ServersSampleJson232Test inheriting from ServersSampleJson231Test) is
wasteful, this spec proposes to run all of the API samples tests against
2.latest. This will ensure no accidental breakage at any single point in the
microversion timeline.

Alternatives
------------

Because the tag attribute needs to be reintroduced to the API, a new
microversion is necessary, as per Nova project policy. There are therefore no
alternatives.

Data model impact
-----------------

None.

REST API impact
---------------

This spec impacts only the body of the POST /servers method. The tag attribute
is re-added to the networks and block_device_mapping_v2 items.

Networks example::

    {
        "server": {
            "name": "nic-tagging",
            "imageRef": "70a599e0-31e7-49b7-b260-868f441e862b",
            "flavorRef": "http://openstack.example.com/flavors/1",
            "networks": {
                "uuid": "a0ef4e02-9150-418c-b4cf-cf4a86e92bf1",
                "tag": "nic1"
            }
        }
    }

Block device mapping example::

    {
        "server": {
            "name": "nic-tagging",
            "imageRef": "70a599e0-31e7-49b7-b260-868f441e862b",
            "flavorRef": "http://openstack.example.com/flavors/1",
            "block_device_mapping_v2": [{
                "boot_index": "0",
                "uuid": "ac408821-c95a-448f-9292-73986c790911",
                "source_type": "image",
                "volume_size": "25",
                "destination_type": "volume",
                "delete_on_termination": true,
                "tag": "disk1"
            }]
        }
    }

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Python-novaclient will be updated to work with the disappearance of the tag
attribute in 2.33 and 2.37. It will also be updated to use the new microversion
that reintroduces the tag attribute.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Artom Lifshitz (notartom)

Other contributors:
  None

Work Items
----------

* Implement a new API microversion that reintroduces the tag attribute to
  networks and block_device_mapping_v2.
* When calling extensions, pass the version as an APIVersionRequest object
  instead of a string.
* Run all API samples tests against 2.latest, except where an API feature has
  been removed.

Dependencies
============

None.

Testing
=======

A functional test will be added for the new API microversion. The existing
Tempest test [4]_ will be modified to test 2.32 and the new microversion that
reintroduces the tag attribute.

Documentation Impact
====================

The API reference will be updated to document the bug as well as the new API
microversion. Release notes will do the same.

References
==========

.. [1] https://bugs.launchpad.net/nova/+bug/1658571
.. [2] https://review.openstack.org/#/c/304510/64/nova/api/openstack/compute/block_device_mapping.py@77
.. [3] https://review.openstack.org/#/c/316398/37/nova/api/openstack/compute/schemas/servers.py
.. [4] https://review.openstack.org/#/c/305120/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
