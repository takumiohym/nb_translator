nb_translator
===========

Translate markdown descriptions in jupyter notebook using Google Cloud Translation API.

Install
-------

```
pip install git+https://github.com/takumiohym/nb_translator.git
```

If you are using notebook environment other than Google Cloud envieronment like AI Platform Notebook, you need to configure the Translation API following these documents.
- https://cloud.google.com/docs/authentication/getting-started
- https://cloud.google.com/translate/docs/setup


Usage
-----

```
translate_nb <source notebook file> --target_language <language code>
[--target_file <target notebook file>] \
[--source_langauge <language code>] \
[--project_id <your GCP project id>] \
[--region <gcp region>]
```

Example
-----

Translate English Notebook file into Japanese (source language is `en` by default)

```
translate_nb notebook_source_en.ipynb --target_language ja
> ja version of .notebook_source_en.ipynb is successfully generated as ja_notebook_source_en.ipynb
```

Translate Spanish Notebook file into Korean


```
translate_nb notebook_source_es.ipynb --source_language es --target_language ko
> ko version of .notebook_source_es.ipynb is successfully generated as ko_notebook_source_es.ipynb
```

Reference
-----

This module is depend on Google Cloud Translation API, so reading these documents beforehand is recommened.

- Pricing (First 500.000 characters per month is free)
https://cloud.google.com/translate/pricing

- Quotas
https://cloud.google.com/translate/quotas

- Supported Language Code
https://cloud.google.com/translate/docs/languages