..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Libvirt driver class refactoring
================================

https://blueprints.launchpad.net/nova/+spec/libvirt-driver-class-refactor

The libvirt driver.py class is growing ever larger and more complicated.
There are circular dependencies between this class and other libvirt
classes. This work aims to split some of the functionality out into
new classes

Problem description
===================

The libvirt driver.py class is growing ever larger over time. This is
increasing the complexity of the code and also resulting in larger
test suites.

The driver.py class is serving what are really a number of distinct
use cases. Primarily it is the interface for the compute manager
class to consume. It also, however, has alot of helper APIs for
dealing with the libvirt connection and the host operating system,
as well as helpers for dealing with guest instance configuration.
A number of these helpers are required by other libvirt modules
such as the vif, volume and image backend drivers. This has resulted
in circular dependancies between the driver.py and the other libvirt
modules. For example, LibvirtDriver uses NWFilterFirewall, but also
has to pass a 'get_connection' callback so that NWFilterFirewall can
obtain the libvirt connection from the LibvirtDriver class. There are
a number of other similar deps.

Proposed change
===============

The intention is to introduce two new modules to the codebase

* host.py - this will encapsulate access to libvirt and the host
  operating system state. It will contain a 'Host' class, which
  manages a single libvirt connection. It will contain the methods
  for connecting to libvirt, getting lists of domains, querying
  host performance metrics and so on (see the work-items section
  for specifics). This is not to be confused with the existing
  HostState class which is just a trivial helper for the driver
  'host_state' method.

* guest.py - this will encapsulate interaction with libvirt guest
  domain instances. It will contain a 'Guest' class, which manages
  a single libvirt guest domain. It will contain all methods used
  to construct the guest XML configuration during instance startup
  that currently live in driver.py

The code for host.py and guest.py will be pulled out of the
existing driver.py class. Other libvirt modules will be updated
as needed to access the new APIs. To minimize the risk of creating
regressions changes to the methods being moved will be minimized,
to just minor renames & fixups where appropriate.

The intended end result is that none of the modules in the libvirt
driver directory should need to access the driver.py file. They
should be able to consume the host.py and guest.py APIs instead,
thus breaking the circular dependancies. For example the
NWFilterFirewall class can be given an instance of the Host class
instead of a callback to LibvirtDriver.

The new structure should also reduce the size of the test_driver.py
file and make it possible to create simpler, self contained tests
for the functionality that's in host.py and guest.py, since it will
be isolated from the overall virt driver API.

It is not anticipated that any configuration parameters will move.
The high level desire is that the new APIs will not directly use
any Nova configuration parameters. Instead the LibvirtDriver would
be responsible for reading the config parameters and then setting
attributes on the new class or passing method parameters where
appropriate.

At the end of the work there should be absolutely no functional
change on the libvirt driver. This is intended to be purely
refactoring work that is invisible to anyone except the people
writing libvirt driver code.

Alternatives
------------

Doing nothing is always an option, but it isn't very appealing
because it leaves us with an ever growing monster ready to
devour us at any moment.

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

There are liable to be conflicts with any developers who have patches
touching driver.py or test_driver.py

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  berrange

Work Items
----------

* Create a host.py module and move the basic connection handling code
  out of driver.py into the new Host class. This will cover the following
  methods:

  * _conn_has_min_version
  * _has_min_version
  * _native_thread
  * _dispatch_thread
  * _event_lifecycle_callback
  * _queue_Event
  * _dispatch_events
  * _init_events_pipe
  * _init_events
  * _get_new_connection
  * _close_callback
  * _test_connection
  * _connect

* Move helpers used by HostState out into the Host class. This will
  cover the following methods

  * _get_vcpu_total
  * _get_memory_mb_total
  * _get_vcpu_used
  * _get_memory_mb_used
  * _get_hypervisor_type
  * _get_hypervisor_version
  * _get_hypervisor_hostname
  * _get_cpu_info
  * _get_disk_available_least

* Create a guest.py module and move the code for creating the guest XML
  configuration out of driver.py into the new Guest class. This will cover
  the following methods

  * _get_guest_cpu_model_config
  * _get_guest_cpu_config
  * _get_guest_disk_config
  * _get_guest_storage_config
  * _get_guest_config_sysinfo
  * _get_guest_pci_device
  * _get_guest_config
  * _get_guest_xml

* Move the code for listing domains into the new Host class. This
  will cover the '_list_instance_domains' method.

* Change NWFilterFirewall and LibvirtBaseVIFDriver so that they
  accept a 'Host' object instance, instead of requiring a callback
  to the LibvirtDriver class.

* Anything else that appears relevant to move :-)

Dependencies
============

* None

Testing
=======

Since it is intended that there is no functional change in this work,
the existing test coverage should be sufficient. The existing unit
tests will need some refactoring as code is moved, and some more unit
tests will be written where appropriate.

Documentation Impact
====================

None

References
==========

None
