# Observability Pack

This folder collects the minimal observability artifacts for stages 21-23.

- Prometheus metrics scrape config and alert rules
- Grafana dashboard JSON for the core RAG signals
- ELK ingest pipeline and Kibana query examples
- Alertmanager routing config

The application now exposes Prometheus metrics on `METRICS_PORT` (default `8001`) and emits structured JSON logs to stdout so Filebeat or Logstash can parse them.
