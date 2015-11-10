..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Nested Quota Driver API
========================

https://blueprints.launchpad.net/nova/+spec/nested-quota-driver-api

Nested quota driver will enable OpenStack to enforce quota in nested
projects.

http://specs.openstack.org/openstack/keystone-specs/specs/juno/hierarchical_multitenancy.html

Problem description
===================

OpenStack is moving towards  support for hierarchical ownership of projects.
In this regard, the Keystone will change the organizational structure of
OpenStack, creating nested projects.


The existing Quota Driver in Nova called ``DbQuotaDriver`` is useful to enforce
quotas at both the project and the project-user level provided that all the
projects are at the same level (i.e. hierarchy level cannot be greater
than 1).

The proposal is extend the existing ``DbQuotaDriver`` to allow enforcing quotas
in nested projects in OpenStack. The nested projects are having a hierarchical
structure, where each project may contain users and projects (can be called
sub-projects).

Users can have different roles inside each project: A normal user can make
use of resources of a project. A project-admin, for example can be a user
who in addition is allowed to create sub-projects, assign quota on resources
to these sub-projects and assign the project admin role to individual users
of the sub-projects. Resource quotas of the root project can only be set by the
admin of the root project. The user roles can be set as inherited, and if set,
then an admin of a project is automatically an admin of all the projects in the
tree below.


Use Cases
---------

**Actors**

* Martha - Cloud Admin (i.e. role:cloud-admin) of ProductionIT
* George - Manager (i.e. role: project-admin) of Project CMS
* John - Manager (i.e. role: project-admin) of Project ATLAS
* Peter - Manager (i.e. role: project-admin) of Project Operations
* Sam - Manager (i.e. role: project-admin) of Project Services
* Paul - Manager (i.e. role: project-admin) of Project Computing
* Jim - Manager (i.e. role: project-admin) of Project Visualisation

The nested structure of the projects is as follows.

.. code:: javascript

     {
        ProductionIT: {
                       CMS  : {
                                 Computing,
                                 Visualisation
                             },
                       ATLAS: {
                                 Operations,
                                 Services
                           }
                    }
      }

Martha is an infrastructure provider and offers cloud services to George for
Project CMS, and John for Project ATLAS. CMS has two sub projects below it
named, Visualisation and Computing, managed by Jim and Paul respectively.
ATLAS has two sub projects called Services and Operations, managed by
Sam and Peter respectively.

1. Martha needs to be able to set the quotas for both CMS and ATLAS, and also
   manage quotas across the entire projects including the root project,
   ProductionIT.
2. George should be able to update the quota of Visualisation and Computing.
3. George should be able to able to view the quota of CMS, Visualisation and
   Computing.
4. George should not be able to update the quota of CMS, although he is the
   Manager of it. Only Martha can do that.
5. George should not be able to view the quota of ATLAS. Only John and Martha
   can do that.
6. Jim, the Manager of Visualisation should not be able to see the quota of
   CMS. Jim should be able to see the quota of Visualisation only, and also
   the quota of any sub projects that will be created under Visualisation.
7. The quota information regarding number of instances in different projects
   are as follows,

  +----------------+----------------+----------+--------------+
  | Name           | ``hard_limit`` | ``used`` | ``reserved`` |
  +================+================+==========+==============+
  |  ProductionIT  | 1000           |  100     | 100          |
  +----------------+----------------+----------+--------------+
  |  CMS           | 300            |  25      | 15           |
  +----------------+----------------+----------+--------------+
  |  Computing     | 100            |  50      | 50           |
  +----------------+----------------+----------+--------------+
  |  Visualisation | 150            |  25      | 25           |
  +----------------+----------------+----------+--------------+
  |  ATLAS         | 400            |  25      | 25           |
  +----------------+----------------+----------+--------------+
  |  Services      | 100            |  25      | 25           |
  +----------------+----------------+----------+--------------+
  |  Computing     | 200            |  50      | 50           |
  +----------------+----------------+----------+--------------+

  a. Suppose, Martha(admin of root project or cloud admin) increases the
     ``hard_limit`` of instances in CMS to 400
  b. Suppose, Martha increases the ``hard_limit`` of instances in CMS to 500
  c. Suppose, Martha delete the quota of CMS
  d. Suppose, Martha reduces the ``hard_limit`` of instances in CMS to 350
  e. Suppose, Martha reduces the ``hard_limit``  of instances in CMS to 200
  f. Suppose, George(Manager of CMS)increases the ``hard_limit`` of
     instances in CMS to 400
  g. Suppose, George tries to view the quota of ATLAS
  h. Suppose, Jim tries to reduce the ``hard_limit`` of instances in CMS to
     400.
  i. Suppose, Martha tries to increase the ``hard_limit`` of instances in
     ProductionIT to 2000.
  j. Suppose, Martha deletes the quota of Visualisation.
  k. Suppose, Martha deletes the project Visualisation.

