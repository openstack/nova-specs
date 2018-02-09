..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================================
Support Proxying of Encryption and Authentication in WebSocketProxy
===================================================================

https://blueprints.launchpad.net/nova/+spec/websocket-proxy-to-host-security

Currently, while the noVNC, HTML5 SPICE and serial console clients can use
TLS-encrypted WebSockets to communicate with the nova websocket proxy server
(and authenticate with Nova console tokens), the encryption and authentication
ends there. There is neither encryption or authentication between the
websockets proxy and the compute node VNC, SPICE and serial console servers.

This spec describes the addition of TLS for all three services to provide
encryption, and use of x509 certificates to authenticate connection attempts to
the compute node console servers.

Problem description
===================

Currently, there is neither authentication or encryption between the websocket
proxy server and the compute node VNC, SPICE & serial console servers.  Were a
malicious entity to gain access to the "internal" network of an OpenStack
deployment they can perform three attacks:

* Passive snooping of all traffic between the proxy and compute node.  This
  could allow the attacker to identify key strokes associated with tenant user
  passwords, or view sensitive information displayed on the virtual desktop.

* Actively impersonate the proxy server, making connections to the compute node
  VNC, SPICE, serial console servers, viewing the tenant's data and interacting
  with their machine.

* Actively impersonate the compute node, providing a spoof remote desktop for
  the proxy server to connect to. This allows the attacker to modify the
  information presented on the desktop for their own purposes.

Use Cases
---------

This addresses the use case where VNC, SPICE or serial console is enabled for a
production deployment of Nova, and the Nova WebSocketProxy is running.

The aim is to provide protection against the three attack scenarios described
above. They will be prevented as follows:

* Passive snooping of the traffic between the proxy and compute node for VNC,
  SPICE and serial console will be blocked by use of TLS for encryption of the
  remote desktop session data.

* Active impersonation of the proxy server will be prevented for VNC and serial
  console by enabling the use of x509 certificates. The proxy server will have
  to present its own certificate to the compute node when connecting which will
  validate the certificate against its permitted whitelist. At time of writing
  SPICE does not have support for validating client x509 certificates. If this
  is developed by the SPICE maintainers, it will also be added to Nova.

* Active impersonation of the compute node will be prevented for VNC, SPICE and
  serial console through the use of x509 certificates. The compute node will
  send its certificate to the proxy server, which will then validate the
  certificate against the CA certificates.

This protection is based on the assumption that the attacker is not able to get
x509 certificates issued by the authority used on the compute nodes and proxy
servers.

Proposed change
===============

This blueprint would introduce callbacks into the websocket proxy classes to
enable negotiation of security features such as TLS encryption, x509
certificate validation and other authentication schemes. The hooks will be able
to optionally perform protocol specific handshakes, and then modify the socket
between the proxy and compute node, replacing the default clear text socket
with an TLS wrapped one, or equivalent.

The intention is to implemented the VeNCrypt authentication scheme for VNC,
which requires providing a security proxy hook that can perform a basic RFB
protocol handshake / negotiation.

For SPICE and serial consoles, it is sufficient to simply replace the default
clear text socket with a TLS wrapped one. It is not immediately neccesssary to
get involved in the SPICE protocol negotiation, since TLS is enabled before the
protocol even starts.

There is no impact on migration, since the change does not require any update
to the guest XML configuration. It is purely a host level config setting on the
compute nodes.

Alternatives
------------

* Doing end-to-end security: this would require supporting more advanced
  encryption and authentication in the HTML5 clients. Unfortunately, this
  requires doing cryptography in the browser, which is not really feasible
  until more browsers start implementing the HTML5 WebCrypto API. End-to-end
  security would also imply that the remote tenant client is able to directly
  see the x509 certificates associated with the compute nodes. This forces the
  deployer to use the same x509 certificate authority for both connections
  inside the cloud and on the public internet. From a manageability point of
  view it is highly desirable to have CA for the internal network completely
  separate from the CA used for public tenant facing servers.

* Using a tool like stunnel: There are a couple of issues with this.  The first
  is that it locks us in to a particular authentication mechanism -- stunnel
  works fine for TLS, but will not work if we want to use SASL instead.  The
  second issue is that it bypasses normal VNC security negotation, which does
  the initial handshake in the clear, and then moves on to security negotiation
  later. It is desired to stay within the confines of the standard RFB (VNC)
  specification.  The third issue is that this would sidestep the issue of
  authentication -- a malicous entity could still connect directly to the
  unauthenticated port, unless you explicitly set up your firewall to block
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
important to ensure that the libraries used behind any implemented drivers are
actually secure.

Assuming the driver is secure and implements both authentication and
encryption, the security of the deployment would be strengthened.

For new deployments, all compute nodes and thus all VM will be able to have TLS
enabled straightaway. The console proxy nodes can thus mandate use of TLS for
all connections. When upgrading existing deployments, however, the console
proxy node will need to allow for some VMs / compute nodes using non-TLS
connections. During this transition period the console proxy is thus
potentially susceptible to a MITM downgrade attack where the attacker strips
TLS. This is no worse than the security risk of running all compute nodes in
plain text as is done with all existing Nova releases. It simply means that the
full security benefit is not obtained until all compute nodes and running VMs
have been upgraded to use TLS. Once this is done and the ``tls_required``
config options are set to ``true``, a downgrade attack is no longer possible.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Minimal.  The extra encryption will most likely be performed via a C-based
Python library, so there will be relatively low overhead.

Other deployer impact
---------------------

For VNC, a deployer will have to enable use of the 'vencrypt' authentication
scheme. This will be done via a new ``[vnc] auth_schemes`` configuration
parameter which takes a list of strings identifying VNC authentication schemes
to try.

