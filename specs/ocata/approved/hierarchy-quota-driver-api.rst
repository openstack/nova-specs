..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Hierarchy Quota Driver API
==========================

TODO: https://blueprints.launchpad.net/nova/+spec/example

Hierarchy quota driver will enable OpenStack to enforce quota according
projects hierarchy.

Problem description
===================

OpenStack supports hierarchical ownership of projects. This enables the
management of projects and quotas in a way that is more comfortable for
private clouds, because in a private cloud, you can organize better your
departmental divisions they work as “subprojects”.

The existing Quota Driver in Nova called ``DbQuotaDriver`` doesn't support
enforcement of quotas for hierarchical project structure. It means that
current Quota Driver doesn't check a quotas for the nested projects in
Openstack.

For the nested projects limits enforcement should be done such way that not
only project usage can't exceed project limit but the sum of project usage and
subprojects usages can't exceed project limit.

For the nested projects Quota Driver should have ability to enforce quotas
with overbooking. An overbooking term in this context means that sum of
subnodes limit values can be greater than parent limit value.

This scheme allows eating more for more active projects still having an upper
limit in the parent project. Such logic requires all project tree traversal
and need to be profiled carefully.


Use Cases
---------

1. Scenario #1 (nested quotas without overbooking):
   There is a projects tree. Prj_0_a has to subprojects: Prj_1_a and Prj_1_b.

   Prj_0_a quota=10.
   Prj_1_a quota=3. Prj_1_a quota < Prj_0_a quota.
   Prj_1_b quota=4. Prj_1_a quota < Prj_0_a quota.

   Sum(Prj_1_a quota, Prj_1_b quota)=7 < Prj_0_a quota.

   +--------------------------------+
   |                                |
   |          +--------+            |
   |          | Domain |            |
   |          +--------+            |
   |              /\                |
   |             /  \               |
   |            /    \              |
   |           /      \             |
   |          /        \            |
   |    +---------+  +---------+    |
   |    | Prj_0_a |  | Prj_0_b |    |
   |    +---------+  +---------+    |
   |    |quota=10 |  |quota=10 |    |
   |    +---------+  +---------+    |
   |          /\                    |
   |         /  \                   |
   |        /    \                  |
   |       /      \                 |
   |      /        \                |
   | +---------+  +---------+       |
   | | Prj_1_a |  | Prj_1_b |       |
   | +---------+  +---------+       |
   | |quota=3  |  |quota=4  |       |
   | +---------+  +---------+       |
   |                                |
   +--------------------------------+

   a. Try to allocate 4 items of resources for project "Prj_1_a" - get an
      error due to the project limits.
   b. Try to allocate 3 items of resources for project "Prj_1_a" - success.
      Prj_1_a usage=3.
   c. Try to allocate one more item for "Prj_1_a" - get an error due to
      the project limits.
   d. Try to allocate 4 items for project "Prj_1_b" - success.
      Prj_1_b usage=4.
   e. Try to allocate one more item for project "Prj_1_b" - get an error due
      to the project limits.