8. Suppose the company doesn't want a nested structure and want to
   restructure in such a way that there are only four projects namely,
   Visualisation, Computing, Services and Operations.


Project Priority
-----------------

The code in the existing DBQuotaDriver is deprecated and hence we need an
update. Also as the entire OpenStack community is moving toward hierarchical
projects this can be an useful addition to Nova.

Proposed change
===============

1. The default quota (hard limit) for any new subproject is set to 0.
   The neutral value of zero ensures consistency of data in the case of race
   conditions when several projects are created by admins  at the same time.
   Suppose the default value of RAM is 1024, and A is the root project. And an
   admin is creating B, a child project of A, and another admin is creating C,
   again a child project of A. Now, the sum of default values for RAM of B and
   C are crossing the default value of A. To avoid this type of situations,
   default quota is set as Zero.

2. A project is allowed to create a instance, only after setting the quota to a
   non-zero value (as default value is 0). After the creation of a new project,
   quota values must be set explicitly by a Nova API call to a value which
   ensures availability of free quota, before resources can be claimed in the
   project.

3. A user with role "admin" in the root project is permitted to do quota
   operations across the entire hierarchy, including the top level project.
   Admins in the root project are the only users who are allowed to set the
   quota of the root project in a tree.

4. A person with role "admin" in a project is permitted to do quota operations
   on its immediate subprojects and users in the hierarchy. If the role "admin"
   in a project is set as inheritable in Keystone, then the user with this role
   is permitted to do quota operations starting from its immediate child
   projects to the last level project/user under the project hierarchy.

5. The total resources consumed by a project is divided into

     a) Used Quota  - Resources used by the instances in a project.
                      (excluding child-projects)
     b) Reserved Quota - Resources reserved for future use by the project
     c) Allocated Quota - Sum of the quota ``hard_limit`` values of immediate
                          child projects

6. The ``free`` quota available within a project is calculated as
         ``free quota = hard_limit - (used + reserved + allocated)``

   Free quota is not stored in the database; it is calculated for each
   project on the fly.

