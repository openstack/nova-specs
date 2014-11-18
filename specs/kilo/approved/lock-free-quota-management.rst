..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
A lock-free quota implementation
================================

https://blueprints.launchpad.net/nova/+spec/lock-free-quota-management

Implement a lock-free quota management algorithm that removes the use of
the SELECT FOR UPDATE in the database API.

Problem description
===================

When launching a single instance in Nova, more than 120 database queries may
be made against the Nova, Neutron, Glance and/or Cinder databases. Of these
queries, a significant portion of them involve quota management tasks --
checking for existing quotas, checking for existing project and user usage
records, claiming the resources used in a reservation, and either committing
or rolling back those reservations once the launch sequence succeeds or fails.

The `SELECT FOR UPDATE` SQL construct is used in Nova in a couple places, to
ensure that no two concurrent threads attempt to update the same rows in the
database. When a thread selects records with `SELECT FOR UPDATE`, the thread
is announcing that it intends to modify the records it is reading from the
table -- this is called a write-intent lock. If another thread wants to update
the same set of records, it will issue a `SELECT FOR UPDATE` call, and this
call will wait until the first thread has completed the transaction and
either issued a `COMMIT` or a `ROLLBACK`.

In the case of traditional RDBMS systems like PostgreSQL or MySQL, calls to
`SELECT FOR UPDATE` are, by nature, a detriment to scalability, since only
a single thread may hold the write-intent lock on the same rows in the table
at any given time. All other threads must wait while the single writer thread
finishes what it is doing. In the case of Nova, the use of `SELECT FOR UPDATE`
is predominantly in two areas: quota management and assignment of free IP
addresses in nova-network's IPAM layer.

In addition to `SELECT FOR UPDATE`'s inherent scalability issues, a popular
replication variant of MySQL, called MySQL Galera, does not support the
write-intent locks that `SELECT FOR UPDATE` requires. What this means, in
practice, for deployers of Nova with MySQL Galera, is that occasionally the
MySQL client will return a deadlock error when two threads simultaneously
attempt to change the same set of rows. A deadlock in the traditional sense
of the term does not actually occur, but Galera raises the error code for
an InnoDB lock wait timeout (deadlock has occurred) when something called a
certification failure happens. A certification failure happens when two
threads writing to two different nodes in a Galera cluster attempt to
`UPDATE` the same set of rows in the same table during the same time interval.
Instead of causing MySQL to contain inconsistent data (two nodes having a
different idea of the underlying data), Galera simply causes both threads to
fail and thus issue a `ROLLBACK` of the containing transaction. This is
different behavior from standard MySQL, in which a similar situation would
cause just one of the threads to `ROLLBACK` after receiving a lock wait
timeout error, and the other thread's `UPDATE` would succeed. The reason that
this "deadlock" is not actually a deadlock in the Galera case is that the
entire process happens without any actual waits or timeout loops. Each
conflicting thread is simply sent an error and that thread issues a
`ROLLBACK` of the current SQL transaction.

Since MySQL Galera is, by far, the most popular high-availability database
deployment option currently in the operator ecosystem, some changes are
required in the quota management code to replace the use of
`SELECT FOR UPDATE` with a lock-free implementation that suffers neither
scalability problems nor the Galera-specific quasi-deadlock problems.

Use Cases
---------

A deployer typically uses a system like Tempest or Rally to provide an
"acceptance test" of their OpenStack deployment. Both of these systems stress
the Nova system by attempting to spawn and take actions against many instances,
using many users and projects. Both of these tests realiably produce error
scenarios where from the Nova log files, the deployer can see that a deadlock
retry mechanism is being used to handle failure of the MySQL Galera cluster to
certify quota usage update records. This deadlock retry mechanism is
heavy-handed and clearly affects the performance and scalability of Nova. The
deployer wants to see the Nova logs free of retry messages, and would like to
see improved throughput of the system as a whole.

Project Priority
----------------

This is not related to any of the project priorities listed for Kilo.

Proposed change
===============

