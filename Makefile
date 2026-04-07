ES7_IMAGE = docker.elastic.co/elasticsearch/elasticsearch:7.17.15
ES8_IMAGE = docker.elastic.co/elasticsearch/elasticsearch:8.13.0
ES_CONTAINER = es-test-local

.PHONY: test test-es7 test-es8 test-unit lint

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
