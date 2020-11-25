..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Nova provides remote console with password authentication
=========================================================

https://blueprints.launchpad.net/nova/+spec/nova-support-webvnc-with-password-authentication

The feature aims at providing a safer remote console with password
authentication. End users can set console password for their instances.
Any user trying to access the password-encrypted console of instance
will get a locked window from web console prompting for ``password``
input, and this provides almost the same experience as using VNC clients
(e.g vncviewer) to access vnc servers that require password authentication.

Problem description
===================
There is only a token authentication against nova novncproxy, with the
``token`` parameter appended to the request access_url. While this is
convenient, anyone who (e.g. A cloud administrator with too much curiosity
about tenants' business) gets the access_url info will have access to
operating the instance by the web console directly, which is not safe.

Now an implementation for remote console with password authentication
will prevent malicious users from using the instance when failing to pass
password authentication, even if they had got the access_url.

Use Cases
---------

The end user can set a remote console password to avoid the console access
url stolen by other user. And end user can reset console password when
he forgets.

Proposed change
===============

* A new microversion will be provided in the nova API (``nova get-*-console``
  subcommand) and OSC will need to provide a specific version for reseting
  remote console password.

* The nova API will be extended to support console password when creating a
  remote console.
  There are two ``create console`` APIs. The first was only for the old
  nova-consoles services (XenAPI-only) and was removed in Ussuri release [1]_.
  The second, which is we will changes to support console password, is still
  valid [2]_.
  And the server actions for the other console [3]_, the console output
  server action still need to be protected, and the deprecated action also
  need to be blocked when the instance has a password set.

* Changes will be proposed to nova-compute and virt driver to handle
  ``Reset Remote Console Password`` request. And this's only implement
  for libvirt driver. For other virt drivers, NotImplement will raise.

* Changes will be proposed to nova-novncproxy: auth schemes(e.g:rfb.VNC)
  will be added. For the fact that project ``noVNC`` has already provided
  native support for password authentication(RFB version negotiation,
  handshakes and password authentication), so rfb.VNC can escape from
  these jobs.

Alternatives
------------

New booting parameter ``console_password`` will be added to launch instances.
And the password will be used to assemble ``graphics`` tag in libvirt XML.
In this way, password-encrypted remote console will be implemented.
The shortcoming of this implement is that no API provided to reset console
password after instance is booted.

Data model impact
-----------------

None

REST API impact
---------------

New microversion will be added to provide extra ``password`` parameter
for the Create Remote Console API.

URL: /servers/{server_id}/remote-consoles

* Request method: POST(update password for remote console)
  Add ``password`` param to the request body

* Update the Create-Remote-Console API:

  .. code-block:: json

     {
        "remote_console": {
            "protocol": "vnc",
            "type": "novnc",
            "password": "newpass"
        }
     }

  The ``password`` is in common password format (not more than 8 characters,
  see `vnc security`_).
  The ``password`` parameter is optional:

  - If ``password`` is present, console password will be updated while
    getting new access_url.
  - Only `vnc` and `spice` console protocols/types support reseting
    password. If both ``password`` and (``protocol``, ``type``)
    are provided, and protocol/type not in support list
    ``HttpBadRequest 400`` will be returned.
  - And for unsupported virt driver, ``HttpBadRequest 400`` will be
    returned.

Security impact
---------------

Surely it will make web console safer. And note that console password will
only be securely kept by libvirtd and won't be displayed in the result
of ``virsh dumpxml <Instance UUID>`` or definition XMLs managed by libvirt
/qemu in local filesystem except. Briefly speaking, no potential security
risks will be introduced.


If we hard reboot the instance, it will be recreate XML when is booting,
and the old console will be disconnect. If you want to open the instance's
console again, you can reset the password and open a new console.

Notifications impact
--------------------

None

Other end user impact
---------------------

It does have impacts on end users:

* Web GUI benefiting this feature allow end users to set/reset
  console passwords for their instances.

* When end users access password-encryted console of instances
  via Web GUI, input for console password will be prompted from
  web console.

* New `get-*-console` CLIs may look like this(using nova command):

  .. code-block:: shell

    $ nova get-vnc-console --vnc-password='newpasswd' <VM UUID> ...
    $ nova get-spice-console --vnc-password='newpasswd' <VM UUID> ...


Performance Impact
------------------

None

Other deployer impact
---------------------

New option ``vnc`` is added to auth_schemes list in ``vnc``
segment in ``nova.conf``. This allows nova-novncproxy to
detect and load rfb.VNC auth scheme.

.. code-block:: ini

  [vnc]
  auth_schemes = none,vnc,vencrypt

Developer impact
----------------

None

Upgrade impact
--------------

We should bump service object version and rpc version for the 'get_*_console'
rpc call. Then only when the cluster fully upgrade to Wallaby release, the
call can be success. otherwise return ``HttpBadRequest 400`` for the request.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  brinzhang

Other contributors:
  songwenping

Feature Liaison
---------------

Feature liaison:
  brinzhang

Work Items
----------

* python-novaclient(and openstackclient as well): new
  ``--password`` option will be added to ``get-*-console``
  commands and some codes processing this value shall be added.

* nova-api: some codes to judge whether to call legacy
  ``get-*-console`` API or to call remote compute service to
  reset remote console password.

* nova-compute: some codes to handle the request to reset console
  password: reassemble graphics tag with password and update it to
  libvirt XML.

* nova-novncproxy: some codes to implement rfb auth schemes,
  security type negotiation (in current version, novncproxy tells
  tenant_sock to use hardcoded ``vnc.AuthType.NONE`` when serving
  as mediator between client and vnc server, though noVNC client
  provides native support for ``vnc.AuthType.VNC`` with password
  security handshake handle) and ``security handshake`` (no-ops,
  leave noVNC/websockify to do the stuff).

Dependencies
============

None

Testing
=======

Add related unit test

Documentation Impact
====================

* `Operation Guide` needs some updates, in #User-Facing Operations#
  section.The ``nova get-*-console`` (or equivalent with openstack
  CLI) provides ``--vnc-password`` option to user to reset console
  console password.

* `API Guides` needs no updates. However, some texts should be posted
  to notify developers about how to benefit from this feature.

* `Configuration Reference` & `Deployment Guides` need some updates.
  A change in nova.conf to enable rfb.VNC auth scheme is added (nova
  -novncproxy cares).

References
==========

.. [1] https://docs.openstack.org/api-ref/compute/#xenserver-vnc-proxy-xvp-consoles-os-consoles
.. [2] https://docs.openstack.org/api-ref/compute/?expanded=#server-consoles
.. [3] https://docs.openstack.org/api-ref/compute/?expanded=create-console-detail#get-vnc-console-os-getvncconsole-action-deprecated

.. _`vnc security`: http://people.redhat.com/pbonzini/qemu-test-doc/_build/html/topics/vnc_005fsecurity.html

* https://libvirt.org/formatdomain.html#elementsGraphics

* https://bugzilla.redhat.com/show_bug.cgi?id=1180092

* https://tools.ietf.org/html/rfc6143

* https://en.wikipedia.org/wiki/Virtual_Network_Computing

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Approved
   * - Victoria
     - Re-proposed
   * - Wallaby
     - Re-proposed
