from unittest import TestCase
import os
import json

from google.cloud import translate
import google.auth

from src.nb_translator import NbTranslator

import warnings
def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test

class TestNbTranslator(TestCase):

    def test_split_start_symbols(self):
        nb_translator = NbTranslator()

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

        
    def test_exclude_code_highlight(self):
        nb_translator = NbTranslator()

        text = 'aaa bbb `CCC` ddd `EEE`'
        expected = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        self.assertEqual(nb_translator._exclude_code_highlight(text), expected)

    def test_preprocess(self):
        nb_translator = NbTranslator()

        text = 'aaa bbb `CCC` ddd `EEE`'
        expected = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'

        nb_translator.exclude_inline_code = True
        nb_translator.exclude_url = False
        self.assertEqual(nb_translator._preprocess(text), expected)

        nb_translator.exclude_inline_code = False
        self.assertEqual(nb_translator._preprocess(text), text)

    @ignore_warnings
    def test_translate(self):
        nb_translator = NbTranslator()

        nb_translator.project_id = google.auth.default()[1]
        nb_translator.region = 'global'
        nb_translator.source_language = 'en'
        nb_translator.target_language = 'es'

        text = 'Hello'
        expected = 'Hola'
        self.assertEqual(nb_translator._translate([text]), expected)
        
    def test_remove_no_translate_tag(self):
        nb_translator = NbTranslator()
        
        text = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        expected = 'aaa bbb `CCC` ddd `EEE`'
        self.assertEqual(nb_translator._remove_no_translate_tag(text), expected)

    def test_fix_markdown_symbols(self):
        nb_translator = NbTranslator()
        
        texts = ['（）', '&#39;aaa&#39;', '&quot;bbb&quot;', '] (']
        expected = ['()', "'aaa'", '"bbb"', '](']
        self.assertEqual([nb_translator._fix_markdown_symbols(t) for t in texts ], expected)
        
    def test_trim_text_format_symbols(self):
        nb_translator = NbTranslator()

        texts = ['* aaa * bbb', '** aaa ** bbb']
        expected = ['*aaa* bbb', '**aaa** bbb']
        self.assertEqual([nb_translator._trim_text_format_symbols(t) for t in texts ], expected)

    def test_trim_inline_math_equation(self):
        nb_translator = NbTranslator()

        texts = ['aaa $ \ hat { Y } $ bbb', 'aaa  \ hat { Y }  bbb']
        expected = ['aaa $\hat{Y}$ bbb', 'aaa  \ hat { Y }  bbb']
        self.assertEqual([nb_translator._trim_inline_math_equation(t) for t in texts ], expected)

    def test_post_process(self):
        nb_translator = NbTranslator()

        text = 'aaa bbb <span translate="no">`CCC`</span> ddd <span translate="no">`EEE`</span>'
        expected = 'aaa bbb `CCC` ddd `EEE`'
        self.assertEqual(nb_translator._postprocess(text), expected)

        texts = ['（）', '&#39;aaa&#39;', '&quot;bbb&quot;', '] (','* aaa * bbb', '** aaa ** bbb']
        expected = ['()', "'aaa'", '"bbb"', '](', '*aaa* bbb', '**aaa** bbb']
        self.assertEqual([nb_translator._postprocess(t) for t in texts ], expected)

    @ignore_warnings
    def test_run(self):
        nb_translator = NbTranslator()

        source_file = 'some.txt'
        target_language = 'ja'
        with self.assertRaises(OSError):
            nb_translator.run(source_file, to=target_language)

        source_file = 'some.ipynb'
        with self.assertRaises(AttributeError):
            nb_translator.run(source_file)

        source_file = './tests/sample.ipynb'
        expected_target_file = f'./tests/{target_language}_sample.ipynb'
        nb_translator.run(source_file,to=target_language)

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
        