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
        text = self._exclude_code_highlight(text)
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

        # * aaa * -> *aaa*
        text = '*'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('*'))])
        # ** aaa ** -> **aaa**
        text = '**'.join([t.strip() if i%2==1 else t for i, t in enumerate(text.split('**'))])
        return text

    def _postprocess(self, text):
        text = self._remove_no_translate_tag(text)
        text = self._fix_markdown_symbols(text)
        return text

    def run(self, source_file, target_file=None, source_language='en', target_language='ja', project_id=None, region='global'):
        if os.path.splitext(source_file)[1] != '.ipynb':
            raise OSError('{} is not jupyter notebook file. Specify .ipynb format file'.format(source_file))
        self.source_file=source_file

        if target_file is None:
            target_file = '{}/{}_{}'.format(os.path.dirname(os.path.realpath(source_file)), target_language, os.path.basename(source_file))
        self.target_file = target_file

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

        with open(source_file, 'r') as f:
            ipynb = json.load(f)

        for i, c in enumerate(ipynb['cells']):
            if c['cell_type']=="markdown":
                for j, s in enumerate(c['source']):
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
