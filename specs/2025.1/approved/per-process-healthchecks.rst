..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Per Process Healthcheck endpoints
=================================

https://blueprints.launchpad.net/nova/+spec/per-process-healthchecks

In many modern deployment frameworks, there is an expectation that
an application can expose a health-check endpoint so that the binary
status can be monitored. Nova currently does not provide a native way
to inspect the health of its binaries which doesn't help cloud monitoring
and maintenance. While limited support exists for health checks via
Oslo middleware for our WSGI based API binaries, this blueprint seeks
to expose a local HTTP health-check endpoint to address this
feature gap consistently for all Nova components.


Problem description
===================

To monitor the health of a Nova service today requires experience to
develop and implement a series of external heuristics to infer the state
of the service binaries.

This can be as simple as checking the service status for those with heartbeats
or can comprise monitoring log output via a watchdog and restarting
the service if no output is detected after a protracted period.
Processing the logs for known error messages and executing a remediation script
or other methods that are easy to do incorrectly are also common.

This is also quite unfriendly to new Nova users who have not gained enough
experience with operating Nova to know what warning signs they should look
for such as inability to connect to the message bus. Nova developers however
do know what some of the important health indicators are and can expose
those as a local health-check endpoint that operators can use instead.

The existing Oslo middleware does not address this problem statement because:

#. It can only be used by the API and metadata binaries

#. The middleware does not tell you the service is alive if its hosted by a
   WSGI server like Apache since the middleware is executed independently from
   the WSGI application. i.e. the middleware can pass while the nova-api can't
   connect to the DB and is otherwise broken.

#. The Oslo middleware in detailed mode leaks info about the host Python
   kernel, Python version and hostname which can be used to determine in the
   host is vulnerable to CVEs which means it should never be exposed to the
   Internet. e.g.

::

  platform: 'Linux-5.15.2-xanmod1-tt-x86_64-with-glibc2.2.5',
  python_version: '3.8.12 (default, Aug 30 2021, 16:42:10) \n[GCC 10.3.0]'



Use Cases
---------

As an operator, I want a simple REST endpoint I can consume to know
if a Nova process is healthy.

As an operator I want this health check to not impact the performance of the
service so it can be queried frequently at short intervals.

As a deployment tool implementer, I want the health check to be local with no
dependencies on other hosts or services to function so I can integrate it with
service managers such as systemd or a container runtime like Docker.

As a packager, I would like the use of the health check endpoints to not
require special clients or packages to consume them. cURL, socat, or netcat
should be all that is required to connect to the health check and retrieve the
service status.

As an operator I would like to be able to use health-check of the Nova API and
metadata services to manage the membership of endpoints in my load-balancer
or reverse proxy automatically.

Proposed change
===============

Definitions
-----------
``TTL``: The time interval for which a health check item is valid.

``pass``: all health indicators are passing and their TTLs have not expired.

``warn``: any health indicator has an expired TTL or where there is
a partial transient failure.

``fail``: any health indicator is reporting an error or all TTLs are expired.

.. Note:

   In line with the recommendation in the IETF RFC API health check draft
   `[1]`_
   ``pass`` and ``warn`` will respond with a 200 OK
   ``fail`` will respond with a 503 Service Unavailable
   Content-Type: application/health+json will be used in all cases.



Warn vs fail
------------

In general if any of the health check indicators are failing then the service
should be reported as ``fail`` however if the specific error condition is
recoverable or only a partial failure the ``warn`` state can and should be
used.

An example of this is a service that has lost a connection to the message bus.
When the connection is lost it should go to the ``warn`` state, if the first
attempt to reconnect fails it should go to the ``fail`` state. Transient
failure should be considered warning but persistent errors should be escalated
to failures.

In many cases external management systems will treat ``warn`` and ``fail`` as
equivalent and raise an alarm or restart the service. While this spec does
not specify how you should recover from a degraded state, it is
important to include a human readable description of why the ``warn`` or
``fail`` state was entered.

Services in the ``warn`` state are still considered healthy in most cases but
they may be about to fail soon or be partially degraded.

.. NOTE:

  Where no health check items are currently registered such as during start up
  the health check, status will be considered ``pass`` not ``warn``
  or ``fail``. This will prevent restart loops for any service managers that
  treat any value other then ``pass`` as an error state.

Code changes
------------
A new top-level Nova health check module will be created to encapsulate the
common code and data structure required to implement this feature.

A new health check manager class will be introduced which will maintain the
health-check state and all functions related to retrieving, updating and
summarizing that state.

.. NOTE:

  All health check state will be stored in memory and reset/lost on restart
  of the binary. For services that support dynamic reconfiguration via SIG_HUP
  the health check data will be reset as part of this process.

The health check manager will be responsible for creating the health check
endpoint when it is enabled in the nova.conf and exposing the health check
over HTTP.

The initial implementation will support HTTP over TCP with optional support for
UNIX domain sockets as a more secure alternative to be added later.
The HTTP endpoint in both cases will be unauthenticated and the response will
be in JSON format.

