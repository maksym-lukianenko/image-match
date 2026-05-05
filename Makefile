ES7_IMAGE = docker.elastic.co/elasticsearch/elasticsearch:7.17.15
ES8_IMAGE = docker.elastic.co/elasticsearch/elasticsearch:8.13.0
ES_CONTAINER = es-test-local
QDRANT_IMAGE     = qdrant/qdrant:v1.9.7
QDRANT_CONTAINER = qdrant-test-local

.PHONY: test test-es7 test-es8 test-qdrant test-unit lint

test: test-es7 test-es8

test-unit:
	.venv/bin/pytest tests/test_goldberg.py -v

lint:
	.venv/bin/ruff check .

test-es7:
	@echo "==> Starting Elasticsearch 7..."
	@docker rm -f $(ES_CONTAINER) 2>/dev/null || true
	docker run -d --name $(ES_CONTAINER) -p 9200:9200 \
		-e "discovery.type=single-node" \
		-e "xpack.security.enabled=false" \
		-e "xpack.monitoring.enabled=false" \
		$(ES7_IMAGE)
	@echo "==> Waiting for Elasticsearch 7..."
	@until curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; do sleep 2; done
	@echo "==> Running ES7 tests..."
	.venv/bin/pip install -q -e ".[es7,test]"
	.venv/bin/pytest --ignore=tests/test_elasticsearch_driver_es8.py -v; \
		EXIT=$$?; docker stop $(ES_CONTAINER); docker rm $(ES_CONTAINER); exit $$EXIT

test-es8:
	@echo "==> Starting Elasticsearch 8..."
	@docker rm -f $(ES_CONTAINER) 2>/dev/null || true
	docker run -d --name $(ES_CONTAINER) -p 9200:9200 \
		-e "discovery.type=single-node" \
		-e "xpack.security.enabled=false" \
		$(ES8_IMAGE)
	@echo "==> Waiting for Elasticsearch 8..."
	@until curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; do sleep 2; done
	@echo "==> Running ES8 tests..."
	.venv/bin/pip install -q -e ".[es8,test]"
	.venv/bin/pytest tests/test_goldberg.py tests/test_elasticsearch_driver_es8.py -v; \
		EXIT=$$?; docker stop $(ES_CONTAINER); docker rm $(ES_CONTAINER); exit $$EXIT

test-qdrant:
	@echo "==> Starting Qdrant..."
	@docker rm -f $(QDRANT_CONTAINER) 2>/dev/null || true
	docker run -d --name $(QDRANT_CONTAINER) -p 6333:6333 -p 6334:6334 $(QDRANT_IMAGE)
	@echo "==> Waiting for Qdrant..."
	@until curl -sf http://localhost:6333/healthz > /dev/null 2>&1; do sleep 2; done
	@echo "==> Running Qdrant tests..."
	.venv/bin/pip install -q -e ".[qdrant,test]"
	.venv/bin/pytest tests/test_elasticsearch_driver_qdrant.py -v; \
		EXIT=$$?; docker stop $(QDRANT_CONTAINER); docker rm $(QDRANT_CONTAINER); exit $$EXIT
