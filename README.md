nb_translator
===========

This is a tool to translate markdown descriptions in jupyter notebook files using Google Cloud Translation API.

Installation
-------

Install the `nbtl` command, and enable the Cloud Translation API.

```
pip install git+https://github.com/takumiohym/nb_translator.git
gcloud services enable translate.googleapis.com
```

If you are using this tool outside of the managed Google Cloud notebook envieronment (e.g. Vertex AI Workbench) please install gcp clients and configure the authentication following these documents.
- https://cloud.google.com/translate/docs/setup
- https://cloud.google.com/docs/authentication/getting-started


Usage
-----

```
nbtl <source notebook file> --to <target language code>
[--target_file <target notebook file>] \
[--orig <source language code>] \
[--project_id <your GCP project id>] \
[--region <gcp region>]
```

Examples
-----

Translate English Notebook file into Japanese (source language is `en` by default)

```
nbtl notebook_source_en.ipynb --to ja
```

Translate Spanish Notebook file into Korean


```
nbtl notebook_source_es.ipynb --orig es --to ko
```

References
-----

This tool uses Google Cloud Translation API. Please read these documents and understand the cost and the limitations.

- Pricing
https://cloud.google.com/translate/pricing

- Quotas
https://cloud.google.com/translate/quotas

- Supported Language Code
https://cloud.google.com/translate/docs/languages