7. An increase in the quota value of a project is allowed only if its parent
   has sufficient free quota available. If there is free quota available with
   the parent, then the quota update operation will result in the update of
   the ``hard_limit`` value of the project and ``allocated`` value update of
   its parent project. That's why, it should be noted that updating the quota
   of a project requires the token to be scoped at the parent level.

   * Hierarchy of Projects is as A->B->C (A is the root project)

     +------+----------------+----------+--------------+---------------+
     | Name | ``hard_limit`` | ``used`` | ``reserved`` | ``allocated`` |
     +======+================+==========+==============+===============+
     |  A   | 100            |  0       | 50           |   50          |
     +------+----------------+----------+--------------+---------------+
     |  B   | 50             | 20       |  0           |   10          |
     +------+----------------+----------+--------------+---------------+
     |  C   | 10             | 10       |  0           |    0          |
     +------+----------------+----------+--------------+---------------+

     Free quota for projects would be:

     A:Free Quota = 100 {A:hard_limit} - ( 0 {A:used} + 0 {A:reserved} +
                         50 {A:Allocated to B})

     A:Free Quota = 50

     B:Free Quota = 50  {B:hard_limit} - ( 20 {B:used} + 0 {B:reserved} +
                         10 {B:Allocated to C})

     B:Free Quota = 20

     C:Free Quota = 10  {C:hard_limit} - ( 10 {C:used} + 0 {C:reserved} +
                         0 {C:Allocated})

     C:Free Quota = 0

     If Project C ``hard_limit`` is increased by 10, then this change results
     in:

     +------------+----------------+----------+--------------+---------------+
     | Name       | ``hard_limit`` | ``used`` | ``reserved`` | ``allocated`` |
     +============+================+==========+==============+===============+
     |  A         | 100            |  0       | 50           |   50          |
     +------------+----------------+----------+--------------+---------------+
     |  B         | 50             | 20       |  0           |   20          |
     +------------+----------------+----------+--------------+---------------+
     |  C         | 10             | 10       |  0           |    0          |
     +------------+----------------+----------+--------------+---------------+

     If Project C hard_limit needs to be increased further by 20, then this
     operation will be aborted, because the free quota available with its
     parent i.e. Project B is only 10. So, first project-admin of A should
     increase the ``hard_limit`` of Project B (using scoped token to
     Project A, because of action at level A) and then increase the
     ``hard_limit`` of Project C (again scoped token to Project B)

     Please consider the use cases mentioned above. The quota information
     of various projects, including the allocated quota is as follows,

     | ProductionIT  : hard_limit=1000, used=100, reserved=100, allocated=700
     | CMS           : hard_limit=300, used=25, reserved=15, allocated=250
     | Computing     : hard_limit=100, used=50, reserved=50, allocated=0
     | Visualisation : hard_limit=150, used=25, reserved=25, allocated=0
     | ATLAS         : hard_limit=400, used=25, reserved=25, allocated=300
     | Services      : hard_limit=100, used=25, reserved=25, allocated=0
     | Computing     : hard_limit=200, used=50, reserved=50, allocated=0

     * Suppose Martha tries to increase the instances quota in CMS to 400.
       Since Martha is having the role of admin in ProductionIT which is the
       parent of CMS, she can increase the quota of CMS provided that the
       token is scoped to ProductionIT. This is required because the increase
       of quota limit in CMS results in the corresponding reduction of
       free quota in ProductionIT.

       Using the above formula, free quota of ProductionIT is given by,

       | ProductionIT:hard_limit minus
       | ProductionIT:used minus
       | ProductionIT:reserved minus
       | ProductionIT:allocated =
       | 1000 - 100 - 100 - (300 + 400) = 100.

       So maximum permissible quota for CMS is 300 + 100 = 400

       Note:ProductionIT:allocated = CMS:hard_limit + ATLAS:hard_limit

       Minimum quota of CMS is given by,
       CMS:used + CMS:reserved + CMS:allocated = 25 + 15 + 250 = 290

       Note: CMS:allocated = Visualisation:hard_limit + Computing:hard_limit

       Since 290 <= 400 <=400, quota operation will be successful.
       After update, the quota of ProductionIT and CMS will be as follows,

       | ProductionIT : hard_limit=1000, used=100, reserved=100, allocated=800
       | CMS          : hard_limit=400, used=25, reserved=15, allocated=250

     * Suppose Martha tries to increase the instances quota in CMS to 500. Then
       it will not be successful, since the maximum quota available
       for CMS is 400.

     * Suppose George who is the Manager of CMS increases the instances
       quota in CMS to 400, then it will not be successful, since George is not
       having admin or project-admin role in ProductionIT which is the parent
       of CMS.

     * Suppose Martha tries to increase the quota of ProductionIT to 2000,
       then it will be successful. Since ProductionIT is the root project,
       there is no limit for the maximum quota of ProductionIT. And also,
       Martha is having admin role in ProductionIT.

8. A decrease in the quota value of a project is allowed only if it has free
   quota available, free quota > 0 (zero), hence the maximum decrease in
   quota value is limited to free quota value.

 * Hierarchy of Projects is A->B->C, where A is the root project
      Project A (hard_limit = 100, used = 0, reserved = 0, allocated = 50)
      Project B (hard_limit = 50, used = 20, reserved = 0, allocated = 10)
      Project C (hard_limit = 10, used = 10, reserved = 0, allocated = 0)

      If Project B hard_limit is reduced by 10, then this change results in
      Project A (hard_limit = 100, used = 0, reserved = 0, allocated = 40)
      Project B (hard_limit = 40, used = 20, reserved = 0, allocated = 10)
      Project C (hard_limit = 10, used = 10, reserved = 0, allocated = 0)

      If Project B's hard_limit needs to be reduced further by 20, then this
      operation will be aborted, because the free quota of Project B should
      be greater than or equal to (20+0+10).

    * Suppose Martha tries to reduce the instances quota in CMS to 350,
      it will be successful since the minimum quota required for CMS is 290.

    * Suppose Martha tries to reduce the instances quota of CMS to 200,
      then it will not be successful, since it violates the minimum quota
      criteria.

