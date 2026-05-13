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
    then applied in Python.  Distances are comparable with SignatureES7/SignatureES8.

    Note: The ``score`` field in search results is the backend's raw relevance
    score (cosine similarity for Qdrant, Lucene score for ES drivers) and is
    not comparable across backends.  Use ``dist`` for cross-backend comparison.

    Example::

        from qdrant_client import QdrantClient
        from image_match.qdrant_driver import SignatureQdrant

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

    def ensure_collection(
        self,
        vector_size: int = 648,
        indexed_fields: dict | None = None,
    ) -> None:
        """Create the Qdrant collection if it does not already exist.

        Args:
            vector_size: Length of the Goldberg signature vector. Must match the
                n_grid used when generating signatures (default n_grid=9 → 648).
            indexed_fields: Optional mapping of payload field path to PayloadSchemaType
                to create payload indexes (e.g. ``{'metadata.tenant_id': PayloadSchemaType.KEYWORD}``).
                Without an index, metadata filters work but fall back to a full
                payload scan, which is slow at scale.  Callers are responsible for
                indexing any metadata keys used in pre_filter queries.
        """
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
            for field_path, schema in (indexed_fields or {}).items():
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_path,
                    field_schema=schema,
                )

    def insert_single_record(self, rec: dict, refresh_after: bool = False) -> None:
        sig = rec['signature']
        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, rec['path'])),
                vector=[float(x) for x in sig],
                payload={
                    'path': rec['path'],
                    # Stored in payload (not retrieved via with_vectors=True) because
                    # Qdrant cosine-normalises vectors at insert time, making the
                    # retrieved vector != original — which would break normalized_distance.
                    'signature': list(sig),
                    **({'metadata': rec['metadata']} if rec.get('metadata') else {}),
                },
            )],
            wait=refresh_after,
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
        path_filter = Filter(must=[FieldCondition(key='path', match=MatchValue(value=path))])
        all_ids = []
        offset = None
        while True:
            hits, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=path_filter,
                with_payload=False,
                limit=1000,
                offset=offset,
            )
            all_ids.extend(h.id for h in hits)
            if offset is None:
                break
        ids_to_delete = all_ids[1:]
        if ids_to_delete:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=ids_to_delete),
            )
