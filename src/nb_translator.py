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

        self.exclude_block_symbol_pair = {
            '```python': '```', # Python syntax highlight
            '```': '```', # General code block
            '\\begin{equation}': '\\end{equation}' # Math equation block
        }

        self.translate_client = translate.TranslationServiceClient()

    def _split_start_symbols(self, text):
        # Match only if the sentense start with these symbols and space after it.
        # #:head, >:quoto, -:list, \d: ordered list, \s:space
        m = re.match("([#|>|\-|\*|\d\.|\s]*\s)(.*)(\n?)", text)

        if m:
            return m.groups()
        else:
            return re.match("()(.*)(\n?)", text).groups()

    def _exclude_code_highlight(self, text):
        return ''.join([t.replace('`', f'{self.no_translate_start_tag}`') \
                        if i%4==1 else t.replace('`', f'`{self.no_translate_end_tag}') \
                        if i%4==3 else t for i, t in enumerate(re.split('(`)',text))])

    # TODO
    def _exclude_url(self, text):
        return text

    def _preprocess(self, text):
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
        text = re.sub(re.compile(self.no_translate_start_tag),'',text)
        text = re.sub(re.compile(self.no_translate_end_tag),'',text)
        return text

    def _fix_markdown_symbols(self, text):
        table = str.maketrans({
            '（': '(',
            '）': ')',
        })
        text = text.translate(table)
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace('] (', '](')
        return text

    def _squish_text_format_symbols(self, text):
        # * aaa * -> *aaa*
        text = '*'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('*'))])
        # ** aaa ** -> **aaa**
        text = '**'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('**'))])
        return text

    def _squish_inline_math_equation(self, text):
        return '$'.join([s.replace(' ','') if i%2==1 else s for i,s in enumerate(text.split('$'))] )

    def _postprocess(self, text):
        text = self._remove_no_translate_tag(text)
        text = self._fix_markdown_symbols(text)
        text = self._squish_text_format_symbols(text)
        text = self._squish_inline_math_equation(text)
        return text

    def run(self, source_file, target_file=None, source_language='en', target_language=None, project_id=None, region='global', exclude_inline_code=False, exclude_url=False):
        if os.path.splitext(source_file)[1] != '.ipynb':
            raise NameError('{} is not jupyter notebook file. Specify .ipynb format file'.format(source_file))
        self.source_file=source_file

        if target_file is None:
            target_file = '{}/{}_{}'.format(os.path.dirname(os.path.realpath(source_file)), target_language, os.path.basename(source_file))
        self.target_file = target_file

        if target_language is None:
            raise TypeError('Please specify target language code. e.g. ja')

        self.source_language = source_language
        self.target_language = target_language
        self.region = region
        
        if project_id is None:
            try:
                self.project_id = google.auth.default()[1]
            except:
                raise RuntimeError('Default GCP Project ID is not set. \
                Please specify GCP project ID directly in project_id option. \
                Or configure following this document. https://cloud.google.com/docs/authentication/getting-started ')

        self.exclude_inline_code = exclude_inline_code
        self.exclude_url = exclude_url

        with open(source_file, 'r') as f:
            ipynb = json.load(f)

        for i, c in enumerate(ipynb['cells']):
            if c['cell_type']=="markdown":
                skip = False
                end_with = None
                for j, s in enumerate(c['source']):
                    if not skip and s.strip() in self.exclude_block_symbol_pair.keys():
                        ipynb['cells'][i]['source'][j] = s
                        skip = True
                        end_with = self.exclude_block_symbol_pair[s.strip()]
                    elif skip:
                        ipynb['cells'][i]['source'][j] = s
                        if s.strip() == end_with:
                            skip = False
                            end_with = None
                    else:
                        sp = self._preprocess(s)
                        sh = self._split_start_symbols(sp)
                        if sh[1]:
                            target = self._translate([sh[1]])
                        else:
                            target = ''
                        # postprocess
                        target = self._postprocess(target)
                        target_finalized = sh[0] + re.sub("\s?/\s?", "/", target) + ('  ' + sh[2] if sh[2] else '')
                        ipynb['cells'][i]['source'][j] = target_finalized

        with open(target_file, 'w') as f:
            json.dump(ipynb, f)

        print('{} version of {} is successfully generated as {}'.format(target_language, source_file, target_file))


def main():
    nb_translater = NbTranslator()
    fire.Fire(nb_translater.run)

if __name__ == '__main__':
    main()
