..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Interactive web-based serial consoles
======================================

https://blueprints.launchpad.net/nova/+spec/serial-ports

This blueprint is about exposing interactive web-based serial consoles to
openstack VMs through a websocket proxy. It is mainly raised because of the
problems openstack is facing with the serial console logs that are hard to
maintain, grow indefinitely, etc. The point is not to eliminate the serial
console logs, but to give the users another option besides logging to a file
and to expose an interactive serial console.

Problem description
===================

Right now the serial console has unsolved issues with the logging that have
bounced from one release to another and no suitable solution was developed for
them. Most of the issues are nicely summed up in the serial console log
blueprint for juno https://review.openstack.org/#/c/80865/ however, this
proposal doesn't deal with exposing an interactive serial console to the end
user.

Proposed change
===============

This blueprint proposes the addition of a new service - serialproxy (a
websocket proxy) that would handle websocket connections to the serial
consoles. The websocket proxy can be deployed on a machine other from the
hypervisor, so unix domain sockets wouldn't do the trick. The best way to
expose them would be by opening a TCP socket for every serial console.
http://libvirt.org/formatdomain.html#elementsCharTCP
This service would act similarly to the novncproxy and scale in more or less
the same way.

One serial port can be accessed only by one user at a time, i.e. it can't
be muxed since none of the hypervisors have a 'clear this line' command
separate from the 'connect' command (or a flag to integrate that with the
original 'connect' call).
The proposed scenario for multiple users accessing the same serial port is the
following:
If a user is already connected, then reject the attempt of a second user to
access the console, but have an API to forceably disconnect an existing
session. This would be particularly important to cope with hung sessions where
the client network went away before the console was cleanly closed.

To allow multiple clients to connect to serial ports we'd need to create the
ports when the instance is booted, but we'd need to know the number of ports
that would need to be created in advance. That number can be passed through a
property in the image metadata, e.g. "serial_ports".
Since the serial ports are exposed through TCP sockets we would also need a
module that tests for free TCP ports and allocates them so that the libvirt
driver can use them when creating the serial ports. This should be persistent,
so that the ports that are already tested won't be tested again for a new
serial port.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The REST API would have one additional method to obtain the serial console URL
for the end user or for displaying in the dashboard.

V2 API specification:
POST: v2/{tenant_id}/servers/{server_id}/get-serial-console

V3 API specification:
POST: v3/servers/{server_id}/get-serial-console

Request parameters:

* tenant_id: The ID for the tenant or account in a multi-tenancy cloud.
* server_id: The UUID for the server to get the serial console for.

JSON response
::

    {
        "serial_console":
        {
            "url": "http://example.com:6083/serial.html?token=b40ac1c3-b640-4a6a-ae34-bf347ef089d6"
        }
    }

JSON schema definition
::

    serial_console = {
        'type': 'object',
        'properties': {
            'serial_console': {
                'type': ['object', 'null'],
                'properties': {},
                'additionalProperties': False,
            },
        },
        'additionalProperties': False,
    }


HTTP response codes:
v2:

* Normal HTTP Response Code: 200 on success

v3:

* Normal HTTP Response Code: 202 on success

Security impact
---------------

The opening of TCP ports in the hypervisor node can enable anyone to gain
access to any of the serial consoles by scanning for open ports if the ports
specified in port_range config param are visible to the public.
Usually the hypervisor ports aren't externally exposed, so this wouldn't be any
better or worse than VNC.
The insecurity of VNC is being tackled by a blueprint that will add strong auth
to VNC on the internal network. That's not a reason to block this serial
console feature though. We can work with the QEMU community at a later date to
get SSL support for the character device sockets it exposes.

Notifications impact
--------------------

None

Other end user impact
---------------------

The python-novaclient will have to implement a new command.

Command:
get-serial-console <server> <console-type>

* param server: The name or Id of the server.


Performance Impact
------------------

Using the serial consoles instead of a graphical console would be more optimal
since it interacts with the instance through a text stream.

Other deployer impact
---------------------

Config options that are being added in the serial_console group:
[serial_console]
- enabled (type=BoolOpt, default=False)
- base_url (type=StrOpt, default='http://127.0.0.1:6083/serial.html')
- listen (type=StrOpt, default='0.0.0.0')
- proxyclient_address (type=StrOpt, default='127.0.0.1')
- port_range (type=StrOpt, default='10000:20000')
- record (type=BoolOpt, default=False)
- daemon (type=BoolOpt, default=False)
- ssl_only (type=BoolOpt, default=False)
- source_is_ipv6 (type=BoolOpt, default=False)
- cert (type=StrOpt, default='self.pem')
- key (type=StrOpt)
- web (type=StrOpt, default='/usr/share/serialproxy-static')

The default value of the "enabled" confing param is False so there's no need
to take something into account after this change gets merged.

A new service - serialproxy is introduced which will need to be deployed
separately in order for this feature to work with websockets.
The command line params would be no different from novnc's which would override
some of the config params specified in the config file).

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Vladan Popovic

Other contributors:
  Ian Wells
  Sushma Korati

Work Items
----------

**Websocket proxy**

* Add a config param in nova that would enable the web-based serial console,
  e.g. enabled=True|False where False would be the default.
* Configure libvirt to open TCP channels on the ports
  http://libvirt.org/formatdomain.html#elementsCharTCP
* Add a port allocator module that would generate/test TCP ports and assign
  them to the instance's libvirt config when it finds a free one.
  This would require another config param in nova, e.g. port_range=10000:20000
* Implement the serial console config generation and retreival in the libvirt
  driver.
* Add a method for obtaining the serial console in the compute manager.
* Add methods in the consoleauth that would authorize the tokens.
* Add API calls that would obtain the serial console URL with the generated
  consoleauth token.
* Add a serialproxy service that will serve as a wesocket proxy for serial
  consoles
* Add static files that will be serverd from the proxy, including a terminal
  emulator, probably https://github.com/chjj/term.js/


Dependencies
============

May require packaging of the static files for the websocket proxy and the
terminal emulator.

Testing
=======

Unit tests should be sufficient to cover libvirt and the API part.


Documentation Impact
====================

Since tihs proposal introduces a new console and service the following things
should be documented at least:

* Deploying the serialproxy (with SSL/TLS support if possible)
* Changes in the image metadata (if that solution fits the needs for multiuser
  serial consoles)
* Now to obtain a serial console URL from the API or from python-novaclient
* Examples of managing the ports specified in the port_range so that they are
  only accessible from the node where the serialproxy is deployed and not from
  the outside.

References
==========

None
