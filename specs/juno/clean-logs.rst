..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Nova logs shouldn't have ERRORs or TRACEs in them
==================================================

https://blueprints.launchpad.net/nova/+spec/clean-logs

Nova logs should be readable, sensible, and contain only errors and
traces in exceptional situations.

Problem description
===================

During a normal, successful, run of Tempest in the OpenStack gate we
get a large number of ERRORs and stack traces in the logs. This is for
passing results, which means the cloud should have been operating
normally.

Stack traces and errors in the logs under normal conditions make it
very difficult for operators to actually determine when real issues
are happening with their OpenStack cloud. We've seen this even as part
of normal development where people will be tricked in debugging
OpenStack issues by the ERRORs, when the real issue is masked.

Proposed change
===============
We should clean up all the instances of Stack Traces and Errors
happening under a normal Tempest run. This means addressing the bugs
that this currently exposes, as well as changing some logging levels
where we are logging Exceptions at log.exception level that are
actually expected (and thus should be a log.debug or deleted
entirely).

See Testing section below for completion criteria.

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------
This will change some log messages for clarity. Users that built
filters around the old error messages will have to adjust their
filters. As they were probably filtering those messages out, this
should be minimal.

Performance Impact
------------------

None. (Possibly miniscule, and largely undetectable, boost because of
not dumping stack traces so much.)

Other deployer impact
---------------------

None.

Developer impact
----------------

Developers will have to be more careful about doing arbitrary
log.exception calls inside Nova code once this is enforcing, and will
need to be more careful on catching appropriate exceptions for
expected conditions.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sdague

Work Items
----------

The services should be tackled in this order (consider cleaning of
each one a work item):

 * n-sched
 * n-net
 * n-api
 * n-cpu

n-sched and n-net are currently the most critical to clean up as they
are services that surface testing don't hit directly (only indirectly
through n-api calls). Ensuring that they don't have unexpect behavior
in dumping stack traces will provide extra verification that those
services are working as expected.


Dependencies
============

None


Testing
=======

Testing will be accomplished by the tempest check_logs.py script
currently running in the gate. Once we are confident that we have
cleaned up a service, we remove that service from the allowed_dirty
list
https://github.com/openstack/tempest/blob/master/tools/check_logs.py#L33. After
that any change which causes there to be a stack trace or error in the
logs for that service will cause the tempest tests to fail, thus
blocking the change from merging.

Documentation Impact
====================

There will be a related effort in overall logging standards (to be
presented as a Juno cross project session) that will need to be
fleshed out in conjunction with this.

References
==========

 * Initial thread on Log Harmonization -
   http://lists.openstack.org/pipermail/openstack-dev/2013-October/017300.html
