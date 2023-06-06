"""ElasticSearch Storage interface."""
from anomaly_detector.storage.storage_attribute import ESStorageAttribute
import datetime
import pandas
from pandas.io.json import json_normalize
from elasticsearch5 import Elasticsearch, helpers
import json
import os
import urllib3
from anomaly_detector.storage.storage_sink import StorageSink
from anomaly_detector.storage.storage_source import StorageSource
import logging
from anomaly_detector.storage.storage import DataCleaner

_LOGGER = logging.getLogger(__name__)


class ESStorage:
    """Elasticsearch storage backend."""

    NAME = "es"
    _MESSAGE_FIELD_NAME = "_source.message"

    def __init__(self, configuration):
        """Initialize Elasticsearch storage backend."""
        self.config = configuration
        self._connect()

    def _squelch_log_spew(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # eslog = logging.getLogger('elasticsearch')
        # eslog.setLevel(max(eslog.getEffectiveLevel(), logging.DEBUG+1))

    def _connect(self):
        self._squelch_log_spew()
        
        es_args = {}
        if self.config.ES_USER or self.config.ES_PASSWORD:
            es_args["http_auth"] = (self.config.ES_USER, self.config.ES_PASSWORD)
        if len(self.config.ES_CA_PATH) and os.path.isfile(self.config.ES_CA_PATH):
            es_args["ca_certs"] = self.config.ES_CA_PATH
            
        if len(self.config.ES_CERT_DIR) and os.path.isdir(self.config.ES_CERT_DIR):
            _LOGGER.warning(
                "Using cert and key in %s for connection to %s (verify_certs=%s)."
                % (
                    self.config.ES_CERT_DIR,
                    self.config.ES_ENDPOINT,
                    self.config.ES_VERIFY_CERTS,
                )
            )
            es_args["client_cert"] = os.path.join(self.config.ES_CERT_DIR, "es.crt")
            es_args["client_key"] = os.path.join(self.config.ES_CERT_DIR, "es.key")
        else:
            _LOGGER.warning("Conecting to ElasticSearch without authentication.")

        self.es = Elasticsearch(
            self.config.ES_ENDPOINT,
            use_ssl=self.config.ES_USE_SSL,
            verify_certs=self.config.ES_VERIFY_CERTS,
            timeout=60,
            max_retries=2,
            **es_args,
        )

    def _prep_index_name(self, prefix):
        # appends the correct date to the index prefix
        now = datetime.datetime.now()
        date = now.strftime("%Y.%m.%d")
        index = prefix + date
        return index


class ElasticSearchDataSink(StorageSink, DataCleaner, ESStorage):
    """Local storage data sink implementation."""

    NAME = "es.sink"

    def __init__(self, configuration):
        """Initialize local storage backend."""
        self.config = configuration
        self._connect()

    def store_results(self, data):
        """Store results back to ES."""
        index_out = self._prep_index_name(self.config.ES_TARGET_INDEX)

        actions = [{"_index": index_out, "_type": "log", "_source": data[i]} for i in range(len(data))]

        helpers.bulk(self.es, actions, chunk_size=int(len(data) / 4) + 1)


class ElasticSearchDataSource(StorageSource, DataCleaner, ESStorage):
    """Local storage Data source implementation."""

    NAME = "es.source"

    def __init__(self, configuration):
        """Initialize local storage backend."""
        self.config = configuration
        self._connect()

    def retrieve(self, storage_attribute: ESStorageAttribute):
        """Retrieve data from ES."""
        if self.config.ES_INPUT_INDEX_RAW:
            index_in = self.config.ES_INPUT_INDEX_RAW
        else:
            index_in = self._prep_index_name(self.config.ES_INPUT_INDEX)

        query = {
            "sort": {"@timestamp": {"order": "desc"}},
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"analyze_wildcard": True, "query": ""}},
                        {"range": {"@timestamp": {"gte": "now-900s", "lte": "now"}}},
                    ],
                    "must_not": [],
                }
            },
        }
        _LOGGER.info(
            "Reading in max %d log entries in last %d seconds from %s",
            storage_attribute.number_of_entries,
            storage_attribute.time_range,
            self.config.ES_ENDPOINT,
        )

        query["size"] = storage_attribute.number_of_entries
        query["query"]["bool"]["must"][1]["range"]["@timestamp"]["gte"] = "now-%ds" % storage_attribute.time_range
        query["query"]["bool"]["must"][0]["query_string"]["query"] = self.config.ES_QUERY

        es_data = self.es.search(index_in, body=json.dumps(query))
        if (self.config.ES_VERSION < 7 and es_data["hits"]["total"] == 0) or \
                (self.config.ES_VERSION >= 7 and es_data["hits"]["total"]["value"] == 0):
            return pandas.DataFrame(), es_data

        # only use _source sub-dict
        es_data = [x["_source"] for x in es_data["hits"]["hits"]]
        self.format_log(self.config, es_data)

        # most of the log formats at play don't have a message parameter
        for data_line in es_data:
            if "message" not in data_line:
                data_line["message"] = json.dumps(data_line)

        es_data_normalized = pandas.DataFrame(json_normalize(es_data)["message"])

        _LOGGER.info("%d logs loaded in from last %d seconds", len(es_data_normalized), storage_attribute.time_range)

        self._preprocess(es_data_normalized)

        return es_data_normalized, es_data  # bad solution, this is how Entry objects could come in.
