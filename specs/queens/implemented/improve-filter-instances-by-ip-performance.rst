..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Improve filter instances by IP performance
==========================================

https://blueprints.launchpad.net/nova/+spec/improve-filter-instances-by-ip-performance

The aim of this feature is to improve the performance when
filter instances by IP address.

Problem description
===================

Nova allows filtering instances by IP address when list instances.
But the performance of such fitering is poor, this is due to that
IP address is one part of the instance.network_info JSON, we have
to iterate one by one to find the instance that matches the request.
Which makes this filter un-usable in large scale deployment.

Use Cases
---------

As an operator, I want to efficiently filter instances by IP so that
I can locate the instances that have abnormal network activities on
the provided IP address(es).

Proposed change
===============

As discussed in Queens PTG [1]_, one possible solution is to
get filtered ports according to the provided IP addresses
from Neutron and retrieve the instance uuid from the
port.device_id and then merge to the other filters.

Nova currently support filtering instances by IP address
using regex matching manner. But the Neutron port list API does
not support regex matching filtering. A RFE has been submitted
in Neutron [2]_ to support this. The changes in Nova side will
depend on the enhancement in Neutron side.

As a newer version of Nova may talk to older version of Neutron,
we will also add logic that check whether regex matching is
supported in Neutron side via a new networking API extension.
If the extension is not available, we will fallback to the existing
behavior and avoid erroneously filter out all instances.

Nova currently also support list and filter deleted instances
by IP address, after this change, user will not able to filter
deleted instances with IP address since Neutron cannot provide
such data. This is considered to be acceptable as there are no
guarantees that users can list deleted instances today since an
operator can archive/purge deleted instances at any point.

Alternatives
------------

An alternative raised up at Queens PTG was storing the IPs in
a mapping table in Nova database for query. The issue with this
is that we already store the IPs in the instance_info_caces.network_info
column and we have to work on keeping that accurate, storing the data
yet in another place could lead to more bugs as we have to manage state
in 3 different locations, Neutron(the source of truth), instance info
cache and the new mapping table.

Data model impact
-----------------

None

REST API impact
---------------

Users will not able to list deleted instances with IP filter after
this change.

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

This change will improve the performance when filtering instances
by IP addresses.

Benchmarking and comparision test at scale (at least 1000 instances)
will be performed with the POC and test result will be provided.

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
  Kevin Zheng <zhengzhenyu@huawei.com>

Work Items
----------

* Add logic to query filtered ports from Neutron
* Merge the results with other filters
* Add related doc and reno

Dependencies
============

As Nova provides regex matching manner filtering for IP filter,
so this is depend on Neutron changes that adds regex matching
manner to the GET /ports API [2]_.

Testing
=======

Add the following tests.

* Unit tests


Documentation Impact
====================

None

References
==========

.. [1] Queens PTG discussion recap:
    http://lists.openstack.org/pipermail/openstack-dev/2017-September/122258.html

.. [2] Neutron RFE to support regex matching when filter ports by IP address:
    https://bugs.launchpad.net/neutron/+bug/1718605

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Proposed
