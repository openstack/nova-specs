..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Add os-xenapi library
=====================

https://blueprints.launchpad.net/nova/+spec/add-os-xenapi-library

XenAPI is currenly involved in several OpenStack projects (e.g. Nova,
Neutron, Ceilometer[1]) and may be involved in other projects in the future.
By creating a new common project to hold the common XenAPI code, it will
help to reduce the duplication between these projects; and also making
it easier to maintain, review and propose new changes to current and future
projects.

Problem description
===================

There are serveral almost identical XenAPI classes existing in different
projects.

We can refactor these classes to the common project os-xenapi. So it
will reduce the code duplication and make it easier to maintain.

Specially there is currently duplication among session management and
XAPI plugins.

Further, these XAPI plugins cannot conform to new Python standards as they
run in XenServer's dom0 where there is only Python2.4 (XenServer 6.5 and
older releases). It makes things tricky when modify plugins and also bring
trouble to add unit tests for these plugins in a way compatible with the
rest of Nova.

Use Cases
---------

This blueprint impacts Developers and Reviewers.

Developers will be able to submit xenapi related commits directly to
os-xenapi.

Nova reviewers will not have to review low level xenapi related code.

Proposed change
===============

The primary changes that needs to be done on nova are as follows:
* Copy the classes from nova/virt/xenapi/client/ to os-xenapi.
* Copy the plugins from ``plugins/xenserver/xenapi/etc/xapi.d/plugins``
  to os-xenapi.
* Add os-xenapi in requirements.txt
* Replace all ``nova.virt.xenapi.client`` imports used by the XenAPI
  driver with "os_xenapi.client".
* Improve interface between Nova and os-xenapi so dom0 plugins are
  invoked through python calls to os-xenapi so version consistency is
  provided using os-xenapi rather than an explicit API check against
  the plugins in dom0.

Alternatives
------------

Continue to duplicate session handling and XenServer plugins between
OpenStack projects.

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

os-xenapi dependency will have to be installed in order for the XenAPI
driver to be used.

Developer impact
----------------

In a typical scenario, a blueprint implementation for the Nova XenAPI
driver may require 2 parts:

* os-xenapi release, adding xenapi related utils required in order to
  implement the blueprint.
* nova commit, implementing the blueprint and using the changes made in
  os-xenapi.

If a Nova commit needs changes in os-xenapi, we must release a new version
of os-xenapi. The Nova change needs to bump Nova's requirements file so
we pull in the required changes and it must depends-on the global
requirements change that bumps the global minimal version for os-xenapi.

If we need to backport a Nova fix to a pre-os-xenapi world and this fix
depends on changes which are merged in os-xenapi, the Nova backport commit
should also cover the needed changes which are equivalent of the os-xenapi
changes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Huan Xie <huan.xie@citrix.com>

Other contributors:
  Jianghua Wang <jianghua.wang@citrix.com>
  Bob Ball <bob.ball@citrix.com>

Work Items
----------

As described in the 'Proposed change' section.

Dependencies
============

The os-xenapi library must be implemented.

Testing
=======

* os-xenapi will contain unit tests for all moved functionality
* Citrix's Xenserver CI will continue to test XenAPI changes when
  os-xenapi is in use.

Documentation Impact
====================

None

References
==========

[1] XenAPI support in Ceilometer: https://specs.openstack.org/openstack/ceilometer-specs/specs/juno/xenapi-support.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Ocata
     - Introduced
