"""Server-adapter retrieval pipeline, disabled by default."""
import re
from hybrid_retrieval import FAQVectorIndex, hybrid_candidates, fingerprint
from knowledge_indexing import refresh_index
from retrieval_cache import QueryVectorCache


class RetrievalPipeline:
    def __init__(self, *, workspace, encoder_version, embed, enabled=False, cache=None):
        if not isinstance(workspace, str) or not workspace.strip() or not isinstance(encoder_version, str) or not encoder_version.strip():
            raise ValueError('invalid scope')
        if not callable(embed):
            raise ValueError('trusted encoder required')
        self.workspace = workspace
        self.encoder_version = encoder_version
        self.embed = embed
        self.enabled = enabled is True
        self.cache = cache if isinstance(cache, QueryVectorCache) else None
        self.index = None

    def refresh(self, approved, revision, *, max_new=0, max_bytes=0):
        if not self.enabled:
            return False
        # Clear previous evidence on any failed refresh; never publish a partial index.
        previous, self.index = self.index, None
        if self.cache:
            self.cache.clear()
        self.index = refresh_index(workspace=self.workspace, revision=revision,
                                   encoder=self.encoder_version, approved=approved,
                                   previous=previous, embed=self.embed, enabled=True,
                                   max_new=max_new, max_bytes=max_bytes)
        return self.index is not None

    def select(self, query, approved, legacy, *, revision, authorize_query=None, cacheable=False):
        """Authorize each cache miss before embedding. No raw question is logged.

        Trusted caller must supply an atomic spend reservation callback and reconcile
        provider usage, including errors. This object is not a concurrent service.
        """
        index = self.index
        if not self.enabled or not isinstance(index, FAQVectorIndex) or index.revision != revision:
            return legacy
        if not isinstance(query, str) or not query.strip() or len(query.encode('utf-8')) > 4096:
            return legacy
        if re.search(r'\d|환불|취소|예약|결제|개인정보|전화번호|비밀번호', query):
            return legacy
        try:
            if len(approved) > 500 or {fingerprint(row) for row in approved} != {key for key, _ in index.records}:
                return legacy
            args = dict(workspace=self.workspace, revision=revision, encoder=self.encoder_version,
                        query=query, cacheable=cacheable is True)
            vector = self.cache.get(**args) if self.cache else None
            if vector is None:
                if not callable(authorize_query) or authorize_query(len(query.encode('utf-8'))) is not True:
                    return legacy
                vectors = list(self.embed([query]))
                if len(vectors) != 1 or len(vectors[0]) != index.dimension:
                    return legacy
                vector = vectors[0]
                if self.cache:
                    self.cache.put(**args, vector=vector)
            return hybrid_candidates(query=query, legacy=legacy, approved=approved, index=index,
                                     workspace=self.workspace, revision=revision, encoder=self.encoder_version,
                                     query_vector=vector, enabled=True)
        except Exception:
            return legacy
