..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
libvirt SPICE direct consoles
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-spice-direct-consoles

This specification proposes modifications to Nova's libvirt driver to support
"direct" SPICE VDI consoles. These consoles are "direct" in that they are not
intended to use a HTML5 transcoding proxy to access, and instead the user would
use a native SPICE client like `remote-viewer`. Such a facility enables a much
richer virtual desktop experience that Nova current supports, in return for
relatively minor changes to Nova. A new Nova API microversion is also required
to allow users of these consoles to lookup connection details for the console.

Problem description
===================

The SPICE protocol was added to Nova a long time ago, and still represents the
richest and most performant option for remote desktops using Nova. However at
the moment, Novas's HTML5 transcoding proxy is the only way to access these
SPICE consoles, and the HTML5 interface does not support many of the more novel
features of the SPICE protocol, nor does it support high resolution desktops
well.

Use Cases
---------

*As a developer, I don't want these changes to make the Nova codebase even more
complicated.* The changes proposed are relatively contained -- a single new API
microversion, some changes to the domain XML generation code which are
optional, and associated tests.

*As a deployer, I want to be able to use OpenStack to provide rich virtual
desktops to my users.* This change facilitates such functionality, but does
require additional deployment steps such as setup to TLS certificates for your
hypervisors and management of a SPICE native proxy. There is a sample
implementation using Kolla-Ansible available, but other deployment systems
would need to integrate this functionality for it to be generally available.

*As a deployer who doesn't want rich desktop consoles, I don't want this
functionality to complicate my deployment.* When disabled, the changes to
deployments are minor -- for example the extra USB passthrough devices and
sound devices in the domain XML are all deployer configurable and can be
disabled.

*As an end user, I would like access to a richer desktop experience than is
currently available.* Once these changes are integrated and Kerbside deployed,
a further change to either Horizon or Skyline will be required to orchestrate
console access via Kerbside. It is expected the complete end to end
functionality will take several releases to land before a fully seamless
experience is available. Once fully implemented, Horizon and Skyline will be
capable of delivering a `.vv` configuration file for a specific console to a
client, who will then have seamless access to their virtual desktop. However,
a user will be able to use the `openstack console url show` command immediately
to create a console session outside of our web clients.

Proposed change
===============

The proposed solution is relatively simple -- add an API microversion which
makes it possible to create a "spice-direct" console, and to lookup connection
details for that console from the API. The new console type and microversion is
required because we need to be able to specify the new console type, which is
an API schema change.

The response from a `get_spice_console` or `create` call which requests a
"spice-direct" console will return a URL derived from
`CONF.spice.kerbside_base_url`, and will include a console access token. The
user would then request this URL, and Kerbside would lookup console connection
details from nova via the `/os-console-auth-tokens/` API. These details would
be used to generate a virt-viewer still .vv configuration file, which the user
can then use to access a proxied SPICE console.

Because the response from `/os-console-auth-tokens/` includes the host and port
on the hypervisor that the SPICE console is running on, it is agreed that these
API methods should have restricted accessibility. However, this is a
pre-existing API and this should already be true. This protects sensitive
network configuration information from being provided to less trusted users.

This specification also covers tweaks the to the libvirt domain XML to enrich
the desktop experience provided by such a direct console, such as:

* requiring an encrypted connection (WIP implementation at
  Ica7083b0836f8d66cad8a4b4097613103fc91560)
* allowing concurrent users as supported by SPICE (WIP implementation at
  I65f94771abdc1a6ef54637ea81f25ce1daaf4963)
* USB device passthrough from client to guest (WIP implementation at
  I0cbd28be272991f95c8fb9d76ee65b2b99a8bcf1)
* sound support (WIP implementation at
  I4c98a0d6307c5e331df5caea80cb760512370058)

The proposed changes allow direct connection to a SPICE console from a SPICE
native client like `remote-viewer`. Without additional software, this implies
that such a client would have network connectivity to relatively arbitrary TCP
ports on the hypervisor hosting the instance. However, a SPICE protocol native
proxy now exists, and a parallel proposal to this one proposes adding support
for it to Kolla-Ansible. This proxy is called Kerbside, and more details are
available at https://github.com/shakenfist/kerbside. That is, with the proxy
deployed there is effectively no change to the network exposure of Nova
hypervisors.

As part of prototyping this functionality, a series of patches to Nova were
developed. These are available at
https://github.com/shakenfist/kerbside-patches/tree/develop/nova as well as
on gerrit at
https://review.opendev.org/q/topic:%22kerbside-spice-direct-consoles%22.

They are:

* Allow Nova to require secured SPICE connections, via a new `require_secure`
  configuration option in the SPICE configuration group.
* Add an API microversion to expose the "spice-direct" console type.
* Allowing concurrent connections to SPICE consoles for people who want to
  share a console session.
* Supporting USB passthrough.
* Optionally enabling SPICE debugging in qemu.
* Adding a sound device so that the consoles can do audio. This will be done
  via a
* Add an optional dependency in Nova to the Kerbside API client library so that
  Nova can fetch console connection details to proxy to a requesting user.

When implemented, a user can fetch a Kerbside connection URL like this:

