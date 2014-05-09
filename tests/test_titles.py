# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import glob
import re

import docutils.core
import testtools


class TestTitles(testtools.TestCase):
    def _get_title(self, section_tree):
        section = {
            'subtitles': [],
        }
        for node in section_tree:
            if node.tagname == 'title':
                section['name'] = node.rawsource
            elif node.tagname == 'section':
                subsection = self._get_title(node)
                section['subtitles'].append(subsection['name'])
        return section

    def _get_titles(self, spec):
        titles = {}
        for node in spec:
            if node.tagname == 'section':
                section = self._get_title(node)
                titles[section['name']] = section['subtitles']
        return titles

    def _check_titles(self, fname, titles):
        expected_titles = ('Problem description', 'Proposed change',
                           'Implementation', 'Dependencies',
                           'Testing', 'Documentation Impact',
                           'References')
        self.assertEqual(
            sorted(expected_titles),
            sorted(titles.keys()),
            "Expected titles not found in document %s" % fname)

        proposed = 'Proposed change'
        self.assertIn('Alternatives', titles[proposed])
        self.assertIn('Data model impact', titles[proposed])
        self.assertIn('REST API impact', titles[proposed])
        self.assertIn('Security impact', titles[proposed])
        self.assertIn('Notifications impact', titles[proposed])
        self.assertIn('Other end user impact', titles[proposed])
        self.assertIn('Performance Impact', titles[proposed])
        self.assertIn('Other deployer impact', titles[proposed])
        self.assertIn('Developer impact', titles[proposed])

        impl = 'Implementation'
        self.assertIn('Assignee(s)', titles[impl])
        self.assertIn('Work Items', titles[impl])

    def _check_lines_wrapping(self, tpl, raw):
        for i, line in enumerate(raw.split("\n")):
            if "http://" in line or "https://" in line:
                continue
            self.assertTrue(
                len(line) < 80,
                msg="%s:%d: Line limited to a maximum of 79 characters." %
                (tpl, i+1))

    def _check_no_cr(self, tpl, raw):
        matches = re.findall('\r', raw)
        self.assertEqual(
            len(matches), 0,
            "Found %s literal carriage returns in file %s" %
            (len(matches), tpl))

    def test_template(self):
        files = ['specs/template.rst'] + glob.glob('specs/*/*')
        for filename in files:
            self.assertTrue(filename.endswith(".rst"),
                            "spec's file must uses 'rst' extension.")
            with open(filename) as f:
                data = f.read()

            spec = docutils.core.publish_doctree(data)
            titles = self._get_titles(spec)
            self._check_titles(filename, titles)
            self._check_lines_wrapping(filename, data)
            self._check_no_cr(filename, data)
