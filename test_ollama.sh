#!/bin/bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: noauth:test-123" \
  -H "X-Forwarded-For: 127.0.0.1" \
  -H "X-RW-Api-Key: test-key" \
  -d '{"query": "Tell me about Algonquin Park", "thread_id": "test-ollama-1"}'
