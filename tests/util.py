from textwrap import dedent

from mock import patch

from docutils.io import StringOutput

from sphinx.builders.text import TextBuilder
from sphinx.application import Sphinx
from sphinx.environment import SphinxFileInput


class MockSphinx(Sphinx):
    '''Patches Sphinx application with MockBuilder'''

    def __init__(self, *args, **kwargs):
        kwargs['warning'] = None
        super(MockSphinx, self).__init__(*args, **kwargs)

    def _init_builder(self, buildername):
        self.builder = MockTestBuilder(self)
        self.emit('builder-inited')

    def _mock_build(self, input_lines):
        '''Mocks return of index.rst'''
        # TODO allow patching in of arbitrary files, not just index.rst
        input_lines = dedent(input_lines)
        with patch.object(SphinxFileInput, 'read') as mock_read:
            mock_read.return_value = input_lines
            self.build(force_all=True)


class MockTestBuilder(TextBuilder):
    '''Saves writer output locally, don't output to disk'''

    def __init__(self, *args, **kwargs):
        self.output = {}
        return super(MockTestBuilder, self).__init__(*args, **kwargs)

    def write_doc(self, docname, doctree):
        self.current_docname = docname
        destination = StringOutput(encoding='utf-8')
        self.writer.write(doctree, destination)
        self.output[docname] = self.writer.output
