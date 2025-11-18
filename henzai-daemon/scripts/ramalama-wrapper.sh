#!/bin/bash
# Ramalama wrapper for henzai - RAG integration
#
# This wrapper conditionally adds --rag flag based on whether
# the RAG database exists and is valid.
#
# NOTE: This is a temporary solution until Ramalama adds runtime RAG API
# See: https://github.com/containers/ramalama/issues/XXX (TODO: update with issue number)
# When API is available, this wrapper can be removed and henzai will use
# the /v1/rag/enable API endpoint instead.

set -e

RAG_DB="$HOME/.local/share/henzai/rag-db"
RAG_METADATA="$RAG_DB/metadata.json"

# Check if RAG database exists and is valid
if [ -d "$RAG_DB" ] && [ -f "$RAG_METADATA" ]; then
    # RAG database exists and has metadata - enable RAG
    exec ramalama serve "$@" --rag "$RAG_DB"
else
    # No RAG database or not yet indexed - run without RAG
    exec ramalama serve "$@"
fi













