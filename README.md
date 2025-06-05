# Jupyter Notebook Translator

This tool leverages the Google Cloud Translation API to translate markdown content within Jupyter Notebook files (.ipynb). It provides a command-line interface (CLI) for easy translation of your notebooks into different languages.

## Installation

To install the `nbtl` command and enable the Cloud Translation API, follow these steps:

1.  **Install the package using pip:**
    ```bash
    pip install git+https://github.com/takumiohym/nb_translator.git
    ```

2.  **Enable the Cloud Translation API:**
    ```bash
    gcloud services enable translate.googleapis.com
    ```
    *(This assumes the `gcloud` command is already set up. See below for details.)*

**Important Note for Non-Google Cloud Environments:**

If you are using this tool outside of a managed Google Cloud notebook environment (e.g., Vertex AI Workbench), you will need to install GCP clients and configure authentication. Please refer to the following documentation:
-   [Cloud Translation API Setup](https://cloud.google.com/translate/docs/setup)
-   [Google Cloud Authentication Getting Started](https://cloud.google.com/docs/authentication/getting-started)


## Usage

The command structure for using `nbtl` is as follows:

```bash
nbtl <source_notebook_file.ipynb> --to <target_language_code> [--target_file <target_notebook_file.ipynb>] [--orig <source_language_code>] [--project_id <your_gcp_project_id>] [--region <gcp_region>]
```

### Command Arguments:

*   `<source_notebook_file.ipynb>`: Path to the input Jupyter Notebook file.
*   `--to <target_language_code>`: Language code to translate the notebook to (e.g., `ja` for Japanese, `es` for Spanish).
*   `[--target_file <target_notebook_file.ipynb>]` (Optional): Path to save the translated notebook. If not provided, a new file will be created with the target language code appended to the original filename (e.g., `notebook_source_en_ja.ipynb`).
*   `[--orig <source_language_code>]` (Optional): Language code of the source notebook. Defaults to `en` (English).
*   `[--project_id <your_gcp_project_id>]` (Optional): Your Google Cloud Project ID.
*   `[--region <gcp_region>]` (Optional): The GCP region for the Translation API.

### Examples:

1.  **Translate an English notebook to Japanese:**
    (Assumes the source language is English by default)
    ```bash
    nbtl notebook_source_en.ipynb --to ja
    ```

2.  **Translate a Spanish notebook to Korean:**
    ```bash
    nbtl notebook_source_es.ipynb --orig es --to ko
    ```

## Development Setup

To set up a development environment and build the package locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/takumiohym/nb_translator.git
    cd nb_translator
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The project uses `setuptools`. Install the package in editable mode along with its dependencies:
    ```bash
    pip install -e .
    ```
    This command installs the package in a way that allows you to make changes to the source code and test them immediately without reinstalling.

4.  **Install build dependencies:**
    Before building the package, ensure you have the necessary tools. `wheel` is required for building wheel packages, `setuptools` for general packaging operations, and `build` for invoking the build process.
    ```bash
    pip install wheel setuptools build
    ```

5.  **Building the package:**
    To build the source distribution and wheel, run the following command. This uses the `build` frontend, which is the current standard for building Python packages.
    ```bash
    python -m build
    ```
    This will create the package files (a `.tar.gz` source archive and a `.whl` wheel file) in the `dist/` directory.

6.  **Install the built package for testing:**
    After building, you can install the package from the generated wheel file to test it:
    ```bash
    pip install dist/nb_translator-0.1.0-py3-none-any.whl
    ```
    *Note: The exact filename of the .whl file depends on the package version. Adjust the command accordingly, or use a glob pattern like `pip install dist/nb_translator-*-py3-none-any.whl` if your shell supports it.*

7.  **Running tests:**
    To run the tests, navigate to the root directory of the project and use the following command:
    ```bash
    python -m unittest discover tests
    ```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## References

This tool uses the Google Cloud Translation API. Please review the following documentation to understand its costs and limitations:

-   [Cloud Translation API Pricing](https://cloud.google.com/translate/pricing)
-   [Cloud Translation API Quotas](https://cloud.google.com/translate/quotas)
-   [Supported Language Codes](https://cloud.google.com/translate/docs/languages)
