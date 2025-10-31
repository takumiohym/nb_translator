import json
import os

def load_notebook(filepath):
    """Loads a Jupyter notebook from the given filepath."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise OSError(f"Source file not found: {filepath}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in source file: {filepath}")

def save_notebook(notebook_content, filepath):
    """Saves a Jupyter notebook to the given filepath."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(notebook_content, f, ensure_ascii=False, indent=4)
    except IOError:
        raise OSError(f"Could not write to target file: {filepath}")
