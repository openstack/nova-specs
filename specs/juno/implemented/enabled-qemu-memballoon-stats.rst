..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Enabled qemu memory balloon stats when boot instance
=====================================================

https://blueprints.launchpad.net/nova/+spec/enabled-qemu-memballoon-stats

We can get vm memory stats from libvirt API 'virDomainMemoryStats', it help
telemetry module like as: Ceilometer to collect vm memory usage, but by
default the memory statistical feature is disable in qemu, we need to add
stats period in order to enabled memory statistical.

Problem description
===================

By default, the memory statistical feature is disable in qemu, we need to
add stats period in order to enabled memory statistical, like this::

    <memballoon model='virtio'>
      <stats period='10'/>
    </memballoon>

Add memballoon device stat period in libvirt.xml when boot instance.

Actual memory statistical works on libvirt 1.1.1+ and qemu 1.5+, and need a
guest driver that supports the feature, but booting instance with memory stats
period does not lead to be failure on libvirt 0.9.6+ and qemu 1.0+.

Refer to [1] for libvirt API 'virDomainMemoryStats' details.

Refer to [2] for memballoon details in libvirt.xml.

Details of enabled memory stats: [3]


Proposed change
===============

* Add the option 'mem_stats_period_seconds' into nova.conf(libvirt section).
* Enable stats period of memballoon device, if user boot instance when
  mem_stats_period_seconds > 0. mem_stats_period_seconds is number of seconds
  to memory usage statistics period. By default mem_stats_period_seconds=10.


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

User need to prepare suitable balloon driver in image, particularly for windows
guests, most modern Linuxes have it built in. Booting instance will be
successful without image balloon driver, just can't get guest memory stat from
'virDomainMemoryStats' API.

Performance Impact
------------------

None

Other deployer impact
---------------------

Add a new option 'mem_stats_period_seconds' in nova.conf libvirt section.
By default mem_stats_period_seconds=10, the stats feature is enable,
mem_stats_period_seconds is number of seconds to memory usage statistics
period. If mem_stats_period_seconds <= 0, the feature is disable.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <kiwik-chenrui>

Work Items
----------

* Add a LibvirtConfigMemoryBalloon class inherit from LibvirtConfigGuestDevice.
* Changes to be made to the libvirt driver get_guest_config method to check
  the option 'mem_stats_period_seconds' in nova.conf, during the boot of the
  instance.
* If mem_stats_period_seconds>0, set stats period of memory balloon device in
  the instance.


Dependencies
============

* libvirt 1.1.1+
* qemu 1.5+
* guest driver that supports memory balloon stats


Testing
=======

Unit tests and tempest tests will verify this function. Compatibility will be
verified, boot instance with 'mem_stats_period_seconds' on current devstack
environment(libvirt0.9.8 and qemu1.0.0).

Memory stats don't work in current gate environment, see details in
Dependencies section. Full test need to ensure the devstack VM gate has updated
libvirt, qemu versions and guest driver compatibility.


Documentation Impact
====================

1. By default this feature is enabled, 'mem_stats_period_seconds'=10. If you
   want to change the stat period, please modify nova.conf.

2. mem_stats_period_seconds is number of seconds to memory usage statistics
   period.

3. If you set mem_stats_period_seconds<=0, the memory stats will be disabled,
   by default mem_stats_period_seconds=10.

This blueprint just add stats period into memory balloon device, it is not
sufficient to guarantee this feature will work because you need to meet the
requirements in dependencies section, and you need to handle the case where
the API 'virDomainMemoryStats' call returns no data(not in scope of this bp).


References
==========

* [1] http://libvirt.org/html/libvirt-libvirt.html#virDomainMemoryStats
* [2] http://libvirt.org/formatdomain.html#elementsMemBalloon
* [3] http://paste.openstack.org/show/78624/