2. Scenario #2 (nested quotas with overbooking).
   There is a projects tree. Prj_0_a has to subprojects: Prj_1_a and Prj_1_b.

   Prj_0_a quota=10.
   Prj_1_a quota=7. Prj_1_a quota < Prj_0_a quota.
   Prj_1_b quota=10. Prj_1_a quota = Prj_0_a quota.

   Sum(Prj_1_a quota, Prj_1_b quota)=17 > Prj_0_a quota.

   +--------------------------------+
   |                                |
   |          +--------+            |
   |          | Domain |            |
   |          +--------+            |
   |              /\                |
   |             /  \               |
   |            /    \              |
   |           /      \             |
   |          /        \            |
   |    +---------+  +---------+    |
   |    | Prj_0_a |  | Prj_0_b |    |
   |    +---------+  +---------+    |
   |    |quota=10 |  |quota=10 |    |
   |    +---------+  +---------+    |
   |          /\                    |
   |         /  \                   |
   |        /    \                  |
   |       /      \                 |
   |      /        \                |
   | +---------+  +---------+       |
   | | Prj_1_a |  | Prj_1_b |       |
   | +---------+  +---------+       |
   | |quota=7  |  |quota=10 |       |
   | +---------+  +---------+       |
   |                                |
   +--------------------------------+

   2.1

   a. Try to allocate 8 items of resources for project "Prj_1_a" - get an
      error due to the project limits.
   b. Try to allocate 7 items of resources for project "Prj_1_a" - success.
      Prj_1_a usage=7. Prj_0_a usage=7.
   c. Try to allocate one more item for "Prj_1_a" - get an error due to the
      project limits.
   d. Try to allocate 3 items for "Prj_1_b" - success. Prj_1_b usage=3.
      Prj_0_a usage=10.
   e. Try to allocate one more item for project "Prj_1_b" - get an error due
      to the parent project limits.

   2.2

   a. Try to allocate 5 items for project "Prj_0_a" - success.
      Prj_0_a usage=5.
   b. Try to allocate 5 items for project "Prj_1_a" - success.
      Prj_1_a usage=5. Prj_0_a usage=10.
   c. Try to allocate one more item for project "Prj_1_a" - get an error due
      to the parent project limits.

Project Priority
----------------

None


Proposed change
===============

1. The main idea is to implement nested quotas without overbooking and
   with overbooking in one Quota Driver.
2. The default quota (hard limit) for any newly created project is set to 0.
3. Each time when trying to allocate resources for project should be done check
   of usages/limits.
4. The limits enforcement should be done such way that not only project usage
   can't exceed project limit but the sum of project usage and subprojects usages
   can't exceed project limit.
   Sum of subprojects limits shouls be <= project limit.
5. In the overbooking mode sum of subprojects limits can be not equal to parent
   project limit. Sum of subprojects limits can be greater then project limit. However,
   sum of usages in subprojects can not ever exceed the quota limits for project.

Alternatives
------------


Data model impact
-----------------


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
  * avolkov


Work Items
----------

1. Implement a new class called ``QuotaNode`` to represent a node of the quotas tree.
   An instance of ``QuotaNode`` class will have following attributes:
   * name - project name
   * limits - a dict {project_id: {recourse: limit}, ...}}
   * usages - a dict {project_id: {recourse: usage}, ...}}
   * children - a list of child nodes
   * parent - parent node

2. Implement a new Quota Driver called ``HierarchyQuotaDriver`` by
   extending the existing ``DbQuotaDriver``, to enforce quotas in hierarchical
   multitenancy in OpenStack.

3. A new driver ``HierarchyQuotaDriver`` will build a tree of instances
   ``QuotaNode`` to check limits and usages of resource for project.

4. The check will be done by ``check`` method in the ``QuotaNode`` class.
   It will work for non-overbooking and overbooking case because of flag.
5. If ``OVERBOOKING_ALLOWED`` flag is set to False:
   Sum of subprojects usages + project usage  shouls be <= project limit.
6. If ``OVERBOOKING_ALLOWED`` flag is set to True in addition to previous
   condition should be called a check for the parent project.
7. Cache (TODO)
8. Config (TODO)


Dependencies
============

Depends on bp Hierarchical Multitenancy
  * `<http://specs.openstack.org/openstack/keystone-specs/specs/juno/hierarchical_multitenancy.html>`_


Testing
=======

* Unit tests will be added for all the REST APIs calls.

* Add unit tests for integration with other services.


Documentation Impact
====================

None


References
==========

* `Wiki <https://wiki.openstack.org/wiki/HierarchicalMultitenancy>`_

* `Heirarchical Projects
  <http://specs.openstack.org/openstack/keystone-specs/specs/juno/hierarchical_multitenancy.html>`_

* `Hierarchical Projects Improvements
  <https://blueprints.launchpad.net/keystone/+spec/hierarchical-multitenancy-improvements>`_