A new HealthcheckStausItem data class will be introduced to store an
individual health check data-point. The HealtcheckStatusItem will contain
the name of the health check, its status, the time it was recorded,
and an optional output string that should be populated if the
status is ``warn`` or ``fail``.

A new decorator will be introduced that will automatically retrieve the
reference to the healthcheck manager from the Nova context object and update
the result based on whether the function decorated raises an exception or not.
The exception list and healthcheck item name will be specifiable.

The decorator will accept the name of the health check as a positional argument
and include the exception message as the output of the health check on failure.
Note that the decorator will only support the pass or fail status for
simplicity; where warn is appropriate a manual check should be written.
If multiple functions act as indicators of the same capability the same name
should be used.

e.g.

.. code-block:: python

   @healthcheck('database', [SQLAlchemyError])
   def my_db_func(self):
       pass

   @healthcheck('database', [SQLAlchemyError])
   def my_other_db_func(self):
       pass

By default all exceptions will be caught and re-raised by the decorator.

The new REST health check endpoint exposed by this spec will initially only
support one URL path ``/health``. The ``/health`` endpoint will include a
`Cache-Control: max-age=<ttl>` header as part of its response which can
optionally be consumed by the client.

The endpoint may also implement a simple incrementing etag at a later date
once the initial implementation is complete, if required.
Initially adding an ``etag`` is not provided as the response is expected to be
small and cheap to query, so etags do not actually provide much benefit form
a performance perspective.

If implemented, the ``etag`` will be incremented whenever the service state
changes and will reset to 0 when the service is restarted.

Additional URL paths may be supported in the future, for example to retrieve
the running configuration or trigger the generation of Guru Meditation Reports
or enable debug logging. However, any endpoint beyond ``/health`` is out of
scope of this spec. ``/`` is not used for health check response to facilitate
additional paths in the future.

Example output
~~~~~~~~~~~~~~

::

   GET /health HTTP/1.1
   Host: example.org
   Accept: application/health+json

   HTTP/1.1 200 OK
   Content-Type: application/health+json
   Cache-Control: max-age=3600
   Connection: close

   {
       "status": "pass",
       "version": "1.0",
       "serviceId": "e3c22423-cd7a-47dc-b6e9-e18d1a8b3bdf",
       "description": "nova-api",
       "notes": {"host": "controller-1.cloud", "hostname": "controller-1.cloud"}
       "checks": {
           "message_bus": {"status": "pass", "time": "2021-12-17T16:02:55+00:00"},
           "api_db": {"status": "pass", "time": "2021-12-17T16:02:55+00:00"}
       }
   }

   GET /health HTTP/1.1
   Host: example.org
   Accept: application/health+json

   HTTP/1.1 503 Sevice Unavailable
   Content-Type: application/health+json
   Cache-Control: no-cache
   Connection: close

   {
       "status": "fail",
       "version": "1.0",
       "serviceId": "0a47dceb-11b1-4d94-8b9c-927d998be320",
       "description": "nova-compute",
       "notes": {"host": "controller-1.cloud", "hostname": "controller-1.cloud"}
       "checks":{
           "message_bus":{"status": "pass", "time": "2021-12-17T16:02:55+00:00"},
           "hypervisor":{
                "status": "fail", "time": "2021-12-17T16:05:55+00:00",
                "output": "Libvirt Error: ..."
           }
       }
   }


.. NOTE:

   ``version`` will initially be 1.0 and can be incremented following
   ``SemVer`` conventions if we extend the response format.
   This is not the Nova version.
   Adding new checks to the Nova code base will not increment the version of
   the response but adding or removing any new field to the response will.
   The set of check names will be closed and each new check name that is added
   will be signaled by a minor version bump. The initial set of check names for
   version 1.0 is left to the implementation.
   ``serviceId`` should be set to the Nova service ID for this binary.
   ``description`` will contain the binary name for the service.
   ``notes`` the notes will contain the CONF.host value in the host field and
    optionally the hypervisor_hostname in the hostname field.
   ``status`` will contain the overall status of the service with details
   provided in the ``checks`` dictionary.
   The keys of the ``checks`` dictionary will be the name of the health check
   and the value will contain the ``status`` and ``time`` in ISO datetime
   format that the status was recorded at. If the ``status`` is ``warn`` or
   ``error`` an ``output`` key will be present with a message explaining the
   status.


Alternatives
------------

Instead of maintaining the state of the process in a data structure and
returning the cached state we, could implement the health check as a series of
active probes such as checking the DB schema version to ensure we can access
it or making a ping RPC call to the cell conductor or our own services RPC
endpoint.

While this approach has some advantages it will have a negative performance
impact if the health-check is queried frequently or in a large deployment where
infrequent queries may still degrade the DB and message bus performance due to
the scale of the deployment.

This spec initially suggested using ``OK``, ``Degraded`` and ``Faulty`` as the
values for the status field. These were updated to ``pass``, ``warn`` and
``fail`` to align with the draft IETF RFC for health check response format for
HTTP APIs `[1]`_.


Data model impact
-----------------

The Nova context object will be extended to store a reference to the
health check manager.


REST API impact
---------------

None

