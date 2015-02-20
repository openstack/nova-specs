..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Nova changes required for standalone EC2 API implementation
===========================================================

https://blueprints.launchpad.net/Nova/+spec/ec2-api

Some of the information required for EC2 API, currently supported by
existing nova's EC2 API implementation is not exposed by public
nova APIs. This spec lists these omissions and provides suggestions
about how to expose them.

Problem description
===================

Existing EC2 API implementation in nova came to a state where it's deprecation
is discussed. A standalone EC2 API project was created as a replacement
(now it resides in stackforge - links at the bottom in References).
It needs to be able to cover the same feature-set as existing solution, for
which it needs to retrieve all of the necessary information through
public APIs of OpenStack services in order to satisfy EC2 API protocol.
Some of the required information is currently not exposed in public APIs.
Existing nova's EC2 API implementation gets it from internal nova interfaces or
directly from the nova DB.
As a result of this the standalone EC2 API service uses direct access to nova
DB as a temporary workaround to fill the gaps.

IMPORTANT: this spec discusses only the properties which are reported by
existing nova's EC2 API and which are lost for external EC2 API
implementation. There is in fact more information which will be eventually
required to be exposed in public APIs for maximum compatibility with AWS EC2,
but this will be a subject for different specs.

Use Cases
----------

1. End User uses fully functional EC2 API protocol to access OpenStack cloud as
the user used to working with AWS.
2. End User needs to access instance metadata service and fetch information
in EC2 metadata compatible format.

Project Priority
-----------------

API v2.1 is a project priority and this is an important microversion to have
in place before the release.

Proposed change
===============

Absent information is of different importance and consists of the following
(novaDB instances table):

1. Reservation-related information:
- reservation_id
- launch_index

2. Network-related information
- hostname

3. Image-related information
- kernel_id
- ramdisk_id

4. Metadata-related information
- user_data

5. Device-related information
- root_device_name
- delete_on_termination (block_device_mapping table)

6. Ephemeral-device-related information (metadata service only)
- List of ephemeral devices (block_device_mapping_table)

All of this information is available in NovaDB at the moment. But not all of
this information probably should reside there.

Almost all of this information can be stored in our external DB and be fully
supported for instances run and handled via EC2 API. So in fact the problem
exists almost only for instances run via nova.

The following is a more detailed description given to the best of our
current knowledge. Also our subjective priorities for exposure of this
information from nova API are given with reasoning (some of those we can
provide without affecting nova):

1. Reservation-related information (reservation_id, launch_index).
Importance: Low.
EC2: Reservation/reservationId
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Reservation.html
EC2: Instance/amiLaunchIndex
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Instance.html