```
openstack console url show --spice-direct 52b2e44e-e561-464c-88f3-2fc6a1ecea2b
+----------+------------------------------------------------------------------+
| Field    | Value                                                            |
+----------+------------------------------------------------------------------+
| protocol | spice                                                            |
| type     | spice-direct                                                     |
| url      | http://127.0.0.1:13002/nova?token=bf2e6883-...                   |
+----------+------------------------------------------------------------------+
```

The user then fetches that URL, and Kerbside delivers a .vv file with the
connection information for a SPICE client. Kerbside uses a call to
`/os-console-auth-tokens/bf2e6883-...` to determine the validity of the
console authentication token, and the connection information for the console.

Alternatives
------------

Unfortunately the SPICE HTML5 proxy does not meet the needs to many remote
desktop users. Realistically OpenStack does not currently have a way of
providing these rich desktop consoles to users. Instead, other systems such as
Citrix are used for this functionality.

Data model impact
-----------------

The console auth token table needs to have an extra column added so that TLS
ports can be tracked alongside unencrypted ports. This change is minor and
should not be difficult for deployers to support as this table should not be
particularly large given authentication tokens already expire.

REST API impact
---------------

This specification adds a new console type, "spice-direct", which provides
the connection information required to talk the native SPICE protocol
directly to qemu on the hypervisor. This is intended to be fronted
by a proxy which will handle authentication separately.

A new microversion is introduced which adds the type "spice-direct"
to the existing "spice" protocol.

This implies that the JSON schema for `create` console call would change to
something like this:

.. code-block::

    create_v297 = {
        'type': 'object',
        'properties': {
            'remote_console': {
                'type': 'object',
                'properties': {
                    'protocol': {
                        'type': 'string',
                        'enum': ['vnc', 'spice', 'rdp', 'serial', 'mks'],
                    },
                    'type': {
                        'type': 'string',
                        'enum': ['novnc', 'xvpvnc', 'spice-html5',
                                 'spice-direct', 'serial', 'webmks'],
                    },
                },
                'required': ['protocol', 'type'],
                'additionalProperties': False,
            },
        },
        'required': ['remote_console'],
        'additionalProperties': False,
    }

And that the JSON schema for the `get_spice_console` would change to
something like this:

.. code-block::

    get_spice_console_v297 = {
        'type': 'object',
        'properties': {
            'os-getSPICEConsole': {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['spice-html5', 'spice-direct'],
                    },
                },
                'required': ['type'],
                'additionalProperties': False,
            },
        },
        'required': ['os-getSPICEConsole'],
        'additionalProperties': False,
    }

The response from `/os-console-auth-tokens/` also needs to be tweaked to return
a TLS port if one is configured for the console, which will require a response
schema change.

Security impact
---------------

This proposal has a medium security impact. While hypervisor host / port
details will only be exposed to requestors that have the `service` role or
`admin` permissions, Kerbside does need to have network connectivity to the
SPICE TCP ports on the hypervisors in the cloud. However, Kerbside provides a
protective layer to these TCP ports, and it is not intended to expose this
information to less privileged requestors.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

As discussed, a complete implementation requires deployment systems to
integrate the Kerbside SPICE proxy, as well as modifications to front ends
such as Horizon and Skyline to orchestrate consoles via Kerbside. However,
those are outside the scope of a Nova specification.

The following configuration options are added by the proposed changes:

* `spice.kerbside_base_url`: defaults to an example URL which wouldn't actually
  work for a non-trivial installation (just as the HTML5 transcoding proxy
  does). This is the base URL for the Kerbside URLs handed out by Nova.

* `spice.require_secure`: defaults to `False`, the current hard coded
  default. Whether to require secure TLS connections to SPICE consoles. If
  you're providing direct access to SPICE consoles instead of using the
  HTML5 proxy, you may wish those connections to be encrypted. If so, set
  this value to True. Note that use of secure consoles requires that you
  setup TLS certificates on each hypervisor.

* `spice.allow_concurrent`: defaults to `False`, the current hard coded
  default. Whether to allow concurrent access to SPICE consoles. SPICE
  supports multiple users accessing the same console simultaneously, with
  some reduced functionality for the second and subsequent users. Set this
  option to True to enable concurrent access to SPICE consoles.

* `spice.debug_logging`: defaults to `False`, the current hard coded
  default. Whether to emit SPICE debug logs or not to the qemu log. These
  debug logs are verbose, but can help diagnose some connectivity issues.

The following additional image property will be added:

* `hw_audio_model`: defaults to `None`, the current hard coded
  default. Whether to include a sound device for instance when SPICE
  consoles are enabled, and if so what type.

Additionally, if SPICE consoles are enabled, then USB passthrough devices are
created in the guest. These devices are harmless if not used by a client
capable of using USB passthrough.

Developer impact
----------------

None.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mikal

Other contributors:
  None

Feature Liaison
---------------

Liaison needed.

Work Items
----------

Land the patches at
https://github.com/shakenfist/kerbside-patches/tree/develop/nova
in the order specified there, with any modifications requested by the Nova team
during code review.

Dependencies
============

None.

Testing
=======

Testing graphical user interfaces in the gate is hard. However, a test for the
API microversion will be added, and manual testing of the console functionality
has occurred on the prototype and will be redone as the patches land.

Documentation Impact
====================

The Operators Guide will need to be updated to cover the new functionality and
configuration options. The End User's guide will need to be updated to
explain usage once the functionality is fully integrated.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.2 Dalmatian
     - Introduced
