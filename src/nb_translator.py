import json
import re
import os
import fire

from google.cloud import translate
import google.auth
from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash-001"

PROMPT = """
    <instruction>
    Translate the markdown texts from a source language into a target language provided below.
    Texts are provided in a list. Please keep the markdown symbols/structures, newlines, and the list structures precisely, and return in JSON.
    </instruction>

    Source Language : {source_lang}

    Target Language : {target_lang}

    <examples>
    Input:
    ["Descriptions in Source Language"]

    Ouptut:
    ["Descriptions in Target Language"]

    <texts>
    {md_texts}
    </texts>

    """

class NbTranslator():
    
    def _generate(self, md_texts):
        prompt = PROMPT.format(
            md_texts=md_texts, 
            source_lang=self.source_lang, 
            target_lang=self.target_lang
        )
        
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            response_modalities = ["TEXT"],
            response_mime_type='application/json',
            safety_settings = [
                types.SafetySetting(
                  category="HARM_CATEGORY_HATE_SPEECH",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_DANGEROUS_CONTENT",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_HARASSMENT",
                  threshold="OFF")
            ],
        )
        response = self.llm_client.models.generate_content(
            model=MODEL, 
            contents=contents, 
            config=generate_content_config
        )
        
        try:
            response = json.loads(response.text)
        except Exception as e:
            raise Exception("JSON parsing failed.")

        return response

    def run(self,
            source_file,
            target_file=None,
            source_lang='en',
            to=None,
            keep_source=True,
            project_id=None,
            region='us-central1',
            max_retries=5,
           ):

        if os.path.splitext(source_file)[1] != '.ipynb':
            raise OSError('{} is not a jupyter notebook file. Specify .ipynb format file'.format(source_file))

        self.source_file=source_file
        self.source_lang = source_lang
        self.target_lang = to
        self.region = region

        if to is None:
            raise AttributeError('Please specify a target language code. e.g. ja')

        if target_file is None:
            target_file = '{}/{}_{}'.format(os.path.dirname(os.path.realpath(source_file)), self.target_lang, os.path.basename(source_file))

        self.target_file = target_file
        
        
        
        if project_id is None:
            try:
                self.project_id = google.auth.default()[1]
            except:
                raise RuntimeError('Default GCP Project ID is not set. \
                Please specify GCP project ID directly in project_id option. \
                Or, configure it following this document. https://cloud.google.com/docs/authentication/getting-started ')

        self.llm_client = genai.Client(
            vertexai=True,
            project=project_id,
            location=region
        )
        
        with open(source_file, 'r') as f:
            ipynb = json.load(f)

        md_texts = [cell['source'] for cell in ipynb['cells'] if cell['cell_type'] == 'markdown']
        for attempt in range(max_retries):
            try:
                response = self._generate(md_texts)
                assert len(md_texts) == len(response)
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying...")
                else:
                    raise SystemError(f"LLM failed for {max_retries} times")

        md_index = 0
        for i, cell in enumerate(ipynb['cells']):
            if cell['cell_type'] == 'markdown':
                source_text = ipynb['cells'][i]['source']
                ipynb['cells'][i]['source'] = response[md_index]
                if keep_source:
                    cell['source'].append("\n\n<!--\n")
                    cell['source'].extend(source_text)
                    cell['source'].append("\n -->\n")
                md_index+=1

        with open(self.target_file, 'w') as f:
            json.dump(ipynb, f)

        print('{} version of {} is successfully generated as {}'.format(self.target_lang, self.source_file, self.target_file))


def main():
    nb_translater = NbTranslator()
    fire.Fire(nb_translater.run)

if __name__ == '__main__':
    main()