When the ``vencrypt`` scheme is chosen, the deployer will also have to provide
x509 certificate configuration for the novncproxy service

.. code::

   [vnc]
   tls_ca_certs = /path/to/ca-cert-bundle.pem
   tls_client_cert = /path/to/client-cert.pem
   tls_client_key = /path/to/client-key.pem

In addition there will be a requirements to configure the virtualization
host to enable use of TLS with VNC. For QEMU/KVM compute nodes this will
involve modifying ``/etc/libvirt/qemu.conf`` and issuing x509 certificates to
the compute nodes. (see `References`_).

When enabling ``vencrypt`` for an existing deployment, two stages will be
required. Initially the ``[vnc]auth_schemes`` configuration parameter will need
to list both ``vencrypt`` and ``none`` auth schemes. This allows the proxy to
connect to both pre-existing deployed compute hosts which do not have TLS
turned on and newly updated compute with TLS. Once all compute hosts have been
updated to enable TLS, the ``[vnc] auth_schemes`` configuration parameter can
be switched to only permit ``vencrypt``.

For SPICE, the deployer will also have to provide x509 certificate
configuration for the spicehtml5proxy service

.. code::

   [spice]
   tls_ca_certs = /path/to/ca-cert-bundle.pem
   tls_required = <boolean>

Note SPICE does not currently make use of client certificates, so there is no
equivalent to the ``[vnc] tls_client_cert`` parameter.

In addition there will be a requirements to configure the virtualization host
to enable use of TLS with SPICE. For QEMU/KVM compute nodes this will involve
modifying ``/etc/libvirt/qemu.conf`` and issuing x509 certificates to the
compute nodes. (see `References`_).

When enabling TLS for an existing deployment, two stages will be required.
Initially the ``[spice] tls_required`` configuration parameter will be set to
``False``. This allows the proxy to connect to both pre-existing deployed
compute hosts which do not have TLS turned on and newly updated compute with
TLS. Once all compute hosts have been updated to enable TLS, the ``[spice]
tls_required`` configuration parameter can be switched to ``True``.

For serial consoles, a deployer will have to enable use of TLS by providing a
CA certificate bundle, and optionally a client certificate and key

.. code::

   [serial_console]
   tls_ca_certs = /path/to/ca-cert-bundle.pem
   tls_client_cert = /path/to/client-cert.pem
   tls_client_key = /path/to/client-key.pem
   tls_required = <boolean>

In addition there will be a requirements to configure the virtualization host
to enable use of TLS with serial ports. For QEMU/KVM compute nodes this will
involve modifying ``/etc/libvirt/qemu.conf`` and issuing x509 certificates to
the compute nodes. (see `References`_).

When enabling TLS for an existing deployment, two stages will be
required. Initially the ``[serial_console] tls_required`` configuration
parameter will be set to ``False``. This allows the proxy to connect to
both pre-existing deployed compute hosts which do not have TLS turned on
and newly updated compute with TLS. Once all compute hosts have been
updated to enable TLS, the ``[serial_console] tls_required`` configuration
parameter can be switched to ``True``.

Developer impact
----------------

None of the other non-QEMU hypervisors support VNC / SPICE / serial port TLS
encryption at this, so this work is only relevant for libvirt with QEMU/KVM. If
other hypervisors gain TLS support later, it should be straightforward for them
to enable it using the enhancements done for libvirt with QEMU.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Stephen Finucane <stephenfin>
Other contributors:
    Daniel Berrangé <berrange>

Work Items
----------

1. Modify the websockets proxy base classes to add hooks that subclasses can
   use to implement encryption and authentication.

2. Create a framework for implementing VNC authentication mechanisms.

3. Create a websockets proxy security driver that can perform a VNC protocol
   negotiation, invoking the VNC authentication schemes at appropriate times.

4. Modify the novncproxy server to enable the VNC security driver

5. Modify the spicehtml5proxy server to enable it to open an SSL socket when
   required

6. Modify devstack to enable it to generate suitable certificates for compute
   nodes and security proxy nodes and enable TLS for VNC, SPICE and serial
   consoles.

7. Modify tempest to perform blackbox testing of the remote console service, to
   validate that its possible to successfully establish a console connection
   when TLS is enabled.

8. Modify documentation to describe the procedure for deploying compute nodes
   and the console proxy servers with TLS security enabled.

Dependencies
============

Support for the VNC and SPICE features is already available in all versions of
QEMU and Libvirt that Nova supports, and it is thus already possible to test it
with currently gate CI nodes.

Support for the serial console TLS feature will require QEMU >= 2.6 and a
libvirt >= 2.2.0. Deployments which lack these versions will have to continue
using the serial console in clear text mode until they upgrade.

Testing
=======

`Tempest has been enhanced`__ to validate the ability to open a remote console
for VNC and SPICE. Unit tests will be included.

__ https://github.com/openstack/tempest/blob/master/tempest/api/compute/servers/test_novnc.py

Documentation Impact
====================

We will need to document the new configuration options, as well as how to
generate certificates for the TLS driver (See `Other deployer impact`_).

References
==========

* The most recent version of the VeNCrypt specification can be found at
  https://github.com/rfbproto/rfbproto/blob/master/rfbproto.rst#id28

* SPICE TLS: http://www.spice-space.org/docs/spice_user_manual.pdf -- page 11

* libvirt TLS setup:

  * VNC: http://wiki.libvirt.org/page/VNCTLSSetup,
  * SPICE: http://people.freedesktop.org/~teuf/spice-doc/html/ch02s08.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Kilo
     - Introduced
   * - Liberty
     - Re-proposed
   * - Mitaka
     - Re-proposed
   * - Newton
     - Re-proposed
   * - Ocata
     - Re-proposed
   * - Pike
     - Re-proposed
   * - Queens
     - Re-proposed
