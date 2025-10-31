import asyncio
from google.cloud import translate
from google.cloud.translate_v3.services.translation_service import TranslationServiceAsyncClient

class TranslationClient:
    def __init__(self, project_id, region, source_language, target_language):
        self.project_id = project_id
        self.region = region
        self.source_language = source_language
        self.target_language = target_language
        self.client = TranslationServiceAsyncClient()

    async def translate_texts(self, texts):
        """Translates a batch of texts."""
        tasks = []
        batch = []
        total_len = 0
        for text in texts:
            if total_len + len(text) >= 30720:  # GCP codepoint limit
                tasks.append(self._translate_batch(batch))
                batch = [text]
                total_len = len(text)
            else:
                batch.append(text)
                total_len += len(text)
        if batch:
            tasks.append(self._translate_batch(batch))

        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    async def _translate_batch(self, batch):
        """Helper method to translate a single batch of texts."""
        request = {
            "parent": f"projects/{self.project_id}/locations/{self.region}",
            "contents": batch,
            "mime_type": "text/html",
            "source_language_code": self.source_language,
            "target_language_code": self.target_language,
        }
        response = await self.client.translate_text(request=request)
        return [t.translated_text for t in response.translations]