Description:
The reservation ID and launch index are correctly stored and handled by
our external code for instances run via EC2 API. Problem concerns only
instances run directly from nova and in fact only the ones run using
os-multiple-creation API extension. Only then reservation and launch
index start making sense.
Nova itself does not report reservation ID except for creation operation
run with return_reservation_id flag set to True and os-multiple-creation
API extension present.
And launch index is in fact only a number in sequence of started instances
during group start for particular reservation (it's informational only and
it seems won't be missed much).

Solution:
- support it in nova and start reporting this reservation ID and
optionally Launch index as part of extended info.
"os-extended-server-attributes:reservation_id"
"os-extended-server-attributes:launch_index"

2. Network-related information (hostname)
Importance: Low
EC2: Instance/privateDnsName
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Instance.html

Description:
Currently correct hostname is returned by nova for usage with nova-network
only. It doesn't quite work correctly in nova at the moment. Also even for
nova-network based solution there is an option to report IP here instead of
hostname (ec2_private_dns_show_ip option).
Amazon generates this hostname from IP and zone:
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/set-hostname.html

Solution:
- support it in nova and start reporting this reservation ID and
optionally Launch index as part of extended info.
"os-extended-server-attributes:hostname"

3. Image-related information (kernel_id, ramdisk_id)
Importance: Low
EC2: Instance/kernelId
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Instance.html
EC2: Instance/ramdiskId
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Instance.html

Description:
Kernel and Ramdisk seemingly are not much used for instances run by nova
and are not very critical to report.

Solutions:
- support it in nova and start reporting this reservation ID and
optionally Launch index as part of extended info.
"os-extended-server-attributes:kernel_id"
"os-extended-server-attributes:ramdisk_id"

4. Metadata-related information (user_data)
Importance: Low
EC2: InstanceAttribute/userData
http://docs.aws.amazon.com/AWSEC2/latest/
APIReference/API_InstanceAttribute.html

Description:
This is user-specific info which is provided during instance creation and this
functionality works. Current nova's EC2 doesn't allow modification of userdata
so the biggest problem now is that we can't provide read-only access to it
from EC2 APIs without exposure in nova public interfaces. The problem stands
for both main EC2 API service and for EC2 metadata service.
Still user can access from by the nova metadata service url from inside the
instance:
http://169.254.169.254/openstack/userdata

Solutions:
- support it in nova and start reporting this reservation ID and
optionally Launch index as part of extended info.
"os-extended-server-attributes:userdata"

5. Device-related information (root_device_name, delete_on_termination)
Importance: Medium
EC2: Instance/rootDeviceName and rootDeviceType
http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_Instance.html
EC2: EbsInstanceBlockDevice/deleteOnTermination
http://docs.aws.amazon.com/AWSEC2/latest/
APIReference/API_EbsInstanceBlockDevice.html

Description:
Root device name is an informational property but it's the only means at the
moment to determine type of the rootDeviceType. rootDeviceType is EBS if
rootDeviceName can be found in a list of block devices (returned in BDM or
in list taken from cinder). The condition is a bit more complicated but in a
nutshell it's so.
deleteOnTermination is only stored in nova DB in block_device_mapping table
for each block device. And it's the only place to get it from. However,
it can be set even now so the only problem is that we do not report it
properly if we don't use novaDB directly.

Solutions:
- support it in nova and start reporting root_device-name and
delete_on_termination of extended info.
"os-extended-server-attributes:root_device_name".
"os-extended-volumes:volumes_attached" as a second key in the dictionary for
the attached volumes.

6. Ephemeral-device-related information (block_device_mapping_table)
Importance: Low
EC2: block-device-mapping/ephemeralN
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html

Description:
- We can report block devices taken from cinder in metadata, so only the
ephemeral devices list is absent at the moment. However, inside the instance
user can get information about devices from the system.

Solution:
- we suggest to not expose it at the moment

For Kilo all of these extensions are proposed to be added as a microversion to
the v2.1 API. Currently it looks like v2.4 microversion.

The whole list of introduced extensions would look like:
"OS-EXT-SRV-ATTR:reservation_id": "r-00000001"
"OS-EXT-SRV-ATTR:launch_index": 0
"OS-EXT-SRV-ATTR:kernel_id": "a5f474bf81474f9dbbc404d5b2e4e9b3"
"OS-EXT-SRV-ATTR:ramdisk_id": "b5f474bf81474f9dbbc404d5b2e4e9b3"
"OS-EXT-SRV-ATTR:hostname": "fake-hostname"
"OS-EXT-SRV-ATTR:root_device_name": "/dev/vda"
"OS-EXT-SRV-ATTR:userdata": "fake"
"os-extended-volumes:volumes_attached": "{"delete_on_termination": True, ...}"


Alternatives
------------

Some of the alternatives were explained above, however there are 3 general
paths in the short term (Kilo and first version of production standalone
EC2 API afterwards) we can take:

1. Not return any information in question.
2. Store everything in standalone EC2 API DB and provide all the information
for EC2 API run instances and some dummy values for nova-run instances.

All of the alternatives presume cutting direct novaDB access.

Data model impact
-----------------

stackforge/ec2-api brings it's own database.

Changes for novaDB are only the cutting of EC2-specific information not
exposed anymore by nova.
No changes required to expose necessary information in public APIs.

REST API impact
---------------

Depends on taken decisions.

New information exposed by public APIs can be put in some extended attributes
for instance listing like:

"os-extended-server-attributes:reservation_id"
"os-extended-server-attributes:launch_index"
"os-extended-server-attributes:kernel_id"
"os-extended-server-attributes:ramdisk_id"
"os-extended-server-attributes:userdata"
"os-extended-server-attributes:deleteOnTerminationDevices": "volume_id_1,
volume_id_2, ...."

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

Implementation
==============

Assignee(s)
-----------

To expose decided public APIs
it's either stackforge/ec2-api team:

Primary assignee:
  Alexandre Levine (alexandrelevine)

Other contributors:
  Feodor Tersin (ftersin),
  Andrey Pavlov (apavlov-e)

or nova team.

Dependencies
============

None

Testing
=======

Usual Unit and Tempest tests for nova APIs along with new stackfore/ec2-api
tests to check that it helped the initial problem.

Documentation Impact
====================

New APIs documentation

References
==========

The existing stackforge project:
https://github.com/stackforge/ec2-api

EC2 API Standalone service spec and blueprint:
https://blueprints.launchpad.net/nova/+spec/ec2-api
Gerrit topic: https://review.openstack.org/#q,topic:bp/ec2-api,n,z

Related mailing list threads:
http://www.mail-archive.com/openstack-dev@lists.openstack.org/msg44704.html
https://www.mail-archive.com/openstack-dev@lists.openstack.org/msg44548.html

Kilo Design Summit notes:
https://etherpad.openstack.org/p/kilo-nova-summit-unconference


