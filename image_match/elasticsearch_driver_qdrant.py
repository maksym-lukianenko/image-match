from __future__ import annotations

import uuid

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from image_match.signature_database_base import SignatureDatabaseBase, normalized_distance


class SignatureQdrant(SignatureDatabaseBase):
    """Image signature storage and search backed by Qdrant vector database.

    Each image is stored as a Qdrant point whose vector is the raw Goldberg
    signature cast to float32.  ANN retrieval via HNSW produces candidates;
    the exact normalized_distance formula (identical to the ES drivers) is
    then applied in Python.  Distances returned are byte-for-byte the same as
    those returned by SignatureES7/SignatureES8.

    Example::

        from qdrant_client import QdrantClient
        from image_match.elasticsearch_driver_qdrant import SignatureQdrant

        client = QdrantClient(url='http://localhost:6333')
        sq = SignatureQdrant(client, collection_name='images')
        sq.ensure_collection()
        sq.add_image('path/to/image.jpg')
        results = sq.search_image('path/to/query.jpg')
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        distance_cutoff: float = 0.45,
        candidates: int = 100,
        **kwargs,
    ) -> None:
        super().__init__(distance_cutoff=distance_cutoff, **kwargs)
        self.client = client
        self.collection_name = collection_name
        self.candidates = candidates

    def ensure_collection(self, vector_size: int = 648) -> None:
        """Create the Qdrant collection if it does not already exist."""
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name='path',
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def insert_single_record(self, rec: dict, refresh_after: bool = False) -> None:
        sig = rec['signature']
        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=str(uuid.uuid4()),
                vector=[float(x) for x in sig],
                payload={
                    'path': rec['path'],
                    'signature': list(sig),
                    'metadata': rec.get('metadata') or {},
                },
            )],
        )

    def search_single_record(self, rec: dict, pre_filter: Filter | None = None) -> list[dict]:
        query_sig = np.array(rec['signature'])
        vector = [float(x) for x in query_sig]

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=self.candidates,
            query_filter=pre_filter,
            with_payload=True,
        )
        hits = response.points

        if not hits:
            return []

        stored_sigs = np.array([hit.payload['signature'] for hit in hits])
        dists = normalized_distance(stored_sigs, query_sig)

        results = []
        for hit, dist in zip(hits, dists):
            if dist < self.distance_cutoff:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'dist': float(dist),
                    'path': hit.payload['path'],
                    'metadata': hit.payload.get('metadata'),
                })
        return results

    def delete_image(self, path: str) -> None:
        """Delete all points whose path matches the given path."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(must=[FieldCondition(key='path', match=MatchValue(value=path))])
            ),
        )

    def delete_duplicates(self, path: str) -> None:
        """Keep only the first point whose path matches; delete the rest."""
        hits, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=[FieldCondition(key='path', match=MatchValue(value=path))]),
            with_payload=False,
            limit=1000,
        )
        ids_to_delete = [h.id for h in hits[1:]]
        if ids_to_delete:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=ids_to_delete),
            )
