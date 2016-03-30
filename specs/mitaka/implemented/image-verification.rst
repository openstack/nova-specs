..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Nova Signature Verification
===========================

https://blueprints.launchpad.net/nova/+spec/nova-support-image-signing

OpenStack currently does not support signature validation of uploaded signed
images. Equipping Nova with the ability to validate image signatures will
provide end users with stronger assurances of the integrity of the image data
they are using to create servers. This change will use the same data model for
image metadata as the accompanying functionality in Glance, which will allow
the end user to sign images and verify these image signatures upon upload [1].


Problem description
===================

Currently, OpenStack's protection against unexpected modification of images is
limited to verifying an MD5 checksum. While this may be sufficient for
protecting against accidental modifications, MD5 is a hash function, not an
authentication primitive [2], and thus provides no protection against
deliberate, malicious modification of images. An image could potentially be
modified in transit, such as when it is uploaded to Glance or transferred to
Nova. An image that is modified could include malicious code. Providing
support for signature verification would allow Nova to verify the signature
before booting and alert the user of successful signature verification via a
future API change. This feature will secure OpenStack against the following
attack scenarios:

* Man-in-the-Middle Attack - An adversary with access to the network between
  Nova and Glance is altering image data as Nova downloads the data from
  Glance. The adversary is potentially incorporating malware into the image
  and/or altering the image metadata.

* Untrusted Glance - In a hybrid cloud deployment, Glance is hosted on
  machines which are located in a physically insecure location or is hosted by
  a company with limited security infrastructure. Adversaries may be able to
  compromise the integrity of Glance and/or the integrity of images stored by
  Glance through physical access to the host machines or through poor network
  security on the part of the company hosting Glance.

Please note that our threat model considers only threats to the integrity of
images while they are in transit between the end user and Glance, while they
are at rest in Glance and while they are in transit between Glance and Nova.
This threat model does not include, and this feature therefore does not
address, threats to the integrity, availability, or confidentiality of Nova.

Use Cases
---------

* A user wants a high degree of assurance that a customized image which they
  have uploaded to Glance has not been accidentally or maliciously modified
  prior to booting the image.

With this proposed change, Nova will verify the signature of a signed image
while downloading that image. If the image signature cannot be verified, then
Nova will not boot the image and instead place the instance into an error
state. The user will begin to use this feature by uploading the image and the
image signature metadata to Glance via the Glance API's image-create method.
The required image signature metadata properties are as follows:

* img_signature - A string representation of the base 64 encoding of the
  signature of the image data.

* img_signature_hash_method - A string designating the hash method used for
  signing. Currently, the supported values are  SHA-224, SHA-256, SHA-384 and
  SHA-512. MD5 and other cryptographically weak hash methods will not be
  supported for this field. Any image signed with an unsupported hash
  algorithm will not pass validation.

* img_signature_key_type - A string designating the signature scheme used to
  generate the signature.

* img_signature_certificate_uuid - A string encoding the certificate
  uuid used to retrieve the certificate from the key manager.

The image verification functionality in Glance uses the signature_utils
module to verify this signature metadata before storing the image. If the
signature is not valid or the metadata is incomplete, this API method will
return a 400 error status and put the image into a "killed" state. Note that,
if the signature metadata is simply not present, the image will be stored as
it would normally.

The user would then create an instance from this image using the Nova API's
boot method. If the verify_glance_signatures flag in nova.conf is set to
'True', Nova will call out to Glance for the image's properties, which include
the properties necessary for image signature verification. Nova will pass the
image data and image properties to the signature_utils module, which will
verify the signature. If signature verification fails, or if the image
signature metadata is either incomplete or absent, booting the instance will
fail and Nova will log an exception. If signature verification succeeds, Nova
will boot the instance and log a message indicating that image signature
verification succeeded along with detailed information about the signing
certificate.


Proposed change
===============

The first component in this change is the creation of a standalone module
responsible for the bulk of the functionality necessary for image signature
verification. This module will primarily consist of three public-facing
methods: an initializing method, an updating method, and a verifying method.
The initializing method will take the signing certificate uuid and the
specified hash method as inputs. This method will then fetch the signing
certificate by interfacing with the key manager through Castellan, extract the
public key, store the public key, certificate and hash method as attributes
and return an instance of the signature verification module. As the image's
data is downloaded, the signature verification module will be updated by
passing chunks of image to the verifying module via the update method. When
all chunks of image data have been passed to the verifier, the service
desiring verfication will call the verify method, passing it the image
signature. More specifically, this module will apply the public key to the
signature, and compare this result to the result of applying the hash
algorithm to the image data. This workflow is essentially a wrapped version of
the workflow by which signature verification occurs in pyca/cryptography.