While this change will expose a new REST API endpoint it will not be
part of the existing Nova API.

In the Nova API the /health check route will not initially be used to allow
those that already enable the Oslo middleware to continue to do so.
In a future release Nova reserves the right to add a /health check endpoint
that may or may not correspond to the response format defined in Oslo.
A translation between the Oslo response format and the health check module
may be provided in the future but it is out of the scope of this spec.



Security impact
---------------

The new health check endpoint will be disabled by default.
When enabled it will not provide any authentication or explicit access control.
The documentation will detail that when enabled, the TCP endpoint should be
bound to ``localhost`` and that file system permission should be used to secure
the UNIX socket.

The TCP configuration option will not prevent binding it to a routable IP if
the operator chooses to do so. The intent is that the data contained in the
endpoint will be non-privileged however it may contain hostnames/FQDNs or other
infrastructure information such as service UUIDs, so it should not be
accessible from the Internet.

Notifications impact
--------------------

None

While the health checks will use the ability to send notification as an input
to determine the health of the system, this spec will not introduce any new
notifications and as such it will not impact the Notification subsystem in
Nova. New notifications are not added as this would incur a performance
overhead.

Other end user impact
---------------------

None

At present, it is not planned to extend the Nova client or the unified client
to query the new endpoint. cURL, socat, or any other UNIX socket or TCP HTTP
client can be used to invoke the endpoint.

Performance Impact
------------------

None

We expect there to be little or no performance impact as we will be taking a
minimally invasive approach to add health indicators to key functions
which will be cached in memory. While this will slightly increase memory usage
there is no expected impact on system performance.


Other deployer impact
---------------------

A new config section ``healthcheck`` will be added in the nova.conf

A ``uri`` config option will be introduced to enable the health check
functionality. The config option will be a string opt that supports a
comma-separated list of URIs with the following format

uri=<scheme>://[host:port|path],<scheme>://[host:port|path]

e.g.

::

  [healthcheck]
  uri=tcp://localhost:424242

  [healthcheck]
  uri=unix:///run/nova/nova-compute.sock

  [healthcheck]
  uri=tcp://localhost:424242,unix:///run/nova/nova-compute.sock

The URI should be limited to the following characters ``[a-zA-Z0-9_-]``,
``,`` is reserved as a separation character, ``.`` may only be used in IPv4
addresses, and ``:`` is reserved for port separation unless the address is an
IPv6 address. IPv6 addresses must be enclosed in ``[`` and  ``]``. ``/`` may
be used with the UNIX protocol however relative paths are not supported.
These constraints and the parsing of the URI will be enforced and provided by
the RFC3986 lib https://pypi.org/project/rfc3986/

A ``ttl`` IntOpt will be added with a default value of 300 seconds.
If set to 0, the time to live of a health check item will be infinite.
If the TTL expires, the state will be considered unknown and the healthcheck
item will be discarded.

A cache_control IntOpt will be provided to set the max-age value in the
cache_control header. By default it will have the same max-age as the TTL
config option. Setting this to 0 will disable the reporting of the header.
Setting this to -1 will report ``Cache-Control: no-cache``.
Any other positive integer value will be used as the max-age.



Developer impact
----------------

Developers should be aware of the new decorator and consider whether it should
be added to more functions, if that function is an indicator of the system's
health. Failures due to interactions with external systems such as Neutron port
binding external events should be handled with caution. While failure to
receive a port binding event will likely result in the failure to boot a VM, it
should not be used as a health indicator for the nova-compute agent. This is
because such a failure may be due to a failure in Neutron, not Nova. As such,
other operations such as VM snapshot may be unaffected and the Nova compute
service may be otherwise healthy. Any failure to connect to a non-OpenStack
service such as the message bus, hypervisor, or database should be treated as a
``warn`` or ``fail`` health indicator if it prevents the Nova binary from
functioning correctly.


Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  balazs-gibizer

Other contributors:
  melwitt

Feature Liaison
---------------

Feature liaison:
  balazs-gibizer

Work Items
----------

* Add new module
* Introduce decorator
* Extend context object to store a reference to health check manager
* Add config options
* Expose TCP endpoint
* Expose UNIX socket endpoint support
* Add docs

Dependencies
============

None

Testing
=======

This can be tested entirely with unit and functional tests, however,
Devstack will be extended to expose the endpoint and use it to determine
whether the Nova services have started.

Documentation Impact
====================

The config options will be documented in the config reference
and a release note will be added for the feature.

A new health check section will be added to the admin docs describing
the current response format and how to enable the feature and its intended
usage. This document should be evolved whenever the format changes or
new functionality is added beyond the scope of this spec.

References
==========

* Yoga PTG topic:
    https://etherpad.opendev.org/p/r.e70aa851abf8644c29c8abe4bce32b81#L415

.. _`[1]`: https://tools.ietf.org/id/draft-inadarei-api-health-check-06.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
   * - 2023.1 Antelope
     - Reproposed
   * - 2024.1 Caracal
     - Reproposed
   * - 2024.2 Dalmatian
     - Reproposed
   * - 2025.1 Epoxy
     - Reproposed
