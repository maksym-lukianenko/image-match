from datetime import datetime

from image_match._es_base import _SignatureESBase


class SignatureES8(_SignatureESBase):
    """Elasticsearch 8.x driver for image-match.

    Install the client with: pip install image-match[es8]

    Note: Documents are stored without doc_type nesting — the signature
    and all fields are at the root of the document. This is incompatible
    with data stored by SignatureES7.

    Example::

        from elasticsearch import Elasticsearch
        from image_match.elasticsearch_driver_es8 import SignatureES8

        es = Elasticsearch()
        ses = SignatureES8(es)
        ses.add_image('path/to/image.jpg')
        results = ses.search_image('path/to/query.jpg')
    """

    def _get_doc_source(self, hit: dict) -> dict:
        return hit['_source']

    def _search_by_path(self, path: str) -> list:
        return self.es.search(
            query={'match': {'path': path}},
            index=self.index,
        )['hits']['hits']

    def search_single_record(self, rec, pre_filter=None):
        rec.pop('path')
        signature = rec.pop('signature')
        rec.pop('metadata', None)

        should = [{'term': {word: rec[word]}} for word in rec]
        query = {'bool': {'should': should}}
        if pre_filter is not None:
            query['bool']['filter'] = pre_filter

        res = self.es.search(
            index=self.index,
            query=query,
            source_excludes=['simple_word_*'],
            size=self.size,
            timeout=self.timeout,
        )['hits']['hits']

        return self._format_results(res, signature)

    def insert_single_record(self, rec, refresh_after=False):
        rec['timestamp'] = datetime.now()
        self.es.index(
            index=self.index,
            document=rec,
            refresh=refresh_after,
        )
