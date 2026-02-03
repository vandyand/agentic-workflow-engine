"""Cache manager for pre-recorded workflow results."""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


CACHE_DIR = Path(__file__).parent.parent / 'cache'


def get_cache_key(workflow_name: str, query: str) -> str:
    """Generate a cache key from workflow name and query."""
    # Normalize query to filename-safe string
    safe_query = query.lower().replace(' ', '_').replace('-', '_')
    return f"{workflow_name}/{safe_query}.json"


def load_cached_result(workflow_name: str, query: str) -> Optional[Dict[str, Any]]:
    """Load cached result for a workflow/query combination.

    Returns None if no cache exists.
    """
    cache_key = get_cache_key(workflow_name, query)
    cache_path = CACHE_DIR / cache_key

    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_cached_result(workflow_name: str, query: str, result: Dict[str, Any]) -> None:
    """Save a result to cache."""
    cache_key = get_cache_key(workflow_name, query)
    cache_path = CACHE_DIR / cache_key

    # Ensure directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)


def list_cached_queries(workflow_name: str) -> list[str]:
    """List all cached queries for a workflow."""
    workflow_cache_dir = CACHE_DIR / workflow_name
    if not workflow_cache_dir.exists():
        return []

    queries = []
    for f in workflow_cache_dir.glob('*.json'):
        # Convert filename back to query
        query = f.stem.replace('_', ' ')
        queries.append(query)
    return queries


# Preset queries for each workflow
PRESET_QUERIES = {
    'arxiv_search': ['transformer', 'reinforcement learning', 'LLM agents'],
    'wiki_summary': ['generative AI', 'neural networks', 'Alan Turing'],
    'error_recovery': ['normal run', 'simulate failure'],
}


def get_preset_queries(workflow_name: str) -> list[str]:
    """Get preset queries for a workflow."""
    return PRESET_QUERIES.get(workflow_name, [])
