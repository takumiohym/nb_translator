import json
import re
import os
import fire

from google.cloud import translate
import google.auth

class NbTranslator():

    def __init__(self):
        self.no_translate_start_tag = '<span translate="no">'
        self.no_translate_end_tag = '</span>'
        self.no_translate_start_tag_re = re.compile(self.no_translate_start_tag)
        self.no_translate_end_tag_re = re.compile(self.no_translate_end_tag)

        # Matches lines starting with markdown symbols or only content.
        self.split_start_symbols_re = re.compile(r"([#|>|\-|\*|\d\.|\s]*\s)?(.*)(\n?)")
        self.empty_match_re = re.compile(r"()(.*)(\n?)")

        # For _trim_inline_math_equation
        self.inline_math_re = re.compile(r'\$(.*?)\$')

        self.exclude_block_symbol_pair = {
            '```python': '```', # Python syntax highlight
            '```': '```', # General code block
            '\\begin{equation}': '\\end{equation}' # Math equation block
        }

        self.translate_client = translate.TranslationServiceClient()

    def _split_start_symbols(self, text):
        # Match only if the sentense start with these symbols and space after them.
        # #:head, >:quoto, -:list, \d: ordered list, \s:space
        m = self.split_start_symbols_re.match(text)
        # Ensure that the first group is an empty string if it's None (no markdown symbols)
        # Group 1: Optional markdown prefix (e.g., "# ", "* ", "1. ")
        # Group 2: Main content of the line
        # Group 3: Optional newline character
        groups = m.groups()
        if groups[0] is None:
            return ('', groups[1], groups[2])
        return groups

    def _exclude_code_highlight(self, text):
        # Exclude code highlights in markdown from translation.
        # `(.*?)` will match any characters between two backticks (non-greedy).
        # \g<0> in the replacement refers to the entire match (i.e., `content_inside_backticks`).
        return re.sub(r'`(.*?)`',
                      f'{self.no_translate_start_tag}\\g<0>{self.no_translate_end_tag}',
                      text)

    # TODO
    def _exclude_url(self, text):
        return text

    def _preprocess(self, text):
        if not text:
            return text

        if self.exclude_inline_code: # disabled by default, since enabling this affects on the quality of translation
            text = self._exclude_code_highlight(text)
        if self.exclude_url:
            text = self._exclude_url(text)
        return text

    def _translate(self, text):
        request={
            "parent": f"projects/{self.project_id}/locations/{self.region}",
            "contents": text,
            "mime_type": "text/html",
            "source_language_code": self.source_language,
            "target_language_code": self.target_language,
        }
        target = self.translate_client.translate_text(request=request)
        return target.translations[0].translated_text

    def _remove_no_translate_tag(self, text):
        if not text:
            return text
        text = self.no_translate_start_tag_re.sub('',text)
        text = self.no_translate_end_tag_re.sub('',text)
        return text

    def _fix_markdown_symbols(self, text):
        if not text:
            return text
        # Using a dictionary for replacements can be cleaner if many replacements are planned.
        # For now, direct chaining is fine.
        table = str.maketrans({
            '（': '(',
            '）': ')',
        })
        text = text.translate(table)
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace('] (', '](')
        return text

    def _trim_text_format_symbols(self, text):
        if not text:
            return text
        # * aaa * -> *aaa*
        text = '*'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('*'))])
        # ** aaa ** -> **aaa**
        text = '**'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('**'))])
        return text

    def _trim_inline_math_equation(self, text):
        if not text:
            return text
        return self.inline_math_re.sub(lambda m: '$' + m.group(1).replace(' ', '') + '$', text)

    def _postprocess(self, text):
        if not text: # Added guard clause for the whole postprocess
            return text
        text = self._remove_no_translate_tag(text)
        text = self._fix_markdown_symbols(text)
        text = self._trim_text_format_symbols(text)
        text = self._trim_inline_math_equation(text)
        return text

    def _initialize_settings(self, source_file, target_file, orig_lang, target_lang, project_id, region, exclude_inline_code, exclude_url):
        self.source_file = source_file
        self.source_language = orig_lang
        self.target_language = target_lang
        self.region = region
        self.project_id = project_id
        self.exclude_inline_code = exclude_inline_code
        self.exclude_url = exclude_url

        if target_file is None:
            self.target_file = '{}/{}_{}'.format(os.path.dirname(os.path.realpath(self.source_file)),
                                                self.target_language,
                                                os.path.basename(self.source_file))
        else:
            self.target_file = target_file

        if self.project_id is None:
            try:
                _, self.project_id = google.auth.default()
            except google.auth.exceptions.DefaultCredentialsError: # Be more specific with exception
                raise RuntimeError('Default GCP Project ID is not set. '
                                   'Please specify GCP project ID directly in project_id option, '
                                   'or configure it following https://cloud.google.com/docs/authentication/getting-started')
            except Exception as e: # Catch other potential auth errors
                 raise RuntimeError(f'Could not retrieve default GCP Project ID: {e}. '
                                   'Please specify GCP project ID directly in project_id option, '
                                   'or configure it following https://cloud.google.com/docs/authentication/getting-started')


    def _validate_inputs(self):
        if not self.source_file or os.path.splitext(self.source_file)[1] != '.ipynb':
            raise OSError('Source file must be a .ipynb file. Provided: {}'.format(self.source_file))
        if not self.target_language:
            raise AttributeError('Target language code (e.g., "ja") must be specified.')

    def _load_notebook(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise OSError(f"Source file not found: {filepath}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in source file: {filepath}")


    def _save_notebook(self, notebook_content, filepath):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(notebook_content, f, ensure_ascii=False, indent=4) # Added indent for readability
        except IOError:
            raise OSError(f"Could not write to target file: {filepath}")

    def _translate_notebook_cells(self, ipynb, keep_source):
        for cell in ipynb.get('cells', []):
            if cell.get('cell_type') == "markdown":
                skip_translation_block = False
                current_block_end_symbol = None
                original_source_lines = cell.get('source', []).copy()
                translated_source_lines = []

                for line_content in original_source_lines:
                    stripped_line = line_content.strip()

                    if not skip_translation_block and stripped_line in self.exclude_block_symbol_pair:
                        skip_translation_block = True
                        current_block_end_symbol = self.exclude_block_symbol_pair[stripped_line]
                        translated_source_lines.append(line_content)
                    elif skip_translation_block:
                        if stripped_line == current_block_end_symbol:
                            skip_translation_block = False
                            current_block_end_symbol = None
                        translated_source_lines.append(line_content)
                    else:
                        preprocessed_line = self._preprocess(line_content)
                        prefix, content_to_translate, suffix = self._split_start_symbols(preprocessed_line)

                        translated_content = ''
                        if content_to_translate:
                            translated_content = self._translate([content_to_translate])
                            translated_content = self._postprocess(translated_content)

                        # Ensure proper spacing for suffix, especially newline
                        final_suffix = ('  ' + suffix) if suffix.strip() == '\n' else suffix
                        if suffix.strip() == '\n' and not translated_content.endswith('\n') and not prefix.endswith('\n'):
                             # Add double space for markdown line break if original line ended with newline and translated doesn't
                             # and it's not a list item or header that might already handle spacing.
                             if not (prefix.strip().endswith('-') or prefix.strip().endswith('*') or prefix.strip().startswith('#')):
                                 final_suffix = '  \n' # Ensure markdown newline if required
                             else:
                                 final_suffix = suffix

                        final_line = prefix + re.sub(r"\s?/\s?", "/", translated_content) + final_suffix
                        translated_source_lines.append(final_line)

                cell['source'] = translated_source_lines
                if keep_source:
                    cell['source'].append("\n\n<!--\n")
                    cell['source'].extend(original_source_lines) # Append original lines
                    cell['source'].append("\n -->\n")
        return ipynb

    def run(self,
            source_file,
            target_file=None,
            orig='en',
            to=None,
            keep_source=True,
            project_id=None,
            region='global',
            exclude_inline_code=False,
            exclude_url=False):

        self._initialize_settings(source_file, target_file, orig, to, project_id, region, exclude_inline_code, exclude_url)
        self._validate_inputs()
        
        notebook_content = self._load_notebook(self.source_file)
        translated_notebook_content = self._translate_notebook_cells(notebook_content, keep_source)
        self._save_notebook(translated_notebook_content, self.target_file)

        print('{} version of {} is successfully generated as {}'.format(self.target_language, self.source_file, self.target_file))

def main():
    nb_translater = NbTranslator()
    fire.Fire(nb_translater.run)

if __name__ == '__main__':
    main()
