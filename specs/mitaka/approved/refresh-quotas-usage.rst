..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Refresh quotas usage
==========================================

https://blueprints.launchpad.net/nova/+spec/refresh-quotas-usage

For some reasons [*]_, the quotas usage can be out of sync.
When a quota is wrongfully reached, a user cannot launch new VMs anymore.
This "refresh" feature allows operators to quickly unblock users without
manually running queries against the database or temporarily increase the
quota.

.. [*] It seems that there are several root causes and there is no procedure
       to reproduce bugs. Although these root causes will eventually be
       identified, we cannot guarantee that some bugs will not occur again.


Problem description
===================

Quotas usage can be out of sync in quota_usages table.
The number of used resources may not reflect the actual use.
For instance we can see 7 cores used while the actual use is only 4.

Use Cases
----------

An end user can be blocked if a quota is wrongfully reached for a resource
type.

If a refresh quotas usage feature is implemented in Nova an operator can
correct the usage without running a SQL query directly on the database.


Project Priority
-----------------

None

Proposed change
===============

Currently, the "refresh quotas usage" feature is hidden inside SQLAlchemy
implementation.
As described in "Alternatives" paragraph, the function
``nova.db.sqlalchemy.api.quota_reserve()`` can refresh the database under
some circumstances.

The change consists to:

* Create a function in the DB API to refresh quotas usage:
  ``nova.db.api.quota_usage_refresh()``

* Do an "extract function" refactoring on
  ``nova.db.sqlalchemy.api.quota_reserve()`` to implement the aforementioned
  ``quota_usage_refresh()`` DB API. That is:
  ``nova.db.sqlalchemy.api.quota_usage_refresh()``.

* Expose the ``nova.db.api.quota_usage_refresh()`` feature through a
  nova-manage command.


The nova-manage command would look like:

::

    $ nova-manage project quota_usage_refresh --project <Project name>
        [--user <User name>] [--key <Quota key>]

If ``--key`` is omitted, all quota resources are refreshed.

Specifying ``--user`` is optional since some resources are per-project quotas,
like fixed_ips, floating_ips and networks. Similarly, the ``nova quota-update``
command takes an optional user.

Example:

::

    $ nova-manage project quota_usage_refresh --project demo --user john_doe
        --key cores

    $ nova-manage project quota_usage_refresh
        --project f85aa788e8ee48fca3da27e0579d3597
        --key cores


Alternatives
------------

Another nova-manage command
"""""""""""""""""""""""""""

Another nova-manage command can use the already implemented
``nova.quota.usage_reset()`` function.

Here is the docstring of this function, note the "for a particular user":

::

    Reset the usage records for a particular user on a list of
    resources.  This will force that user's usage records to be
    refreshed the next time a reservation is made.

    Note: this does not affect the currently outstanding
    reservations the user has; those reservations must be
    committed or rolled back (or expired).

    :param context: The request context, for access checks.
    :param resources: A list of the resource names for which the
                      usage must be reset.


"Reset" means "set to -1 in database".

The resulting command would be:

::

    $ nova-manage project quota_usage_reset --project <Project name>
        --user <User name> [--key <Quota key>]

If ``--key`` is omitted,  all quota resources are reset.

Pros
""""

Only ``nova/cmd/manage.py`` is modified.
Unlike quota_usage_refresh, no changes are required at the database API level.


Cons
""""

The main difference with quota_usage_refresh is that the user won't see actual
quota usages until the next reservation.


Credits: This command is proposed by Joe Gordon (cf. patch set 2)


Configure Nova
""""""""""""""

We can enable quotas "auto refresh" in nova.conf thanks to:

* until_refresh (IntOpt) Count of reservations until usage is refreshed
* max_age       (IntOpt) Number of seconds between subsequent usage refreshes

These two settings (disabled by default) allow to refresh quotas usage but only
during a quota reservation. The algorithm is:

1. Check quota
2. until_refresh or max_age threshold reached?
3. If yes: refresh

Let's take an example: a quota of 10 instances is set on a tenant.

The quota is wrongfully reached:

* nova absolute-limits shows totalInstancesUsed = 10
* nova quota-show shows instances = 10

The actual instances number is 9.

When a user runs a ``nova boot`` he will get an error: "Quota exceeded".
Many users will stop here and contact their support. Actually, a second
``nova boot`` might succeed if the first one has refreshed the quotas usage
(depending on until_refresh or max_age threshold).
We would need to improve this behavior but it's off topic here.

Note that on Horizon a user will not able to spawn an instance (corresponding
to the first ``nova boot``) because the button is disabled when a quota is
reached.

To conclude:

* until_refresh or max_age need to be enabled but a cloud operator
  may not want to enable them if only few tenants encounter a bug on quotas
  usage.

* Even with these two settings enabled, we can't force a refresh.


Data model impact
-----------------

None

REST API impact
---------------

None

Policy changes
--------------

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

The feature hits the table quota_usages the same way
``nova.db.sqlalchemy.api.quota_reserve()`` does when triggering a refresh.


Other deployer impact
---------------------

None

Developer impact
----------------

Other implementations of ``nova.db.api`` should implement
``nova.db.api.quota_usage_refresh()``.

Handle nested projects?
https://blueprints.launchpad.net/nova/+spec/nested-quota-driver-api


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem@us.ibm.com>

Other contributors:
  Romain Hardouin <romain.hardouin@cloudwatt.com>


Work Items
----------

Not a big change, this BP can be submitted as a whole.

Two subtasks:

* Change the DB API
* Implement the nova-manage command


Dependencies
============

None

Testing
=======

In-tree unit and functional testing should be sufficient.


Documentation Impact
====================

Document the new nova-manage command.


References
==========

* "nova quota statistics can be incorrect":
  https://bugs.launchpad.net/nova/+bug/1284424

* "Test job failes with FixedIpLimitExceeded with nova network":
  https://bugs.launchpad.net/nova/+bug/1353962

* "How to reset incorrect quota count?":
  https://ask.openstack.org/en/question/494/how-to-reset-incorrect-quota-count/

* "nova 'absolute-limits': [...] (they are wrong)"
  http://lists.openstack.org/pipermail/openstack/2014-November/010250.html

* "[...] usage now out-of-sync":
  https://ask.openstack.org/en/question/11943/deleted-vms-still-showing-in-nova-dashboard-usage-now-out-of-sync/

For information, on Horizon side:

* "absolute-limits sometimes returns negative value" :
    https://bugs.launchpad.net/nova/+bug/1370867
