..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Libvirt: add perf event support
===============================

https://blueprints.launchpad.net/nova/+spec/support-perf-event

The purpose of this blueprint is to add nova an ability to support perf event
to gain statistic (for example cpu cache usage) for each instance. These
perf event data will be collected by Ceilometer. [1]_

Problem description
===================

Perf event is a Linux feature that provides a framework for analyzing
performance events at both hardware and software levels. Through a
list of measurable events we can measure events coming from different
resources (like context-switches, cache misses, etc.) and gain statistic
for each instance.

Perf has integrated to libvirt from 1.3.3 and it now supports to gain cpu
cache and more event type will be added. We can enable perf support in Nova.

Use Cases
----------

As a cloud operator, he/she wants to know if instances in a cloud occupy
what kinds of resources, for example, cpu, memory, cpu cache, memory
bandwidth etc., and also the amount of resource of the instance. These kinds
of monitor data can be collected from Ceilometer. With these monitor data,
the operatior can do some analysis to identify what is the most important
resource for this instance and he/she can do further operations like
migrate to some other hosts to provide better resources to meet customers SLA.

The Ceilometer spec requires to nova have perf support.[1]_

Proposed change
===============

Add new libvirt driver list configure option `enabled_perf_events`, which
is a list to indicate the perf event type, default is `[]`.

Add missing elements when generating XML definition in libvirt driver to
support perf event per the configuration of `enabled_perf_events`. Only
supported event with proper Libvirt version, it will be ignored if the
version of Libvirt is too old.

For example we have enabled_perf_events=['cmt'], the XML element will be
like this::

  <perf>
    <event enable="yes" name="cmt"/>
  </perf>

Libvirt requires this flag in it's XML to initialize a file descriptor
before we gain the statistic, the polling won't be started until we call
Libvirt API.

In this spec, we don't propose nova to polling statistic data itself,
Ceilometer can benefit from this configuration.

Alternatives
------------

Another solution is enable perf event per instance by using flavor's
extra_spec, like adding 'perf:event=cmt,...', add aggregate to host.
It's complex to enable it from operators.

The reason not using flavor's extra_spec is this is not a spec user
should take care, it's not a feature of VM, but things the platform can
provide us, so if platform can provide us such feature, we can benifit from
it. It doesn't make sense that a user wants an instance schedule to a host
which can have performance monitor.

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

There won't be performance impact. When perf event is enabled,
the operation is just to write the count into the memory,
and the impact can be almost ignored, especially we just
enable events for VMs (not for each processes).

No addition API call is requires at all.

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
  Eli Qiao <liyong.qiao@intel.com>

Other contributors:
  qiaowei-ren <qiaowei.ren@intel.com>


Work Items
----------

The primary work items are:

* Add new libvirt driver configuration option.
* If the version of libvirt is new enough to support the flags in the xml,
  update the libvirt guest XML configuration when one or more perf events
  are specified in libvirt driver configuration.

Dependencies
============

And this spec will depend on the following libraries:

* libvirt >= 1.3.3

Testing
=======

* Add unit test case to verify guest XML has been updated correctly.

Documentation Impact
====================

* Add explanation of new added libvirt configuration.

References
==========

.. [1] `ceilometer l3-cache-meter spec <https://blueprints.launchpad.net/ceilometer/+spec/l3-cache-meter/>`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - introduced.
