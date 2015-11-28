..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================================
Adding new nova-manage cmd to list compute node metrics
========================================================================

https://blueprints.launchpad.net/nova/+spec/compute-node-metrics-api

We need a way to list the available metrics stored in the DB
which is reported by the compute monitor plugins, so the administrator
can easily configure the scheduler's MetricWeigher settings.

Problem description
===================

With the Icehouse blueprint implementation
https://blueprints.launchpad.net/nova/+spec/utilization-aware-scheduling,
now various monitor plug-ins can be configured to report hypervisor
metrics periodically. These metrics could be used in scheduling process
through the MetricsWeigher configured by the administrator.

When the administrator wants to configure the settings for MetricsWeigher,
he/she need to know the exact metrics to make the settings working
properly. Currently, we don't have a way to let the administrator know what
metrics are available unless asking the administrator to look at the monitor
plug-ins code or looking in certain DB tables.

We need a way to list the available metrics currently reported
by the nova compute monitors and stored in the DB, so the administrator
can configure the MetricWeigher much more easily.

Use Cases
----------

The Administrator will use this way to list all the available metric names,
in order to configure the MetricsWeigher to work as expected.

Project Priority
-----------------

None

Proposed change
===============

A new nova-manage command will be added::

    nova-manage host_metric [--host=<host>] { list | show }

This command will load the information from nova DB about all the available
compute node metrics stored there. The 'list' action will list all the
available compute node metrics name, and the 'show' action will show all
the details of each metric.

Alternatives
------------

One alternative is to add a new method in
nova.compute.monitors.base.MonitorBase class that would return a list of
the metric names that each plugin supports.

A new top-level REST API resource will be added, it simply lists the metric
names which are returned by the new method mentioned above::

    GET /v2.1/host-metrics

A array 'metrics' will be returned in the response of this API, listing
all the metrics names. The response will looks like::

    200 OK
    {
        "host_metrics": [
            'cpu.kernel.time',
            'cpu.user.time',
            ......
        ]
    }

This new API by default is admin only.

Another alternative is to extend the current os-hypervisors API extension which
list all the information about the compute node hypervisor. It pulls the
information from the DB, but it ignores the metrics related information.

We need to modified the os-hypervisors API extension to list the metrics
of each compute node hypervisor through the following restful API call::

    GET /v2.1/os-hypervisors/{hypervisor_id}/metrics

The above API would query the DB and return the metrics stored in the DB
for the specified compute node hypervisor.

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

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lianhao-lu

Other contributors:
  None

Work Items
----------

* add new nova-manage command


Dependencies
============

https://review.openstack.org/#/q/project:openstack/nova+branch:master+topic:bug/1468012,n,z


Testing
=======

New unit test cases will be added.

Documentation Impact
====================

The admin configuration documentation need to be updated.


References
==========

None

