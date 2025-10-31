from unittest import TestCase, mock
import os
import json
import asyncio
import re

from src.nb_translator import NbTranslator
from src.text_processor import TextProcessor

import warnings

def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func(self, *args, **kwargs))
            else:
                test_func(self, *args, **kwargs)
    return do_test

class TestTextProcessor(TestCase):
    def setUp(self):
        self.text_processor = TextProcessor()

    def test_split_start_symbols(self):
        texts = ['# AAA', '## AAA', '### AAA']
        expected = [('# ', 'AAA', ''), ('## ', 'AAA', ''), ('### ', 'AAA', '')]
        self.assertEqual([self.text_processor.split_start_symbols(t) for t in texts], expected)

    def test_split_lines_by_length(self):
        self.text_processor.split_by_length = 10
        text = 'a' * 11
        expected = ['a' * 10, 'a']
        self.assertEqual(self.text_processor.split_lines_by_length(text), expected)

    def test_exclude_code_highlight(self):
        text = 'aaa bbb `CCC` ddd `EEE`'
        expected = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        self.assertEqual(self.text_processor._exclude_code_highlight(text), expected)

    def test_exclude_image_tag(self):
        text = 'aaa bbb ![image.png](attachment:image.png) ddd'
        expected_text = 'aaa bbb <span translate="no">__IMAGE_PLACEHOLDER_0__</span> ddd'
        expected_placeholders = {'__IMAGE_PLACEHOLDER_0__': '![image.png](attachment:image.png)'}
        processed_text = self.text_processor._exclude_image_tag(text)
        self.assertEqual(processed_text, expected_text)
        self.assertEqual(self.text_processor.image_placeholders, expected_placeholders)

    def test_restore_image_tags(self):
        self.text_processor.image_placeholders = {'__IMAGE_PLACEHOLDER_0__': '![image.png](attachment:image.png)'}
        text = 'aaa bbb __IMAGE_PLACEHOLDER_0__ ddd'
        expected = 'aaa bbb ![image.png](attachment:image.png) ddd'
        self.assertEqual(self.text_processor._restore_image_tags(text), expected)

    def test_preprocess(self):
        text_processor = TextProcessor(exclude_inline_code=True)
        text = 'aaa `CCC`'
        expected = 'aaa <span translate="no">`CCC`</span>'
        self.assertEqual(text_processor.preprocess(text), expected)

    def test_remove_no_translate_tag(self):
        text = 'aaa <span translate="no">`CCC`</span>'
        expected = 'aaa `CCC`'
        self.assertEqual(self.text_processor._remove_no_translate_tag(text), expected)

    def test_fix_markdown_symbols(self):
        texts = ['（）', '&#39;aaa&#39;']
        expected = ['()', "'aaa'"]
        self.assertEqual([self.text_processor._fix_markdown_symbols(t) for t in texts], expected)
        
    def test_trim_text_format_symbols(self):
        texts = ['* aaa *', '** bbb **']
        expected = ['*aaa*', '**bbb**']
        self.assertEqual([self.text_processor._trim_text_format_symbols(t) for t in texts], expected)

    def test_trim_inline_math_equation(self):
        text = '$ \int x dx $'
        expected = '$\int x dx$'
        self.assertEqual(self.text_processor._trim_inline_math_equation(text), expected)

    def test_postprocess(self):
        text = '<span translate="no">`code`</span>'
        expected = '`code`'
        self.assertEqual(self.text_processor.postprocess(text), expected)

class TestNbTranslator(TestCase):
    @ignore_warnings
    @mock.patch('src.nb_translator.TranslationClient')
    async def test_run(self, MockTranslationClient):
        mock_translator_instance = MockTranslationClient.return_value
        mock_translator_instance.translate_texts = mock.AsyncMock(return_value=['こんにちは世界'] * 24)

        nb_translator = NbTranslator()

        source_file = './tests/sample.ipynb'
        target_language = 'ja'
        expected_target_file = f'./tests/{target_language}_sample.ipynb'

        await nb_translator.run(source_file, target_file=expected_target_file, to=target_language, project_id="test-project")

        self.assertTrue(os.path.exists(expected_target_file))
        os.remove(expected_target_file)

    @ignore_warnings
    @mock.patch('src.nb_translator.TranslationClient')
    async def test_translate_notebook_cells(self, MockTranslationClient):
        mock_translator_instance = MockTranslationClient.return_value
        mock_translator_instance.translate_texts = mock.AsyncMock(return_value=["translated"])

        nb_translator = NbTranslator()
        nb_translator._initialize_settings(
            './tests/sample.ipynb', None, 'en', 'ja', 'test-project', 'global', False, False
        )
        nb_translator.translation_client = mock_translator_instance
        
        texts = ["hello"]
        await nb_translator._translate_notebook_cells(
            {'cells': [{'cell_type': 'markdown', 'source': texts}]}, False
        )
        mock_translator_instance.translate_texts.assert_called_once()
