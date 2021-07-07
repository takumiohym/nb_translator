from setuptools import setup, find_packages

setup(
    name="nb_translator",
    version="0.1.0",
    author='Takumi Ohyama',
    author_email='takumi10di@gmail.com',
    url='https://github.com/takumiohym/nb_translator',
    packages=find_packages(),
    install_requires=["fire", "google-cloud-translate"],
    entry_points={
        "console_scripts": [
            "translate_nb = src.nb_translator:main",
        ]
    }
)