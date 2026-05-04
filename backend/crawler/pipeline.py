import os
import requests
import logging

logger = logging.getLogger(__name__)

API_URL = os.environ.get("NEPTUNE_API_URL", "http://localhost:8000")
CRAWLER_SECRET = os.environ.get("CRAWLER_SECRET", "dev-secret")
BATCH_SIZE = 50   # send pages in batches of 50 for efficiency

class NeptuneIndexPipeline:
    def __init__(self):
        self.buffer = []

    def process_item(self, item, spider):
        self.buffer.append(dict(item))
        if len(self.buffer) >= BATCH_SIZE:
            self._flush()
        return item

    def close_spider(self, spider):
        # Flush remaining items when spider finishes
        if self.buffer:
            self._flush()
        logger.info(f"NeptuneIndexPipeline: done. Total batches sent.")

    def _flush(self):
        if not self.buffer:
            return
        try:
            resp = requests.post(
                f"{API_URL}/bulk-index",
                json={"documents": self.buffer, "secret": CRAWLER_SECRET},
                timeout=30,
            )
            if resp.status_code == 200:
                logger.info(f"Indexed {len(self.buffer)} pages OK")
            else:
                logger.error(f"Index error {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            logger.error(f"Failed to send batch to API: {e}")
        self.buffer = []