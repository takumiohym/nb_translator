import json
import re
import os
import fire

from google.cloud import translate
import google.auth

class NbTranslater():
    def __init__(self):
        self.translate_client = translate.TranslationServiceClient()

    @staticmethod
    def _exclude_code_highlight(text):
        return ''.join([t.replace('`', '<span translate="no">`') \
                        if i%4==1 else t.replace('`', r'`</span>') \
                        if i%4==3 else t for i, t in enumerate(re.split('(`)',text))])

    # TODO
    @staticmethod
    def _exclude_url(text):
        return text

    def _exclude_preprocess(self, text):
        _text = self._exclude_code_highlight(text)
        _text = self._exclude_url(_text)
        return _text

    def _translate(self, text):
        return self.translate_client.translate_text(
            request={
                "parent": f"projects/{self.project_id}/locations/{self.region}",
                "contents": text,
                "mime_type": "text/html",
                "source_language_code": self.source_language,
                "target_language_code": self.target_language,
            }).translations[0].translated_text

    def translate(self, source_file, target_file=None, source_language='en', target_language='ja', project_id=None, region='global'):
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
                    sh = re.match("([#|\-|>|\d\.|*|\_|\s]*)(.*)(\n?)", s).groups()
                    if sh[1]:
                        text = self._exclude_preprocess(sh[1])
                        target = re.sub(re.compile('<.*?>'),'', self._translate([text]))
                    else:
                        target = ''
                    # reshape for md symbol
                    target_formatted = target.replace("（", "(").replace("）", ")")
                    target_formatted = target_formatted.replace("&#39;", "'").replace("&quot;", '"').replace('] (', '](')
                    target_formatted = '**'.join([t.strip() if i%2==1 else t for i, t in enumerate(target_formatted.split('**'))])
                    target_formatted = sh[0] + re.sub("\s?/\s?", "/", target_formatted) + ('  ' + sh[2] if sh[2] else '')

                    ipynb['cells'][i]['source'][j] = target_formatted

        with open(target_file, 'w') as f:
            json.dump(ipynb, f)

        print('{} version of {} is successfully generated as {}'.format(target_language, source_file, target_file))


def main():
    nb_translater = NbTranslater()
    fire.Fire(nb_translater.translate)

if __name__ == '__main__':
    main()
