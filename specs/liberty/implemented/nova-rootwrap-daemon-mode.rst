..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
rootwrap daemon mode
====================

https://blueprints.launchpad.net/nova/+spec/nova-rootwrap-daemon-mode

Nova is one of projects that heavily depends on executing actions on compute
and network nodes that require root priviledges on Linux system. Currently this
is achieved with oslo.rootwrap that has to be run with sudo. Both sudo and
rootwrap produce significant performance overhead. This blueprint is one of the
series of blueprints that would cover mitigating rootwrap part of the overhead
using new mode of operations for rootwrap - daemon mode. Neutron has already
adopted this approach.

Problem description
===================

As you can see in [#ne_ml]_ rootwrap presents big performance overhead for
Neutron. Impact on Nova is not as signigicant since most of the work is done
with libvirt's API but it is still there.
Details of the overhead are covered in [#rw_bp]_.

Use Cases
----------

This will eliminate bottleneck in nova-network, nova-compute at boot large of
number of nodes.

Project Priority
-----------------

None

Proposed change
===============

This blueprint proposes adopting functionality in oslo.rootwrap that would
allow to run rootwrap daemon. The daemon will work just as a usual rootwrap but
will accept commands to be run over authenticated UNIX domain socket instead of
command line and will run continuously in background.

Note that this is not usual RPC over some message queue. It uses UNIX socket,
so no remote connections are available. It also uses digest authentication with
key shared over stdout (pipe) with parent process, so no other processes will
have access to the daemon. Further details of rootwrap daemon are covered in
[#rw_bp]_.

``use_rootwrap_daemon`` configuration option should be added that will make
``utils.execute`` use daemon instead of usual rootwrap.

Alternatives
------------

Alternative approaches have been discussed for Neutron in [#ne_eth]_.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

This change requires additional endpoint to be available to run as root -
``nova-rootwrap-daemon``. It should be added to the ``sudoers`` file.

All security issues with using client+daemon instead of plain rootwrap are
covered in [#rw_bp]_.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

This change introduces performance boost for disk and network operations that
are required to be run with root priviledges in ``nova-compute`` and
``nova-network``. Current state of rootwrap daemon shows over 10x speedup
comparing to usual ``sudo rootwrap`` call. Total speedup for Nova will be less
impressive but should be noticeable.

Looking at numbers from check-tempest-dsvm-full CI job ([#nova_perf]_) with
the rootwrap daemon mode on and off, here's what we see:

Daemon Off - Average 0.08981064764 seconds
Daemon On  - Average 0.02984345922 seconds

Other deployer impact
---------------------

This change introduces new config variable ``use_rootwrap_daemon`` that
switches on new behavior. Note that by default ``use_rootwrap_daemon`` will be
turned off so to get the speedup one will have to turn it on. With it turned on
``nova-rootwrap-daemon`` is used to run commands that require root priviledges.

This change also introduces new binary ``nova-rootwrap-daemon`` that should
be deployed beside ``nova-rootwrap`` and added to ``sudoers``.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Davanum Srinivas <davanum@gmail.com>

Work Items
----------

The only work item here is to implement new config variable and run rootwrap in
daemon mode with it.

Dependencies
============

* rootwrap-daemon-mode blueprint in oslo.rootwrap [#rw_bp]_.

Testing
=======

This change doesn't change APIs so it doesn't require additional integration
tests. If tempest is happy with ``use_rootwrap_daemon`` turned on, the feature
works. We can turn this flag on for some of the jobs say the nova-network
job.

Documentation Impact
====================

None

References
==========

.. [#rw_bp] oslo.rootwrap blueprint:
   https://blueprints.launchpad.net/nova/+spec/nova-rootwrap-daemon-mode

.. [#ne_ml] Original mailing list thread:
   http://lists.openstack.org/pipermail/openstack-dev/2014-March/029017.html

.. [#ne_eth] Original problem statement summarized here:
   https://etherpad.openstack.org/p/neutron-agent-exec-performance

.. [#nova_perf] Nova check-tempest-dsvm-full comparison:
   https://docs.google.com/spreadsheets/d/1sxhan2fRg6eshY4559O8z1g8sFPRXma00xz53nZ6sAI/edit#gid=870990378
