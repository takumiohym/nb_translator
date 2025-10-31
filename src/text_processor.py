import re

class TextProcessor:
    def __init__(self, exclude_inline_code=False, exclude_url=False):
        self.no_translate_start_tag = '<span translate="no">'
        self.no_translate_end_tag = '</span>'
        self.no_translate_start_tag_re = re.compile(self.no_translate_start_tag)
        self.no_translate_end_tag_re = re.compile(self.no_translate_end_tag)
        self.image_placeholders = {}
        self.split_start_symbols_re = re.compile(r"([#|>|\-|\*|\d\.|\s]*\s)?(.*)(\n?)")
        self.inline_math_re = re.compile(r'\$(.*?)\$')
        self.split_by_length = 5000
        self.exclude_inline_code = exclude_inline_code
        self.exclude_url = exclude_url

    def preprocess(self, text):
        if not text:
            return text
        if self.exclude_inline_code:
            text = self._exclude_code_highlight(text)
        if self.exclude_url:
            text = self._exclude_url(text)
        text = self._exclude_image_tag(text)
        return text

    def postprocess(self, text):
        if not text:
            return text
        text = self._remove_no_translate_tag(text)
        text = self._fix_markdown_symbols(text)
        text = self._trim_text_format_symbols(text)
        text = self._trim_inline_math_equation(text)
        text = self._restore_image_tags(text)
        return text

    def _exclude_code_highlight(self, text):
        return re.sub(r'`(.*?)`', f'{self.no_translate_start_tag}\\g<0>{self.no_translate_end_tag}', text)

    def _exclude_url(self, text):
        return text  # Placeholder for URL exclusion logic

    def _exclude_image_tag(self, text):
        def replacer(match):
            placeholder = f"__IMAGE_PLACEHOLDER_{len(self.image_placeholders)}__"
            self.image_placeholders[placeholder] = match.group(0)
            return f'{self.no_translate_start_tag}{placeholder}{self.no_translate_end_tag}'
        return re.sub(r'!\[(.*?)\]\((.*?)\)', replacer, text)

    def _remove_no_translate_tag(self, text):
        text = self.no_translate_start_tag_re.sub('', text)
        text = self.no_translate_end_tag_re.sub('', text)
        return text

    def _fix_markdown_symbols(self, text):
        table = str.maketrans({'（': '(', '）': ')'})
        text = text.translate(table)
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace('] (', '](')
        return text

    def _trim_text_format_symbols(self, text):
        text = '*'.join([t.strip() if i % 2 == 1 else t for i, t in enumerate(text.split('*'))])
        text = '**'.join([t.strip() if i % 2 == 1 else t for i, t in enumerate(text.split('**'))])
        return text

    def _trim_inline_math_equation(self, text):
        return self.inline_math_re.sub(lambda m: '$' + m.group(1).strip() + '$', text)

    def _restore_image_tags(self, text):
        for placeholder, original_tag in self.image_placeholders.items():
            text = text.replace(placeholder, original_tag)
        return text

    def split_start_symbols(self, text):
        m = self.split_start_symbols_re.match(text)
        groups = m.groups()
        if groups[0] is None:
            return ('', groups[1], groups[2])
        return groups

    def split_lines_by_length(self, text):
        if not text or len(text) <= self.split_by_length:
            return [text]
        return [text[i:i + self.split_by_length] for i in range(0, len(text), self.split_by_length)]
