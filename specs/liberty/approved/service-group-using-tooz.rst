..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================================
Replace Zookeeper, Memcache servicegroup driver with Tooz drivers
=================================================================

https://blueprints.launchpad.net/nova/+spec/tooz-for-service-groups

Nova's zookeeper and memcache service group drivers have fallen into
disrepair. `tooz`_ (a new oslo library that has been under development
for around a year) is able to provide the grouping concepts in a way
that means nova would no longer need to maintain the zookeeper and memcache
service group drivers.

Problem description
===================

Nova currently has to maintain, test and support db, memcache, zookeeper
drivers. The db driver is currently the only widely deployed driver.

The memcache and zookeepr drivers have since fallen into disrepair.
For example, the Zookeeper driver uses evzookeeper which is no longer actively
maintained and doesn't work with eventlet >= 0.17.1.

If Nova adds a `tooz`_ service group driver, it means Nova can deprecate the
existing zookeeper and memcache drivers, and eventually no longer have to
maintain that code.

Longer term, its hoped users will be able to migrate away from the db driver
to the more promising systems supported by `tooz`_, but this effort it outside
the scope of this specification.

Use Cases
----------

* In scope: Migrate existing memcache and zookeeper driver users to the
  new tooz service group driver

* Out of scope: Existing db driver users migrate to the tooz driver

Project Priority
-----------------

None

Proposed change
===============

Before this effort can start, we need to fix the service group API
abstraction:
https://blueprints.launchpad.net/nova/+spec/servicegroup-api-control-plane

The above effort is likely to extend the amount of the data that needs
to be stored by tooz, such as if the node is enabled or disabled.
At the same time, this will make clear many of the current limitations of the
existing non-DB service group drivers that need to be avoided in the
tooz driver.

A ToozServiceGroupDriver will be added that implements the existing
ServiceGroupDriver interface. Although the above work may adjust the
interface slightly.

It will simply wrap calls into the `tooz`_ library, and raise Nova
specific exceptions for errors that are hit.

Alternatives
------------

We could do nothing, but that is unlikely to get the broken drivers fixed,
leading to lots of confusion for users, and painful upgrades.

We could just drop support for memcache and zookeeper service group drivers
all together, but there appears to be a community that wants to support them
via `tooz`_ and it would be good to support that community.

We could attempt a live-upgrade from Nova's memcache and zookeeper drivers
to the new `tooz`_ driver, but given those drivers appear to be currently
broken, that seems like wasted effort. User feedback during the deprecation
cycle can be used to decide if this is needed before we remove the drivers
from the Nova code base.

Data model impact
-----------------

The DB service group driver will be unaffected by this change.

The memcache and zookeeper drivers do not store information in those system in
the same way that `tooz`_ stores information. But Nova is just a user of the
`tooz`_ library, so we can skip over the details of that change here.

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

None

Performance Impact
------------------

None expected, there will still need to be periodic heartbeats into memcache
to ensure the memcache key is not expired, zookeeper clients (even using
`kazoo`_ also need to periodically check-in with zookeeper) so nothing should
be drastically different in this arena.

Other deployer impact
---------------------

There will be a new configuration value for the `tooz` driver, using a URL.
A few examples of this URL format::

    servicegroup_tooz_url = "kazoo://127.0.0.1:2181?timeout=5"
    servicegroup_tooz_url = "memcached://localhost:11211?timeout=5"
    servicegroup_tooz_url = "redis://localhost:6379?timeout=5"

Given the current state of Nova's memcache and zookeeper drivers,
we are adopting a very simple transition approach.
It will be something like:

* Upgrade to liberty, using existing service group driver

* Restart nova-compute first.

* Update configuration to point at new service group driver

* Restart nova-api after updating configuration.

We will look for feedback from users on this approach during the deprecation
window for the memcache and zookeeper drivers, to assess if the simpler
approach will be sufficient.


Developer impact
----------------

Nova developers may have to interact more with the oslo community (and
the tooz subcommunity) when learning, understanding, and integrating with
tooz.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
vilobhmm

Work Items
----------

* Implement the new tooz servicegroup driver.

* Document the migration from existing drivers to the tooz driver,
  including the implementation of any required data migration.

* Add deprecation warnings for memcache and zookeeper drivers.

* Complete testing work detailed below.

Dependencies
============

This spec adds a dependency on tooz

This work also depends on the work to tidy up the service group API:
https://blueprints.launchpad.net/nova/+spec/servicegroup-api-control-plane

Testing
=======

* Work with infra to ensure one of the gate jobs starts using the tooz driver

Documentation Impact
====================

* Describe the new tooz driver and its configuration options

* Describe how to migrate from memcacahe or zookeeper to `tooz`

* Communicate the deprecation of the memcache and zookeeper drivers

References
==========

Tooz adoption by oslo:

- https://review.openstack.org/#/c/122439/

Tooz rtd:

- http://docs.openstack.org/developer/tooz/

Others:

- https://review.openstack.org/#/c/190322/
- https://wiki.openstack.org/wiki/Oslo/blueprints/service-sync
- http://specs.openstack.org/openstack/ceilometer-specs/specs/juno/cent\
  ral-agent-partitioning.html
- http://lists.openstack.org/pipermail/openstack-operators/2015-Marc\
  h/006674.html
- http://lists.openstack.org/pipermail/openstack-dev/2015-April/062737.html

.. _tooz: https://pypi.python.org/pypi/tooz
.. _kazoo: http://kazoo.readthedocs.org/
