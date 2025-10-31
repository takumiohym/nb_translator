from unittest import TestCase, mock
import os
import json
import asyncio # Added asyncio

from google.cloud import translate
import google.auth

from src.nb_translator import NbTranslator

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

class TestNbTranslator(TestCase):
    @mock.patch('google.auth.default', return_value=(None, 'test-project'))
    @mock.patch('src.nb_translator.TranslationServiceAsyncClient') # Patched the correct path
    def setUp(self, mock_async_translate_client, mock_auth_default): # Renamed for clarity
        self.nb_translator = NbTranslator()
        # self.nb_translator.translate_client is an instance of MagicMock (the return_value of the class mock)
        # So, we configure the translate_text method on this instance.
        self.mock_translate_text_method = mock.AsyncMock() # Python 3.8+
        self.nb_translator.translate_client.translate_text = self.mock_translate_text_method

    def test_split_start_symbols(self):
        nb_translator = self.nb_translator

        # Header: #
        texts = ['# AAA', '## AAA', '### AAA']
        expected = [('# ', 'AAA', ''), ('## ', 'AAA', ''), ('### ', 'AAA', '')]
        self.assertEqual([nb_translator._split_start_symbols(t) for t in texts], expected)

        # Quote: >
        texts = ['> AAA']
        expected = [('> ', 'AAA', '')]
        self.assertEqual([nb_translator._split_start_symbols(t) for t in texts], expected)
        
        # Bullet Points: *, - 
        texts = ['* AAA',' * AAA','  * AAA']
        expected = [('* ', 'AAA', ''),(' * ', 'AAA', ''),('  * ', 'AAA', '')]
        self.assertEqual([nb_translator._split_start_symbols(t) for t in texts], expected)
        
        texts = ['- AAA',' - AAA','  - AAA']
        expected = [('- ', 'AAA', ''),(' - ', 'AAA', ''),('  - ', 'AAA', '')]
        self.assertEqual([nb_translator._split_start_symbols(t) for t in texts], expected)
        
        # Ordered List: 1., 2., ...
        texts = ['1. AAA','2. AAA','100. AAA']
        expected = [('1. ', 'AAA', ''),('2. ', 'AAA', ''),('100. ', 'AAA', '')]
        self.assertEqual([nb_translator._split_start_symbols(t) for t in texts], expected)

        
    def test_split_lines_by_length(self):
        nb_translator = self.nb_translator
        nb_translator.split_by_length = 10

        text = 'a' * 5
        self.assertEqual(nb_translator._split_lines_by_length(text), [text])

        text = 'a' * 10
        self.assertEqual(nb_translator._split_lines_by_length(text), [text])

        text = 'a' * 11
        expected = ['a' * 10, 'a']
        self.assertEqual(nb_translator._split_lines_by_length(text), expected)

    def test_exclude_code_highlight(self):
        nb_translator = self.nb_translator

        text = 'aaa bbb `CCC` ddd `EEE`'
        expected = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        self.assertEqual(nb_translator._exclude_code_highlight(text), expected)

    def test_exclude_image_tag(self):
        nb_translator = self.nb_translator
        nb_translator.image_placeholders = {}

        text = 'aaa bbb ![image_6.png](attachment:image_6.png) ddd'
        expected_text = 'aaa bbb <span translate="no">__IMAGE_PLACEHOLDER_0__</span> ddd'
        expected_placeholders = {'__IMAGE_PLACEHOLDER_0__': '![image_6.png](attachment:image_6.png)'}

        processed_text = nb_translator._exclude_image_tag(text)

        self.assertEqual(processed_text, expected_text)
        self.assertEqual(nb_translator.image_placeholders, expected_placeholders)

    def test_restore_image_tags(self):
        nb_translator = self.nb_translator
        nb_translator.image_placeholders = {'__IMAGE_PLACEHOLDER_0__': '![image_6.png](attachment:image_6.png)'}

        text = 'aaa bbb __IMAGE_PLACEHOLDER_0__ ddd'
        expected = 'aaa bbb ![image_6.png](attachment:image_6.png) ddd'

        self.assertEqual(nb_translator._restore_image_tags(text), expected)

    def test_preprocess(self):
        nb_translator = self.nb_translator

        text = 'aaa bbb `CCC` ddd `EEE`'
        expected = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'

        nb_translator.exclude_inline_code = True
        nb_translator.exclude_url = False
        self.assertEqual(nb_translator._preprocess(text), expected)

        nb_translator.exclude_inline_code = False
        self.assertEqual(nb_translator._preprocess(text), text)

    @ignore_warnings
    def test_translate(self):
        async def run_test():
            nb_translator = self.nb_translator

            # Create a mock response object
            mock_response = mock.Mock()
            mock_translation = mock.Mock()
            mock_translation.translated_text = "Hola"
            mock_response.translations = [mock_translation]

            self.mock_translate_text_method.return_value = mock_response

            nb_translator.project_id = 'test-project'
            nb_translator.region = 'global'
            nb_translator.source_language = 'en'
            nb_translator.target_language = 'es'

            texts = ['Hello']
            expected = ['Hola']
            self.assertEqual(await nb_translator._translate(texts), expected)
        asyncio.run(run_test())

    @ignore_warnings
    def test_translate_batch(self):
        async def run_test():
            nb_translator = self.nb_translator
            nb_translator.split_by_codepoints = 10

            # Mock the _translate method
            async def mock_translate(batch):
                await asyncio.sleep(0.01)  # simulate network latency
                return [f"translated_{t}" for t in batch]

            nb_translator._translate = mock.AsyncMock(side_effect=mock_translate)

            # Test case 1: A batch that is smaller than the limit
            texts = ["a" * 2, "b" * 3, "c" * 4]
            expected = ["translated_" + "a" * 2, "translated_" + "b" * 3, "translated_" + "c" * 4]
            self.assertEqual(await nb_translator._translate_batch(texts), expected)
            self.assertEqual(nb_translator._translate.call_count, 1)

            # Reset the mock for the next test case
            nb_translator._translate.reset_mock()

            # Test case 2: A batch that needs to be split
            texts = ["a" * 5, "b" * 6, "c" * 7]
            expected = ["translated_" + "a" * 5, "translated_" + "b" * 6, "translated_" + "c" * 7]
            self.assertEqual(await nb_translator._translate_batch(texts), expected)
            self.assertEqual(nb_translator._translate.call_count, 3)
        asyncio.run(run_test())
        
    def test_remove_no_translate_tag(self):
        nb_translator = self.nb_translator
        
        text = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        expected = 'aaa bbb `CCC` ddd `EEE`'
        self.assertEqual(nb_translator._remove_no_translate_tag(text), expected)

    def test_fix_markdown_symbols(self):
        nb_translator = self.nb_translator
        
        texts = ['（）', '&#39;aaa&#39;', '&quot;bbb&quot;', '] (']
        expected = ['()', "'aaa'", '"bbb"', '](']
        self.assertEqual([nb_translator._fix_markdown_symbols(t) for t in texts ], expected)
        
    def test_trim_text_format_symbols(self):
        nb_translator = self.nb_translator

        texts = ['* aaa * bbb', '** aaa ** bbb']
        expected = ['*aaa* bbb', '**aaa** bbb']
        self.assertEqual([nb_translator._trim_text_format_symbols(t) for t in texts ], expected)

    def test_trim_inline_math_equation(self):
        nb_translator = self.nb_translator

        texts = ['aaa $ \ hat { Y } $ bbb', 'aaa  \ hat { Y }  bbb']
        expected = ['aaa $\hat{Y}$ bbb', 'aaa  \ hat { Y }  bbb']
        self.assertEqual([nb_translator._trim_inline_math_equation(t) for t in texts ], expected)

    def test_post_process(self):
        nb_translator = self.nb_translator

        text = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        expected = 'aaa bbb `CCC` ddd `EEE`'
        self.assertEqual(nb_translator._postprocess(text), expected)

        texts = ['（）', '&#39;aaa&#39;', '&quot;bbb&quot;', '] (','* aaa * bbb', '** aaa ** bbb']
        expected = ['()', "'aaa'", '"bbb"', '](', '*aaa* bbb', '**aaa** bbb']
        self.assertEqual([nb_translator._postprocess(t) for t in texts ], expected)

    @ignore_warnings
    def test_run(self):
        nb_translator = self.nb_translator

        source_file = 'some.txt'
        target_language = 'ja'
        with self.assertRaises(OSError):
            asyncio.run(nb_translator.run(source_file, to=target_language, project_id="test-project"))

        source_file = 'some.ipynb'
        with self.assertRaises(AttributeError):
            asyncio.run(nb_translator.run(source_file, project_id="test-project"))

        source_file = './tests/sample.ipynb'
        expected_target_file = f'./tests/{target_language}_sample.ipynb'

        # Configure the mock_translate_text_method from setUp for the run test
        mock_run_response = mock.Mock()
        mock_run_translation_item = mock.Mock()
        mock_run_translation_item.translated_text = 'こんにちは世界' # Sample translation
        mock_run_response.translations = [mock_run_translation_item] * 24 # The number of lines to translate in sample.ipynb
        self.mock_translate_text_method.return_value = mock_run_response

        asyncio.run(nb_translator.run(source_file, to=target_language, project_id="test-project"))

        self.assertTrue(os.path.exists(expected_target_file))
        
        with open(source_file, 'r') as f:
            source = json.load(f)

        with open(expected_target_file, 'r') as f:
            target = json.load(f)
        
        # Length of the files should be the same
        self.assertEqual(len(source['cells']),len(target['cells']))

        # Code cell should be the same
        self.assertEqual([c for c in source['cells'] if c['cell_type'] =='code'], 
                         [c for c in target['cells'] if c['cell_type'] =='code'])
        
        os.remove(expected_target_file)
        