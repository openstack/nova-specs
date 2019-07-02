..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Add ALL-IN operator to extra spec ops
======================================

`https://blueprints.launchpad.net/nova/+spec/add-all-in-list-
operator-to-extra-spec-ops
<https://blueprints.launchpad.net/nova/+spec/add-all-in-list-
operator-to-extra-spec-ops>`_

Allow extra spec to match all values in a list by adding the ALL-IN operator.


Problem description
===================

This blueprint aims to allow querying if ALL of the given values are present
in a list.
Currently there's support for an IN operator that returns True if a given
element is present in a list. There is also an OR operator that
only works for single values.

Example:

Suppose a flavor needs to be placed on a host that has the cpu flags 'aes'
and 'vmx'. As it is today is not possible since the only posibility is to
use the <in> operator. But, as the extra specs is a dict, the flavor
extra-spec key would be the same:

capabilities:cpu_info:features : <in> aes
capabilities:cpu_info:features : <in> vmx

Just one of them will be saved.

something like this is needed:

capabilities:cpu_info:features : <all-in> aes vmx

Proposed change
===============

We need to add the new <all-in> operator and its lambda function to
_op_methods dict in extra_specs_ops.py.

...
'<all-in>': lambda x, y: all(val in x for val in y),
...

Then add a call to this function with a list, instead of with a
string if there are more than one element in the query.


Alternatives
------------

Instead of add the '<all-in>' operator extend/overload the '<in>' operator to
work with a list.

capabilities:cpu_info:features : <in> aes vmx

Seems to be easy to understand but could generate confusion because <in>
operator as it is today, aims to be used to match a substring.

Another possibility is add both <any> and <all> operators. By doing this, we
are using <in> and <or> for single values and the new set of operators for
collections values. But something is missing with this approach,
<all> or <any> what? All elements in a list, all elements are True, or all
elements are equal to a given value.


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

None

Implementation
==============

Add a new lambda function to
nova/scheduler/filter/extra_specs_ops.py _ops_method dict:

'<all-in>': lambda x, y: all(val in x for val in y)

Assignee(s)
-----------

Primary assignee:
  facundo-n-maldonado

Other contributors:
  None

Work Items
----------

Dependencies
============

None

Testing
=======

Unit tests should be added for the new operator.

Documentation Impact
====================

Filter scheduler documentation should be updated with the new operator.

References
==========

None