We then propose an initial implementation by incorporating this module into
Nova's control flow for booting instances from images. Upon downloading an
image, Nova will check whether the verify_glance_signatures configuration flag
is set in nova.conf. If so, the module will perform image signature
verification using image properties passed to Nova by Glance. If this fails,
or if the image signature metadata is incomplete or missing, Nova will not
boot the image. Instead, Nova will throw an exception and log an error. If the
signature verification succeeds, Nova will proceed with booting the instance.

The next component will be to add functionality to the pyca/cryptography
library which will validate a given certificate chain against a pool of given
root certificates which are known to be trusted. This algorithm for validating
chains of certificates against a set of trusted root certificates is a
standard, and has been outlined in RFC 5280 [3].

Once the certificate validation functionality has been added to the
pyca/cryptography library, we will amend the signature_utils module by
incorporating certificate validation into the signature verification workflow.
We will implement functionality in the signature_utils module which will use
GET requests to dynamically fetch the certificate chain for a given
certificate. Any service using the signature_utils module will now call the
signature_utils module's initializing method with an additional parameter: a
list of references representing a pool of trusted root certificates. This
module will then use its certificate chain fetching functionality to build the
certificate chain for the signing certificate, fetch the root certificates
through Castellan, and will verify this chain against the trusted root
certificates using the functionality in the pyca/cryptography library. If the
chain fails validation, then an exception will be thrown and signature
verification will fail. Nova will retrieve the root certificate references
necessary to call the updated functionality of the signature_utils module by
reading the references in from a root_certificate_references configuration
option in nova.conf.

Future API changes are necessary to mitigate attacks that are possible when
Glance is untrusted; such as Glance returning a different signed image than the
image that was requested. Possible changes include the following extensions:

* Modify the REST API to accept a specific signature required to verify the
  integrity of the image. If the specified signature cannot be verified, then
  Nova refuses to boot the image and returns an appropriate error message to
  the end user. This change builds upon a spec that allows overriding image
  properties at boot time [4].

* Modify the REST API to provide metadata back to the end user for successful
  boot requests. This metadata would include the signing certificate ownership
  information and a base64 encoding of the signature. The user can use an out-
  of-band mechanism to manually verify that the encoded version of the
  signature matches the expected signature.

The first approach is preferred since it may be fully automated whereas the
second approach requires manual verification by the end user.

The certificate references will be used to access the certificates from a key
manager through the interface provided by Castellan.

Alternatives
------------

An alternative to signing the image's data directly is to support signatures
which are created by signing a hash of the image data. This introduces
unnecessary complexity to the feature by requiring an additonal hashing stage
and an additional metadata option. Due to the Glance community's performance
concerns associated with hashing image data, we initially pursued an
implementation which produced the signature by signing an MD5 checksum which
was already computed by Glance. This approach was rejected by the Nova
community due to the security weaknesses of MD5 and the unnecessary complexity
of performing a hashing operation twice and maintaining information about both
hash algorithms.

An alternative to using pyca/cryptography for the hashing and signing
functionality is to use PyCrypto. We are electing to use pyca/cryptography
based on both the shift away from PyCrypto in OpenStack's requirements and the
recommendations of cryptographers reviewing the accompanying Glance spec [5].

An alternative to using certificates for signing and signature verification
would be to use a public key. However, this approach presents the significant
weakness that an attacker could generate their own public key in the key
manager, use this to sign a tampered image, and pass the reference to their
public key to Nova along with their signed image. Alternatively, the use of
certificates provides a means of attributing such attacks to the certificate
owner, and follows common cryptographic standards by placing the root of trust
at the certificate authority.

An alternative to using the verify_glance_signatures configuration flag to
specify that Nova should perform image signature verification is to use
"trusted" flavors to specify that individual instances should be created from
signed images. The user, when using the Nova CLI to boot an instance, would
specify one of these "trusted" flavors to indicate that image signature
verification should occur as part of the control flow for booting the
instance. This may be added in a later change, but will not be included in the
initial implementation. If added, the trusted flavors option will work
alongside the configuration option approach. In this case, Nova would perform
image signature verification if either the configuration flag is set, or if
the user has specified booting an instance of the "trusted" flavor.

