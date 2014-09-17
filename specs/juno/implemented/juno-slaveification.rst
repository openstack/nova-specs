..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
More periodic tasks to slave for Juno
==========================================

https://blueprints.launchpad.net/nova/+spec/juno-slaveification

In the Icehouse development cycle we gave deployers the option to offload
most reads from nova-compute periodic tasks to a DB replication slave.
We will continue this work in Juno by "slaveifying" the rest of the
periodic tasks where appropriate.

Problem description
===================

Currently the accepted way to scale the database for reads and writes in Nova
is to do a multi-master setup or use some sort of database clustering. The
problem with this approach is that while read scalability is potentially
increased by making more hardware resources available (CPU, RAM, iops, etc).
Write scalability is decreased and more operational complexity is inherited.

Proposed change
===============

I would like to continue the work done in Icehouse by completing the
"slaveification" of periodic tasks.

Alternatives
------------

There are alternative ways to scale reads and writes both:

-Handling scaling within the application through some sort of sharding scheme.
-Handle scaling at the DB level.

We have a sharding model, cells, in Nova currently. It could be argued that
time would be better spent improving this approach rather than spending time
trying to scale it using available DB technologies.

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

No negative changes, hopefully this allows us to take some load off of
a "write master" and offload them to a slave or slaves.

Other deployer impact
---------------------

If a deployer changes the slave_connection configuration parameter in the
database section it is assumed that they are accepting the behavior of
having all reads from periodic tasks be sent to that connection. The
deployer needs to be educated and aware of the implication of running a
database replication slave and fetching actionable data from said slave.
These include, but may not be limited to:

-Need for monitoring of the slave status
-Operational staff familiar with maintenance of replication slaves
-Possibility to operate on data that is slightly out of date

See https://wiki.openstack.org/wiki/Slave_usage


Developer impact
----------------

Developers should consider which reads might benefit from optionally using
a slave handle. When new reads are introduced, consider the context in which
the code is called. Will it matter if this code operates on possibly out of
date data? Is the benefit of offloading reads greater than an inconvenience
caused by acting on old data?

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <geekinutah>

Other contributors:
  <None>

Work Items
----------

Slaveify the following periodic tasks in nova/compute/manager.py

update_available_resource
_run_pending_deletes
_instance_usage_audit
_poll_bandwidth_usage
_poll_volume_usage

Dependencies
============

We will need to have an object for bw_usage, this is covered by
https://blueprints.launchpad.net/nova/+spec/compute-manager-objects-juno

Testing
=======

Currently there is no testing in Tempest for reads going to the alternate
slave handle. We should add a replication slave to our test runs and test
the periodic tasks with and without slave_connection enabled.

Documentation Impact
====================

The operations guide should be updated and provide instructions with references
to MySQL and Postgres documentation on setting up and maintaining slaves. We
should also talk about HA possibilities with asynchronous slaves and various
automation frameworks that deal with this problem. It would also be good to
explain that while being able to specify a slave_connection is primarily a
scaling feature, the ability to use it for availability purposes is there.

References
==========

https://wiki.openstack.org/wiki/Slave_usage

The original blueprint with code history and discussion:
https://blueprints.launchpad.net/nova/+spec/db-slave-handle

The Icehouse blueprint:
https://blueprints.launchpad.net/nova/+spec/periodic-tasks-to-db-slave
