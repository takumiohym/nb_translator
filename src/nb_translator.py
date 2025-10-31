import os
import fire
import asyncio
import google.auth
import re

from src.notebook_handler import load_notebook, save_notebook
from src.translation_client import TranslationClient
from src.text_processor import TextProcessor

class NbTranslator:
    def __init__(self):
        self.exclude_block_symbol_pair = {
            '```python': '```',
            '```': '```',
            '\\begin{equation}': '\\end{equation}'
        }

    def _initialize_settings(self, source_file, target_file, orig_lang, target_lang, project_id, region, exclude_inline_code, exclude_url):
        self.source_file = source_file
        self.target_language = target_lang

        if target_file is None:
            self.target_file = os.path.join(
                os.path.dirname(os.path.realpath(self.source_file)),
                f"{self.target_language}_{os.path.basename(self.source_file)}"
            )
        else:
            self.target_file = target_file

        if project_id is None:
            try:
                _, project_id = google.auth.default()
            except google.auth.exceptions.DefaultCredentialsError:
                raise RuntimeError('Default GCP Project ID is not set. Please specify it directly.')

        self.translation_client = TranslationClient(project_id, region, orig_lang, target_lang)
        self.text_processor = TextProcessor(exclude_inline_code, exclude_url)

    def _validate_inputs(self):
        if not self.source_file or not self.source_file.endswith('.ipynb'):
            raise OSError(f'Source file must be a .ipynb file. Provided: {self.source_file}')
        if not self.target_language:
            raise AttributeError('Target language code must be specified.')

    async def _translate_notebook_cells(self, ipynb, keep_source):
        lines_to_process_map = {}
        texts_to_translate = []

        for cell_idx, cell in enumerate(ipynb.get('cells', [])):
            if cell.get('cell_type') == "markdown":
                lines_to_process_map[cell_idx] = self._prepare_cell_for_translation(cell, texts_to_translate)

        translated_texts = await self.translation_client.translate_texts(texts_to_translate)
        self._update_cells_with_translations(ipynb, lines_to_process_map, iter(translated_texts), keep_source)

        return ipynb

    def _prepare_cell_for_translation(self, cell, texts_to_translate):
        processed_lines_info = []
        skip_translation_block = False
        current_block_end_symbol = None

        for line_content in cell.get('source', []):
            stripped_line = line_content.strip()
            entry = self._create_translation_entry(line_content)

            if not skip_translation_block and stripped_line in self.exclude_block_symbol_pair:
                skip_translation_block = True
                current_block_end_symbol = self.exclude_block_symbol_pair[stripped_line]
            elif skip_translation_block and stripped_line == current_block_end_symbol:
                skip_translation_block = False
            else:
                self._process_line_for_translation(entry, texts_to_translate)

            processed_lines_info.append(entry)

        return processed_lines_info

    def _create_translation_entry(self, line_content):
        return {'original_line': line_content, 'translate': False, 'prefix': '', 'content_to_translate': [], 'suffix': ''}

    def _process_line_for_translation(self, entry, texts_to_translate):
        preprocessed_line = self.text_processor.preprocess(entry['original_line'])
        prefix, content, suffix = self.text_processor.split_start_symbols(preprocessed_line)

        if content:
            entry.update({'translate': True, 'prefix': prefix, 'suffix': suffix})
            split_content = self.text_processor.split_lines_by_length(content)
            entry['content_to_translate'] = split_content
            texts_to_translate.extend(split_content)

    def _update_cells_with_translations(self, ipynb, lines_to_process_map, translated_texts_iter, keep_source):
        for cell_idx, cell in enumerate(ipynb.get('cells', [])):
            if cell.get('cell_type') == "markdown":
                processed_lines_info = lines_to_process_map.get(cell_idx, [])
                translated_source_lines = self._build_translated_lines(processed_lines_info, translated_texts_iter)

                cell['source'] = translated_source_lines
                if keep_source:
                    original_source = [line_info['original_line'] for line_info in processed_lines_info]
                    cell['source'].extend(["\n\n<!--\n", *original_source, "\n -->\n"])

    def _build_translated_lines(self, processed_lines_info, translated_texts_iter):
        translated_lines = []
        for line_info in processed_lines_info:
            if line_info['translate']:
                translated_content = "".join([next(translated_texts_iter) for _ in line_info['content_to_translate']])
                postprocessed_content = self.text_processor.postprocess(translated_content)
                final_line = f"{line_info['prefix']}{postprocessed_content}{line_info['suffix']}"
                translated_lines.append(final_line)
            else:
                translated_lines.append(line_info['original_line'])
        return translated_lines

    async def run(self, source_file, target_file=None, orig='en', to=None, keep_source=True, project_id=None, region='global', exclude_inline_code=False, exclude_url=False):
        self._initialize_settings(source_file, target_file, orig, to, project_id, region, exclude_inline_code, exclude_url)
        self._validate_inputs()
        
        notebook_content = load_notebook(self.source_file)
        translated_notebook = await self._translate_notebook_cells(notebook_content, keep_source)
        save_notebook(translated_notebook, self.target_file)

        print(f'{self.target_language} version of {self.source_file} is successfully generated as {self.target_file}')

def main():
    fire.Fire(NbTranslator().run)

if __name__ == '__main__':
    main()
