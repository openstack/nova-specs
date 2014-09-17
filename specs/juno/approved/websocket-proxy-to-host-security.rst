..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================================
Support Proxying of Encryption and Authentication in WebSocketProxy
===================================================================

https://blueprints.launchpad.net/nova/+spec/websocket-proxy-to-host-security

Currently, while the noVNC and HTML5 SPICE clients can use TLS-encrypted
WebSockets to communicate with Websockify (and authenticate with Nova console
tokens), the encryption and authentication ends there.  There are neither
encryption nor authentication between Websockify and the hypervisors'
VNC and SPICE servers.

This blueprint would propose introducing a generic framework for supporting
proxying security for Websockify to use between itself and the compute nodes.

Problem description
===================

Currently, there are neither authentication nor encryption between Websockify
and the hypervisors' SPICE and VNC servers.  Were a malicious entity to gain
access to the "internal" network of an OpenStack deployment he or she could:

* "Listen" to VNC and SPICE traffic (lack of encryption)

* Connect freely to the SPICE and VNC servers of VMs (lack of authentication)

For example, suppose Alice starts a VM, which gets placed on "hypervisor-a".
Carol could then use Wireshark or the like to watch what Alice is doing with
her VM's console.  Furthermore, Carol could point her VNC client at
"hypervisor-a:5900" and actually access the VM's console.

Proposed change
===============

This blueprint would introduce a generic framework performing proxying of
authentication and encryption.  When establishing a connection, the proxy would
act as a client to the server and a server to the client, performing different
steps for each during the security negotiation phase of the respective
protocols.

The proxy would then wrap the server socket in an encryption layer that
respected the standard python socket class (much like python's :code:`ssl`
library does) and pass the resulting wrapped socket off to the normal proxy
code.

Authentication drivers would have a class for SPICE as well as for VNC
(since VNC has to do some extra negotiation as part of the RFB protocol).
Deployers could then point Nova to the appropriate driver and options via
configuration options.

A base driver for TLS [1]_ (VeNCrypt for VNC, plain TLS for SPICE) would be
included as an example implementation, although it would be beneficial to
develop further drivers, such as a SASL driver [2]_.

.. [1] To ensure only the correct clients connect, the proxy would send
       the hypervisor x509 client certificates, and the server would reject
       any certificates not signed by the specified CA (authentication).  To
       prevent evesdroppers, the actual data stream would use TLS encryption.
       While both of these are supported for VNC by QEMU (and thus KVM, Xen,
       etc), it would appear that SPICE only supports the encryption.  If a
       deployment is using SPICE, another driver should be used.

.. [2] Such a driver would most likely use the GSSAPI mechanism, which would
       provide Kerberos encryption and authentication for the connections.
       However, SASL supports other mechanisms, so non-GSSAPI drivers could
       be written.  Some mechanisms do not support encryption ("data-layer
       security" in SASL terms), so TLS should be used to provide encryption
       with those.  SASL connections are by both SPICE and VNC on QEMU fully.

Alternatives
------------

* Doing end-to-end security: this would require supporting more advanced
  encryption and authentication in the HTML5 clients.  Unfortunately, this
  requires doing cryptography in the browser, which is not really feasible
  until more browsers start implementing the HTML5 WebCrypto API.

* Using a tool like stunnel: There are a couple of issues with this.  The first
  is that it locks us in to a particular authentication mechanism -- stunnel
  works fine for TLS, but will not work if we want to use SASL instead.
  The second issue is that it bypasses normal VNC security negotation, which
  does the initial handshake in the clear, and then moves on to security
  negotiation later.  It is desired to stay within the confines of the standard
  RFB (VNC) specification.  The third issue is that this would sidestep the
  issue of authentication -- a malicous entity could still connect directly to
  the unauthenticated port, unless you explicitly set up your firewall to block
  remote connections to the normal VNC ports (which requires more setup on the
  part of the deployer -- we want to make it fairly easy to use this).

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

The actual crypto done would depend on the driver being used.  It will be
important to ensure that the libraries used behind any implemented drivers
are actually secure.

Assuming the driver is secure and implements both authentication and
encryption, the security of the deployment would be strengthened.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Minimal.  The extra encryption will most likely be performed via a C-based
python library, so there will be relatively low overhead.

Other deployer impact
---------------------

First, a deployer would have to choose the driver that he or she wished to use:
:code:`console_proxy_security_driver = driver_name`.  Then, the particular
driver would be have configuration options under its own section in the
configuration file.  For instance, the x509/TLS driver would appear as the
following:

.. code::

   [console_proxy_tls]
   ca_certificate = /path/to/ca.cert
   client_certificate = /path/to/client.cert

Finally, most drivers will require extra setup outside of Nova.  For instance,
the x509/TLS driver will reqiure generating CA, client, and server
certificates, distributing the CA and client certificates, and configuring
libvirt to require x509/TLS encryption and authentication when connecting to
VNC and SPICE consoles (see `References`_).

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    sross-7

Other contributors:
    None

Work Items
----------

1. Implement the base framework for proxying authentication and
   encryption.

2. Implement a No-op driver

3. Implement the basic x509/TLS driver


Dependencies
============

While individual drivers might introduce new dependencies,
the actual framework would not.


Testing
=======

We should test that the framework is callable correctly.  Additionally,
it will be necessary to work with infra to ensure that we can test the actual
drivers (for instance, for x509/TLS, we will need to generate certificates,
etc).


Documentation Impact
====================

We will need to document the new configuration options, as well as how to
generate certificates for the TLS driver (See `Other deployer impact`_).


References
==========

* The most recent version of the VeNCrypt specification can be found in
  this thread http://sourceforge.net/p/tigervnc/mailman/message/25748057/ --
  http://sourceforge.net/p/tigervnc/mailman/attachment/20100720083109.GA3303%40evileye.atkac.brq.redhat.com/1/

* SPICE TLS: http://www.spice-space.org/docs/spice_user_manual.pdf -- page 11

* libvirt TLS setup:
  VNC: http://wiki.libvirt.org/page/VNCTLSSetup,
  SPICE: http://people.freedesktop.org/~teuf/spice-doc/html/ch02s08.html
