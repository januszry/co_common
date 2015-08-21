#!/usr/bin/env python3
# @author Ruoyu Zeng

"""
Tools to generate restructedText
"""
import logging


class RestructuredTextGenerator(object):

    """A set of class methods to generate restructured text string.

    I only implemented most common rst elements, no embedding."""
    SECTION_HEAD_MARKERS = ['=', '-', '~', '+', '^']

    def __init__(self):
        self._max_section_header_level = 0
        self._logger = logging.getLogger(__name__)
        self._body = ""
        self._explicit_links = {}

    def __str__(self):
        return self._body + self.format_marks()

    def add(self, elem, *args, **kwargs):
        """Add rst element to body.

        :param elem: element type
        :param args: positional arguments for elem
        :param kwargs: keyword arguments for elem"""
        self._body += getattr(self, elem)(*args, **kwargs)

    def end_of_block(self):
        """Just two new line."""
        return '\n\n'

    def format_marks(self):
        result = []
        for mark, link in self._explicit_links.items():
            result.append('.. _{}: {}'.format(mark, link))
        return '\n' + self._block('', *result)

    def option(self, name, text, indent=0):
        """An option of a element."""
        return "\n{}:{}: {}\n\n".format(' ' * indent, name, text)

    def text_block(self, text):
        """A block of plain text."""
        return '\n' + text + '\n\n'

    def transition(self):
        """Transitions separate elements.

        Transition in rst is a hozizontal line of
            4 or more repeated punctuation chars,
        with blank lines before and after.
        See http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html
            #transitions"""
        return '\n\n----\n\n'

    def section_header(self, level, text):
        """Section header is single line text with section_header_markers under it.

        The marker should be at least as long as the text
        >>> print(RestructuredTextGenerator().transition())"""
        length = max(10, len(text))
        if level >= len(self.SECTION_HEAD_MARKERS):
            self._logger.warning("No available markers for level %s", level)
            return
        if level <= self._max_section_header_level:
            if level == self._max_section_header_level:
                self._max_section_header_level += 1
            return '{}\n{}\n'.format(
                text, self.SECTION_HEAD_MARKERS[level] * length)
        else:
            self._logger.warning(
                "Level %s not reached til now [%s]",
                level, self._max_section_header_level)

    def italic(self, text):
        """Italic is inline markup *text*."""
        if not isinstance(text, str):
            self._logger.warning(
                "Only str is supported for <text>, %s is not", text)
            return
        return ' *' + text + '* '

    def bold(self, text):
        """Bold is inline markup **text**."""
        return ' **' + text + '** '

    def inline_code(self, text):
        """Inline-code is inline markup ``text``."""
        if not isinstance(text, str):
            self._logger.warning(
                "Only str is supported for <text>, %s is not", text)
            return
        return ' ``' + text + '`` '

    def quote(self, text):
        """Quotes are solely indented text, line-breaks are ignored."""
        if not isinstance(text, str):
            self._logger.warning(
                "Only str is supported for <text>, %s is not", text)
            return
        return '\t' + text + '\n'

    def definition(self, title, content):
        """Definition is a title followed by description."""
        return title + '\n' + '\t' + content + '\n\n'

    def _block(self, marker, *list_of_text):
        if not all(map(lambda x: isinstance(x, str), list_of_text)):
            self._logger.warning(
                "Only str is supported for <text>, %s is not", list_of_text)
            return
        return '\n' + ('\n' + marker).join([''] + list(list_of_text)) + '\n\n'

    def bulleted_list(self, *list_of_text):
        """Bulleted lists are not numbered."""
        return self._block('* ', *list_of_text)

    def numbered_list(self, *list_of_text):
        """Numbered lists are numbered."""
        return self._block('#. ', *list_of_text)

    def line_block(self, *list_of_text):
        """Line blocks are a way of preserving line blocks."""
        return self._block('| ', *list_of_text)

    def source_code(self, *list_of_text):
        """Source code is a block preserving line blocks."""
        return '::' + self._block('\t', *list_of_text)

    def table(self, header, *rows):
        """Simple table, all row-span == 1, col-span == 1.

        * header can be None
        * body can be empty
        * every cell must be provided"""
        if header:
            length = len(header)
        elif not rows:
            self._logger.warning(
                "Empty table with empty header and empty body")
            return
        else:
            length = len(rows[0])
        for row in rows:
            if len(row) != length:
                self._logger.warning("All rows must be with the same length")
                return
        # OK, the table is valid, get cell min length
        col_length = [0] * length
        if header:
            for i, cell in enumerate(header):
                if len(str(cell)) > col_length[i]:
                    col_length[i] = len(str(cell))
        for row in rows:
            for i, cell in enumerate(row):
                if len(str(cell)) > col_length[i]:
                    col_length[i] = len(str(cell))
        result = []

        separate_line_normal = '+'
        for i in range(length):
            separate_line_normal += '-' * (col_length[i] + 2) + '+'
        separate_line_header = '+'
        for i in range(length):
            separate_line_header += '=' * (col_length[i] + 2) + '+'
        # Write first line
        result.append(separate_line_normal)
        if header:
            line = '|'
            for i, cell in enumerate(header):
                line += ' {:{}} |'.format(cell, col_length[i])
            result.append(line)
            result.append(separate_line_header)
        for row in rows:
            line = '|'
            for i, cell in enumerate(row):
                line += ' {:{}} |'.format(cell, col_length[i])
            result.append(line)
            result.append(separate_line_normal)

        return self._block('', *result)

    def inline_hyperlink(self, text, link):
        """A hyperlink to web location."""
        return ' `{} <{}>`_ '.format(text, link)

    def explicit_link(self, mark, link=None):
        """Separated mark and link.

        If link is not None,
            the link and mark will be in self._explicit_links."""
        t = ' `{}`_ '.format(mark)
        if link is not None and link.strip():
            self._explicit_links[mark] = link.strip()
        return t
