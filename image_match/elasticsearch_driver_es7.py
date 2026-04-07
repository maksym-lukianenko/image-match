from datetime import datetime

from image_match._es_base import _SignatureESBase


class SignatureES7(_SignatureESBase):
    """Elasticsearch 7.x driver for image-match.

    Install the client with: pip install image-match[es7]

    Example::

        from elasticsearch import Elasticsearch
        from image_match.elasticsearch_driver_es7 import SignatureES7

        es = Elasticsearch()
        ses = SignatureES7(es)
        ses.add_image('path/to/image.jpg')
        results = ses.search_image('path/to/query.jpg')
    """

    def _get_doc_source(self, hit: dict) -> dict:
        return hit['_source'][self.doc_type]

    def _search_by_path(self, path: str) -> list:
        return self.es.search(
            body={'query': {'match': {f'{self.doc_type}.path': path}}},
            index=self.index,
        )['hits']['hits']

    def search_single_record(self, rec, pre_filter=None):
        rec.pop('path')
        signature = rec.pop('signature')
        rec.pop('metadata', None)

        should = [
            {'term': {f'{self.doc_type}.{word}': rec[word]}}
            for word in rec
        ]
        body = {
            'query': {'bool': {'should': should}},
            '_source': {'excludes': [f'{self.doc_type}.simple_word_*']},
        }
        if pre_filter is not None:
            body['query']['bool']['filter'] = pre_filter

        res = self.es.search(
            index=self.index,
            body=body,
            size=self.size,
            timeout=self.timeout,
        )['hits']['hits']

        return self._format_results(res, signature)

    def insert_single_record(self, rec, refresh_after=False):
        rec['timestamp'] = datetime.now()
        self.es.index(
            index=self.index,
            body={self.doc_type: rec},
            refresh=refresh_after,
        )
