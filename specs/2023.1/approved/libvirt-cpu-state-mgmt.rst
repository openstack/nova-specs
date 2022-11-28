..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
 CPU state management in libvirt
================================

https://blueprints.launchpad.net/nova/+spec/libvirt-cpu-state-mgmt

In many telecom or semi-static clouds, there is a bin packing problem
where a node for all practical use cases is full since no further
applications can be scheduled to the host but in reality, it still has
unused CPU cores.

In a typical server system, an idle CPU core consumes 3-5 watts of
power and produces 3-5 watts of heat which the data center cooling
solution must accommodate. To facilitate reducing power usage and heat
output in order to make data centers greener and less expensive, it makes sense
to allow the power state of CPUs to be turned off or using another governor so
that they can be optimized.

An easy possibility is to have the libvirt driver to support it by modifying
power states from the kernel sysfs interface.


Problem description
===================

For our large telco operators, they often find that they have 2-4 CPUs that are
not usable due to CPU pinning/packing requirements per host. Each CPU
consumes 3-5 watts per core or ~12-20 watts per host. Assuming a nominal
cost per kWh of $0,20 and 1000 hosts, that means they pay $35,040 in wasted
electricity a year alone from just the idle CPU usage plus the additional cost
of dissipating all of the heat generated.

Furthermore, while many telco use-cases require low latency and high
throughput, not all of them require the CPU to run at the max frequency.

Use Cases
---------

As an operator using the nova libvirt driver, I would like to be able
to disable or run slower cpu cores using the kernel sysfs interface.

As an operator, I want my nova-compute service to enable or put at max
performance a CPU core if it will be in use for a new instance that is
currently starting.


Proposed change
===============

There are two parts to this proposal :
 - add a config option for declaring that CPUs are managed
 - add a config option for telling the performance strategy to use


Declaring CPUs as managed
-------------------------

We can add a config option to the hardware section to declare that the host
CPUs are managed `[1]`_.

.. code::

  # registered in group [libvirt]
  cfg.BoolOpt('cpu_power_management',
              default=False,
              help='Use libvirt to manage CPU cores performance.')


If this option is set to True, then at nova-compute startup, all the CPUs that
are defined by the ``[compute]/cpu_dedicated_set`` option as dedicated will be
tuned for minimum performance (either offlined or set to powersave) depending
on the other CPU tuning configuration option explained below, but only if they
don't run an instance.

.. note:: Of course, shared CPUs wouldn't have their performance to be modified
          as instances float between them. If we would like to support them
          too, then *all* CPU shared cores should be modified at the same time
          and once an instance is arriving, then *all* of them would need to
          have the max performance.


Define the performance strategy per compute service
---------------------------------------------------

.. note:: for the sake of simplicity, here we loudly state that the performance
          strategy will be defined against all CPU cores from the host, and
          explicitely not be defined per CPU core.

Since different performance strategies could be taken per operator, we let them
decide which one they prefer per compute service. The current list of
performance strategies will be :

* online/offline CPU cores
* flip between ``performance`` and ``powersave`` CPU core governors

The initial implementation won't propose any other strategy (like reducing the
CPU clock) and we don't expect those other strategies to be implemented in a
foreseeable future.

.. note:: This is the operator's responsibility to verify that the OS kernel is
          recent enough to support CPU core tuning and that those CPU cores
          have their governors supporting both the ``performance`` and the
          ``powersave`` profiles.

A configuration option will accordingly be defined for choosing between those
two strategies :

.. code::

  # registered in group [libvirt]
  cfg.StrOpt('cpu_power_management_strategy',
             choices=['cpu_state', 'governor']
             default='cpu_state',
             help='Tuning strategy to reduce CPU power consumption when '
                  'unused')

Two specific config options will be defined for telling which governors to
use.

.. code::

  # registered in group [libvirt]
  cfg.StrOpt('cpu_power_governor_low',
             default='powersave',
             help='Governor to use in order to reduce CPU power consumption')

  cfg.StrOpt('cpu_power_governor_high',
             default='performance',
             help='Governor to use in order to have best CPU performance')


Instance lifecycle
------------------

When an instance is spawned (or migrated or resumed), we will use the
performance strategy to either online the core or use the best governor.
When an instance is stopped (or powered off or suspended or shelved offload or
in confirm-resize state on the source host), then we would either offline the
core or use the powersaving governor.

Note that even if we say that this is the operator responsibility to verify
whether their compute kernels support the two above strategies, we will return
an exception if when trying to either online the core or modify the governor,
so the instance could eventually be on the ERROR state.
Also, if we can't offline (or powersave) the CPU core when we stop the
instance, then we would provide a WARNING log in the compute logs.

Alternatives
------------

We could just do the first step and provide a way to disable checking the CPU
online state in the libvirt driver with no synchronization, but this would
require the operators to statically manage their cloud, which is cumbersome.

We could do this directly in nova and amend Nova everytime we want a new
usecase. Not sure we'd appreciate this.

We could make reporting CPUs to the Placement API controlable via config, but
this would only solve one usecase and would still require some tooling for
playing with the config option.


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

Upgrade impact
--------------

None, config defaults disable this feature.


Implementation
==============

Assignee(s)
-----------
Primary assignee:
  bauzas

Other contributors:
  sean-k-mooney

Feature Liaison
---------------

Feature liaison:
  N/A

Work Items
----------

* Add a config option for cpu state management `[1]`_
* Add a config option for cpu tuning
* provide a ``cpu`` framework for managing cpu core tuning thru sysfs
* modify libvirt to online/performance a CPU core when an instance is spawning
* modify libvirt to offline/powersave a CPU core when an instance is stopped
* amend init_host() to put CPU cores to low performance (or offline)


Dependencies
============

None

Testing
=======

Testing of this spec will be done with unit and functional tests.


Documentation Impact
====================

Well, usual bits.

References
==========

.. _[1]: https://review.opendev.org/c/openstack/nova/+/821228


History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
   * - Antelope
     - Reproposed
