# Intelligent paste handling for Sublime.
# @author Alex Hunt <https://github.com/huntie>

import sublime, sublime_plugin
import re
import html

class SuperAwesomePasteCommand(sublime_plugin.TextCommand):
    def run(self, edit):

        # Get current document contents
        body = self.view.substr(sublime.Region(0, self.view.size()))
        # Get content that precedes the selection
        preceding_text = body[:self.view.sel()[0].begin()]
        # Get current file type
        file_type = self.view.file_name().split('.')[-1] if isinstance(self.view.file_name(), str) else ''

        def get_clipboard_content():
            clipboard = sublime.get_clipboard()
            if re.search('\n', clipboard):
                return clipboard.strip()
            else:
                return clipboard

        def strip_line_numbers(string):
            # If enough preceding line numbers are found (more than half of all lines)
            if (len(re.findall('\n', string)) > 2 and
                len(re.findall(r'\n[ \t]*\d+\:?', string)) > len(string.splitlines()) / 2 - 2):
                # Remove line number from first line
                string = re.sub(r'^[ \t]*\d+\:?[ \t]*\n?', '', string)

                # If a preceding line number is found on every line
                if len(re.findall(r'\n[ \t]*\d+\:?', string)) > len(string.splitlines()) - 2:
                    # Remove preceding numbers from subsequent lines
                    string = re.sub(r'\n[ \t]*\d+\:?', '\n', string)
                else:
                    # Remove preceding numbers and extra lines from subsequent lines
                    string = re.sub(r'\n[ \t]*\d+\:?', '', string)

            return string

        def split_or_merge_lines(string):
            # If there existing semicolon-separated lines on the page
            if len(re.findall(r';[ \t]*\n', body)) > 1:
                # Split lines with multiple phrases by semicolons
                string = re.sub(r';[ \t]*(\w)', r';\n\1', string)

            # If the file content precedes with a quote
            if re.search(r'[\'\"][ \t]*$', preceding_text):
                # Merge lines separated by semicolons
                string = re.sub(r';[ \t]*\n[ \t]*(\w)', r'; \1', string)

            return string

        def normalise_line_endings(string):
            line_endings = self.view.settings().get('default_line_ending')

            # Reset line ending character
            string = string.replace('\r\n', '\n').replace('\r', '\n')
            # Strip trailing whitespace
            string = re.sub(r'[ \t]*\n', '\n', string)

            # Apply line endings of the current file
            if line_endings == 'windows':
                string = string.replace('\n', '\r\n')
            elif line_endings == 'mac':
                string = string.replace('\n', '\r')

            return string

        def clean_formatting(string):
            if re.search('•', string):
                if re.search(r'md|markdown', file_type):
                    # Convert bullet symbols to markdown list items
                    string = re.sub(r'(^|\n)•\t? ?', '\n+ ', string)
                else:
                    # Strip bullet symbol when pasting in an HTML list item
                    if re.search(r'<li[^<>]*?>[^<>]*$', preceding_text):
                        string = re.sub(r'(^|\n)•\t? ?', '', string)

            return string

        def html_escape(string):
            # When pasting inside a content element
            if re.search(r'<(p|h[1-5]|span|em|strong|small|td)[^<>]*?>[^<>]*$', preceding_text):
                # If there are no tags or existing escaped entities present in the paste content
                if not re.search(r'[<>]|&[^\s]+;', string):
                    # Replace special characters with their HTML entity
                    string = html.escape(string)

            return string

        def format_urls(string):
            if re.search('.', string):
                # Regex to match URLs adapted from Matthew O'Riordan <http://bit.ly/1mlEHm8>
                url = re.compile(r'((([A-Za-z]{3,9}:(?:\/\/)?)'     # Match protocol
                                    '([A-Za-z0-9\.\-]+)'            # domain
                                    '|(?:www\.)'                    # OR www.
                                    '[A-Za-z0-9\.\-]+)'             # domain
                                    '((?:\/[\+~%\/\.\w\-_]*)'       # path
                                    '?\??(?:[\-\+=&;%@\.\w_]*)'     # query string
                                    '#?(?:[\.\!\/\\\w]*))?)')       # anchor

                for this_url, start, protocol, domain, path in re.findall(url, string):
                    if not protocol:
                        if not (re.search(r'\/$', preceding_text) or re.search(r'^\/', string)):
                            # Add a protocol to the start of the url if missing
                            string = string.replace(this_url, 'http://' + this_url)
                    if re.search(r'[A-Z]', this_url):
                        # If any uppercase characters are found, make the URL lowercase
                        string = string.replace(this_url, this_url.lower())

            return string

        def show_message(string):
            if re.search('\n', string):
                sublime.status_message('Pasted {} lines'.format(len(string.splitlines())))
            elif len(string) == 0:
                sublime.status_message('Nothing to paste')
            else:
                sublime.status_message('Pasted {n[0]} character{n[1]}'
                    .format(n = [len(string), 's'] if len(string) != 1 else [1, '']))

        # Assign clipboard contents to paste_content
        paste_content = get_clipboard_content()

        if len(paste_content) > 0:
            # Apply corrections to paste content
            paste_content = strip_line_numbers(paste_content)
            paste_content = normalise_line_endings(paste_content)
            paste_content = split_or_merge_lines(paste_content)
            paste_content = clean_formatting(paste_content)

            if self.view.settings().get('super_awesome_paste.escape_html'):
                paste_content = html_escape(paste_content)

            if self.view.settings().get('super_awesome_paste.format_urls'):
                paste_content = format_urls(paste_content)

            # Make this command a single edit to undo
            self.edit = edit

            for region in self.view.sel():
                # Insert final clipboard content into currently selected regions
                self.view.replace(edit, region, paste_content)
                # Reindent selected regions if pasted content spans multiple lines
                if re.search('\n', paste_content):
                    self.view.run_command('reindent', {'single_line': False})
                # Move caret to the right
                self.view.run_command('move', {'by': 'characters', 'forward': True})

        # Show status bar completion message
        show_message(paste_content)