..
 This work is licensed under a Creative Commons Attribution 3.0 Unported

 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Strictly isolate group of hosts for an image
============================================

https://blueprints.launchpad.net/nova/+spec/restrict-image-isolation-with-defined-keys

The aim of this blueprint is to improve the filter
`AggregateImagePropertiesIsolation`

An operator wants to schedule instances for a specific image on a
pre-defined group of hosts. In addition, he wants to strictly isolate this
group of hosts for the image only and accept images without key scheduled
to other hosts.

Problem description
===================

Currently with the filter `AggregateImagePropertiesIsolation` we have the
possibility to define images that will be scheduled on a specific aggregate
following this matrix:

+--------------+------------+----------+----------+
| img \\ aggr  | key=foo    | key=xxx  | <empty>  |
+==============+============+==========+==========+
| key=foo      | True       | False    | True     |
+--------------+------------+----------+----------+
| key=bar      | False      | False    | True     |
+--------------+------------+----------+----------+
| <empty>      | True       | True     | True     |
+--------------+------------+----------+----------+

*Table 1: row are image properties, col are aggregate metadata.*

The problem is:
 * An image without key can still be scheduled in a tagged aggregate
 * The hosts outside aggregates or in a no-tagged aggregate can still accept a
   tagged image

Proposed change
===============

We would like to add an option to:
 * Make tagged aggregate refuse not-tagged images
 * Make not-tagged aggregate accept ONLY not-tagged images

+--------------+------------+----------+----------+
| img \\ aggr  | key=foo    | key=xxx  | <empty>  |
+==============+============+==========+==========+
| key=foo      | True       | False    | False    |
+--------------+------------+----------+----------+
| key=bar      | False      | False    | False    |
+--------------+------------+----------+----------+
| <empty>      | False      | False    | True     |
+--------------+------------+----------+----------+

*Table 2: row are image properties, col are aggregate metadata*

We propose to add global option `aggregate_image_filter_strict_isolation` in
the filter which dictates strictness level of the isolation:

 * aggregate_image_filter_strict_isolation = False:
   the filter functions as before (Tab. 1)
 * aggregate_image_filter_strict_isolation = True:
   the filter functions as proposed decision (Tab. 2)

*For backward compatibility this option will be set by default to False.*

We also propose to add this option configurable in per-aggregate.


Alternatives
------------

* An alternative solution would be to create a new filter that inherits from
  `AggregateImagePropertiesIsolation`.
* A more configurable solution could be to use two config options
  `allow_untagged_images_in_tagged_aggregate=True` and
  `allow_tagged_images_in_untagged_aggregate=True` but currently we cannot
  find any cases of using this alternative.

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

None

Performance Impact
------------------

None

Other deployer impact
---------------------

* Operator needs to update the scheduler's `nova.conf` to set the option
  `aggregate_image_filter_strict_isolation`.

::
  aggregate_image_filter_strict_isolation=True

* To configure per-aggregate Operator needs to set the metadata.

::
  nova aggregate-set-metadata aggrA
  aggregate_image_filter_strict_isolation=True

*Note: For existing system, instances will be not re-scheduled. The operator
always have the possibility to do migration.*

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sahid-ferdjaoui

Work Items
----------

* Updating `AggregateImagePropertiesIsolation` to accept the new global option.
* Updating `AggregateImagePropertiesIsolation` to accept per-aggregate
  configuration.

Dependencies
============

None

Testing
=======

* Unit tests can validate the expected behavior.

Documentation Impact
====================

We need to update the documentation:
  'doc/source/devref/filter_scheduler.rst'

References
==========

* http://docs.openstack.org/developer/nova/devref/filter_scheduler.html#filtering
* https://review.openstack.org/#/c/80940/