Supporting the untrusted Glance use case requires future modifications to the
REST API as previously described. An alternative to the proposed approach uses
a "sign-the-hash" method for signatures instead of signing the image content
directly. In this case, Nova's REST API can be modified to allow the user to
specify a hash algorithm and expected hash value as part of the boot command.
If the actual hash value does not match, then Nova will not boot the image.
Signing the hash instead of the image directly is useful because hashes are
commonly provided for cloud images and users can obtain these hashes
out-of-band.

Data model impact
-----------------

The accompanying work in Glance introduced additional Glance image properties
necessary for image signing. The initial implementation in Nova will introduce
a configuration flag indicating whether Nova should perform image signature
verification before booting an image. The updated implementation which
includes certificate validation will introduce an addtional configuration flag
for specifying the trusted root certificates.

REST API impact
---------------

A future change will modify the request or response to the boot command. This
change supports the untrusted Glance use cases by giving the user additional
assurance that the desired image has been booted.

Security impact
---------------

Nova currently lacks a mechanism to validate images prior to booting them. The
checksum included with an image protects against accidental modifications but
provides little protection against an adversary with access to Glance or to
the communication network between Nova and Glance. This feature facilitates
the creation of a logical trust boundary between Nova and Glance; this trust
boundary permits the end user to have high assurance that Nova is booting an
image signed by a trusted user.

Although Nova will use certificates to perform this task, the certificates
will be stored by a key manager and accessed via Castellan.

Notifications impact
--------------------

None

Other end user impact
---------------------

If the verification of a signature fails, then Nova will not boot an instance
from the image, and an error message will be logged. The user would then have
to edit the image's metadata through the Glance API, the Nova API, or the
Horizon interface; or reinitiate an upload of the image to Glance with the
correct signature metadata in order to boot the image.

Performance Impact
------------------

This feature will only be used if the verify_glance_signatures configuration
flag is set.

When signature verification occurs there will be latency as a result of
retrieving certificates from the key manager through the Castellan interface.
There will also be CPU overhead associated with hashing the image data and
decrypting a signature using a public key.

Other deployer impact
---------------------

In order to use this feature, a key manager must be deployed and configured.
Additionally, Nova must be configured to use a root certificate which has a
root of trust that can respond to an end user's certificate signing requests.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dane-fichter

Other contributors:
  brianna-poulos
  joel-coffman

Reviewers
---------

Core reviewer(s):
  None

Work Items
----------

The feature will be implemented in the following stages:

* Create standalone signature_utils module which handles interfacing with a
  key manager through Castellan and verifying signatures.

* Add functionality to Nova which calls the standalone module when Nova
  uploads a Glance image and the verify_glance_signatures configuration flag
  is set.

* Add certificate validation functionality to the pyca/cryptography library.

* Add functionality to the signature_utils module which fetches certificate
  chains. Incorporate this method, along with the pyca/cryptography library's
  certificate validation functionality into the signature_utils module's
  functionality for verifying image signatures.

* Amend the initial implementation in Nova to utilize this change by allowing
  Nova to fetch root certificate references and pass them to the image
  signature verification method.

* Implement a REST API change to respond to a successful boot request with
  information relevant to the signing data and/or implement a REST API change
  to allow the end user to specify the expected signature at boot time.


Dependencies
============

The pyca/cryptography library, which is already a Nova requirement, will be
used for hash creation and signature verification. The certificate validation
portion of this change is dependent upon adding certificate validation
functionality to the pyca/cryptography library.

In order to simplify the interaction with the key manager and allow multiple
key manager backends, this feature will use the Castellan library [6]. Since
Castellan currently only supports integration with Barbican, using Castellan
in this feature indirectly requires Barbican. In the future, as Castellan
supports a wider variety of key managers, our feature will require minimal
upkeep to support these key managers; we will simply update Nova's and
Glance's requirements to use the latest Castellan version.


Testing
=======

Unit tests will be sufficient to test the functionality implemented in Nova.
We will need to implement Tempest and functional tests to test the
interoperability of this feature with the accompanying functionality in
Glance.


Documentation Impact
====================

Instructions for how to use this functionality will need to be documented.


References
==========

Cryptography API: https://pypi.python.org/pypi/cryptography/0.2.2

[1] https://review.openstack.org/#/c/252462/
[2] https://en.wikipedia.org/wiki/MD5#Security
[3] https://tools.ietf.org/html/rfc5280#section-6.1
[4] https://review.openstack.org/#/c/230382/
[5] https://review.openstack.org/#/c/177948/
[6] http://git.openstack.org/cgit/openstack/castellan