The proposed solution is to borrow a page from obstruction-free and lock-free
algorithm design and use a "compare and swap" method that allows the thread
that intends to change the quota usage records for a user or project to issue
a standard `SELECT` statement for those records, and when that thread goes
to update those records, it first checks that the state of records is what
the thread previously knew to exist. The `UPDATE` statement will include a
`WHERE` condition that will ensure that the rows are *only* updated in the
table IFF the current row values are what the thread thought they were when
previously reading the rows with the `SELECT` statement. The thread will
check the number of rows affected by the `UPDATE` statement. If the number of
rows affected is 0, then a randomized exponential backoff loop will be hit and
the process of reading and then `UPDATE` ing with the `WHERE` condition will
repeat until a pre-defined number of tries has been attempted.

This algoritm is lock-free, in that no record locks of any kind are taken at
any point in the quota management transactions.

Alternatives
------------

None

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

We will work with the Rally developer team to identify some pre and post
benchmarks that should demonstrate better concurrency with this lock-free
implementation under both MySQL and PostgreSQL deployments.

Other deployer impact
---------------------
None

Developer impact
----------------
None

Implementation
==============

We will implement the lock-free algorithm entirely in the quota_reserve(),
quota_rollback() and quota_commit() DB API methods.

The use of `with_lockmode('update')` shall be removed from the query object
construction in the `_get_project_user_quota_usages()` method in
`nova.db.sqlalchemy.api`. Within `quota_reserve()`, `quota_commit()` and
`quota_rollback()`, we will change the algorithm from this *simplified*
pseudo-code for `quota_reserve()`::

    start_transaction:

        usage_records = get_and_lock_usage_records()

        reservations = []
        for resource, amount in requested_resource_changes:

            reservation = reservation_record_create(resource, amount)
            reservations.append(reservation)

    commit_transaction
    return reservations

to this::

    current_usage_records = get_usage_records()

    for resource, amount in requested_resource_changes:

        while num_attempts < max_attempts:
            if usage_records_update(resource, amount,
                                    current_usage_records):
                break
            num_attempts++
            current_usage_records = get_usage_records()

    return requested_resource_changes

where the `usage_records_update()` method would look like this, again,
in pseudo-code::

    def usage_records_update(resource, amount, current_records):

        sql = "UPDATE quota_usage SET used = used + amount
               WHERE resource = $resource
               AND used = $current_records.used"
        execute_sql()
        return num_affected_rows() > 0

It's important to note that the implementation above proposes to remove the
transactional container around the retrieval and update of quota usage records.
This is due to the need to have each `UPDATE` SQL statement occur within its
own transactional container. Otherwise, the semantics of the `REPEATABLE_READ`
isolation level would mean the transaction would not see any changes from other
transactions.

Assignee(s)
-----------

Primary assignees:
  AlexFrolov <afrolov@mirantis.com>
  pkholkin <pkholkin@mirantis.com>

Work Items
----------

* Add a new quota driver `nova.quota.ConcurrentDbDriver` class that we can use
  to isolate testing of this new functionality and ensure that the existing
  quota DB driver can remain the default quota driver while this work is
  completed.

* Add new DB API methods that perform the update of a single resource usage
  record that returns the number of rows affected by the UPDATE statement to
  the caller. The UPDATE statement shall construct a WHERE condition that
  includes the expected usage amount.

* Add a new DB API method that returns the set of quota usage records for
  a project, but does not call lock_mode('update').

* Change the reserve() method of the new quota DB driver to call the new DB
  API method to retrieve the usage records, loop over each usage record,
  calling the new compare-and-swap update usage amounts DB API method for
  each resource reservation. The method should implement a while loop
  that detects when the usage record was not updated and retries the update
  after reading the updated usage record information. The method should keep
  track of the records that were updated successfully. If on any retry loop
  of any resource, a quota exceeded is detected, then the successfully-updated
  usage records should be updated to undo the reservation.

* Do a similar implementation for the commit() method of the new quota DB
  driver.

* Do a similar implementation for the rollback() method of the new quota DB
  driver.

* Provide solid reference documentation in the developer reference docs about
  the concurrent quota DB driver.

Dependencies
============
None

Testing
=======
We should add a test that checks for occurrences of retry on deadlock in the
Nova logs, and verify that after this fix, we do not see any more occurrences.

Documentation Impact
====================
None

References
==========

A relevant mailing list thread about the strategy of retries:

http://lists.openstack.org/pipermail/openstack-dev/2014-November/050935.html
http://lists.openstack.org/pipermail/openstack-dev/2014-November/051300.html
