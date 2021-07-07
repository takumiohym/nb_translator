import json
import re
import os
import fire

from google.cloud import translate

translate_client = translate.TranslationServiceClient()

def translate_nb(source_file, target_file=None, source_language='en', target_language='ja', project_id=None, region='global'):
    if os.path.splitext(source_file)[1] != '.ipynb':
        raise OSError('{} is not jupyter notebook file. Specify .ipynb format file'.format(source_file))

    if project_id is None:
        #TODO: Add config function to get DefaultProject ID
        raise RuntimeError('Please specify GCP project ID in project_id option')

    if target_file is None:
        target_file = '{}/{}_{}'.format(os.path.dirname(os.path.realpath(source_file)), target_language, os.path.basename(source_file))


    def _translate(text):
        return translate_client.translate_text(
            request={
                "parent": f"projects/{project_id}/locations/{region}",
                "contents": text,
                "mime_type": "text/html",
                "source_language_code": source_language,
                "target_language_code": target_language,
            }).translations[0].translated_text

    def _exclude_code_highlight(text):
        return ''.join([t.replace('`', '<span translate="no">`') \
                        if i%4==1 else t.replace('`', r'`</span>') \
                        if i%4==3 else t for i, t in enumerate(re.split('(`)',text))])

    # TODO
    def _exclude_url(text):
        return text

    def _exclude_preprocess(text):
        _text = _exclude_code_highlight(text)
        _text = _exclude_url(_text)
        return _text

    with open(source_file, 'r') as f:
        ipynb = json.load(f)

    for i, c in enumerate(ipynb['cells']):
        if c['cell_type']=="markdown":
            for j, s in enumerate(c['source']):
                sh = re.match("([#|\-|>|\d\.|*|\_|\s]*)(.*)(\n?)", s).groups()
                if sh[1]:
                    text = _exclude_preprocess(sh[1])
                    target = re.sub(re.compile('<.*?>'),'', _translate([text]))
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
    fire.Fire(translate_nb)

if __name__ == '__main__':
    main()