9. Delete quota is equivalent to updating the quota with zero values. It
   will be successful if the allocated quota is zero. Authentication logic
   is same as that of update logic.

  * Suppose Martha tries to  delete the quota of CMS then it will not be
    successful, since allocated quota of CMS is non-zero.

  * Suppose Martha deletes the quota of Visualisation, then it will be
    successful since the allocated quota of Visualisation is zero. The
    deleted quota of Visualisation will add to the free_quota of CMS. The
    quota of CMS will be CMS :hard_limit=300, used=25, reserved=15,
    allocated=100.

  * Suppose, Martha deletes the project Visualisation, the quota of
    Visualisation should be released to its parent, CMS. But in the current
    setup, Nova will not come to know, when a project is deleted from keystone.
    This is because, Keystone service is not synchronized with other services,
    including nova. So even if the project is deleted from keystone, the quota
    information remains there in nova database. This problem is there in
    the current running model of OpenStack. Once the keystone service is
    synchronized, this will be automatically taken care of. For the time
    being, Martha has to delete the quota of Visualisation, before she is
    deleting that project. Synchronization of keystone with other OpenStack
    services is beyond the scope of this blueprint.

10. Suppose if George, who is the Manager of CMS tries to view the quota of
    ATLAS, it will not be successful, since George is not having any role in
    ATLAS or in the parent of ATLAS.

11. Suppose Jim who is the Manager of Visualisation tries to update the
    quota of CMS, it will not be successful, because he is not having admin or
    project-admin role in the parent of CMS.

12. Suppose if the organization doesn't want a nested structure and wants
    only four projects namely, Visualisation, Computing, Services and
    Operations, then the setup will work like the current setup where there is
    only one level of projects. All the four projects will be treated as root
    projects.

13. A "admin" user in a parent project, will be able to set quotas for users
    beyond the hierarchy.


Alternatives
------------

For quota update and delete operations of a project, the token can be scoped to
the project itself, instead to its parent. But, we are avoiding that, because
the quota change in the child project lead to change in the free quota of the
parent. Because of that, according to this bp, for quota update and delete
operations, the token is scoped to the parent.


Data model impact
-----------------

Create a new column ``allocated`` in table ``quotas`` with default value 0.


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
  * sajeesh

Other contributors:
  * ericksonsantos
  * raildo
  * schwicke
  * vilobhm

Work Items
----------

1. Extend the existing ``DbQuotaDriver``, to enforce quotas in hierarchical
   multitenancy in OpenStack.

2. A migration script will be added to create the new column ``allocated`` in
   table ``quotas``, with default value 0.

3. Update the default quota value for subprojects to zero.

4. Implements Keystone calls to get the parent_id and subtree information.

5. Update the API v2.1 related to Quota operations to handle with a target
   project( On this case, a subproject)

6. Update the quota calculation to handle with the allocated quota.


Dependencies
============

Depends on bp Hierarchical Multitenancy
  * `<http://specs.openstack.org/openstack/keystone-specs/specs/juno/hierarchical_multitenancy.html>`_


Testing
=======

* Unit tests will be added for all the REST APIs calls.

* Add unit tests for integration with other services.

* Add functional tests in tempest for the new API calls.


Documentation Impact
====================

* Update the API docs to explain how the user can update quota for a
  subproject.

References
==========

* `Wiki <https://wiki.openstack.org/wiki/HierarchicalMultitenancy>`_

* `Heirarchical Projects
  <http://specs.openstack.org/openstack/keystone-specs/specs/juno/hierarchical_multitenancy.html>`_

* `Hierarchical Projects Improvements
  <https://blueprints.launchpad.net/keystone/+spec/hierarchical-multitenancy-improvements>`_

* `Cinder nested quota driver
  <http://specs.openstack.org/openstack/cinder-specs/specs/liberty/cinder-nested-quota-driver.html>`_
