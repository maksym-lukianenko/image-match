from abc import abstractmethod

import numpy as np
from elasticsearch import Elasticsearch

from image_match.signature_database_base import SignatureDatabaseBase, normalized_distance


class _SignatureESBase(SignatureDatabaseBase):
    """Private base class for Elasticsearch drivers.

    Subclasses must implement:
        - search_single_record
        - insert_single_record
        - _get_doc_source(hit) -> dict
        - _search_by_path(path) -> list[dict]
    """

    def __init__(self, es: Elasticsearch, index: str = 'images', doc_type: str = 'image',
                 timeout: str = '10s', size: int = 100, *args, **kwargs):
        self.es = es
        self.index = index
        self.doc_type = doc_type
        self.timeout = timeout
        self.size = size
        super().__init__(*args, **kwargs)

    @abstractmethod
    def _get_doc_source(self, hit: dict) -> dict:
        """Extract the document fields from a raw ES hit.

        ES7 stores data nested under doc_type; ES8 stores at root.
        """
        raise NotImplementedError

    @abstractmethod
    def _search_by_path(self, path: str) -> list:
        """Return raw ES hits whose path field matches the given path."""
        raise NotImplementedError

    def _format_results(self, res: list, signature: list) -> list[dict]:
        """Compute distances and format ES hits into result dicts."""
        sigs = np.array([self._get_doc_source(x)['signature'] for x in res])

        if sigs.size == 0:
            return []

        dists = normalized_distance(sigs, np.array(signature))

        formatted_res = []
        for x in res:
            source = self._get_doc_source(x)
            formatted_res.append({
                'id': x['_id'],
                'score': x['_score'],
                'metadata': source.get('metadata'),
                'path': source.get('url', source.get('path')),
            })

        for i, row in enumerate(formatted_res):
            row['dist'] = dists[i]

        return list(filter(lambda y: y['dist'] < self.distance_cutoff, formatted_res))

    def delete_duplicates(self, path: str) -> None:
        """Delete all but one entry whose path matches the given path."""
        hits = self._search_by_path(path)
        matching_ids = [
            hit['_id'] for hit in hits
            if self._get_doc_source(hit).get('path') == path
        ]
        for id_tag in matching_ids[1:]:
            self.es.delete(index=self.index, id=id_tag)
