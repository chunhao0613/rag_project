# Kibana Query Templates

Use these KQL examples against the `rag-app-*` index pattern.

## 1. Trace one request by request_id

```kql
request_id : "abc123def456"
```

## 2. Find all Google provider errors

```kql
provider : "google" and error_type : *
```

## 3. Inspect high latency query events

```kql
event : "query_success" and elapsed_seconds > 3
```

## 4. Find cache clears for a specific model

```kql
event : "embedding_cache_cleared" and model : "embed-multilingual-v3.0"
```

## 5. Filter by service component

```kql
component : "rag_app" and event : "query_error"
```
