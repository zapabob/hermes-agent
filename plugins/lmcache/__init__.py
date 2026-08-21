"""LMCache Plugin for Hermes Agent

LMCache integration plugin providing KV cache management capabilities:
- Cache status monitoring
- Cache management operations  
- Optimization suggestions
- Model context length tracking across providers

This plugin follows Hermes Agent plugin conventions:
- Data stored in <hermes_home>/plugin-data/lmcache/
- Uses plugin_storage module for durable state
- Exposes tools via Hermes tool framework
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.plugin_storage import plugin_data_dir, plugin_db

logger = logging.getLogger(__name__)

__all__ = [
    "lmcache_status",
    "lmcache_set_entry",
    "lmcache_get_entry",
    "lmcache_remove_entry",
    "lmcache_record_optimization",
    "lmcache_get_optimization_stats",
    "lmcache_get_model_context_lengths",
    "lmcache_clear_all",
    "lmcache_reset_db",
    "LMCachePlugin",
]


# Plugin data directory: <hermes_home>/plugin-data/lmcache/
PLUGIN_DATA_ROOT = plugin_data_dir("lmcache")


def get_model_context_lengths_for_prompt() -> str:
    """Generate prompt snippet for model context lengths."""
    plugin = get_plugin()
    models = plugin.get_model_context_lengths()
    if not models:
        return ""
    
    lines = ["【モデルコンテキスト長情報】"]
    for m in models:
        provider_str = f" ({m['provider']})" if m.get("provider") else ""
        lines.append(f"- {m['model_name']}{provider_str}: {m['context_length']} tokens")
    lines.append("")
    return "\n".join(lines)


class LMCachePlugin:
    """Main plugin class for LMCache integration."""
    
    def __init__(self) -> None:
        self.name = "lmcache"
        self._db_conn = None
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the plugin data directory exists."""
        PLUGIN_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        logger.debug(f"LMCache plugin data dir: {PLUGIN_DATA_ROOT}")
    
    @property
    def db(self) -> "sqlite3.Connection":
        """Get or create the plugin SQLite database connection."""
        if self._db_conn is None:
            db_path = PLUGIN_DATA_ROOT / "data.db"
            self._db_conn = plugin_db("lmcache", "data.db")
            # Initialize schema
            self._init_schema()
        return self._db_conn
    
    def _init_schema(self) -> None:
        """Initialize the database schema."""
        conn = self.db
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT,
                timestamp REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                ttl INTEGER DEFAULT 300
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS optimization_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT,
                context_length INTEGER,
                ttft_ms REAL,
                throughput REAL,
                provider TEXT,
                timestamp REAL NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_context_lengths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                context_length INTEGER NOT NULL,
                last_updated REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                UNIQUE(model_name, provider)
            )
        """)
        conn.commit()
        logger.info("LMCache plugin schema initialized")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current LMCache cache status."""
        conn = self.db
        rows = conn.execute(
            "SELECT key, value, timestamp FROM cache_status ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        
        return {
            "plugin": self.name,
            "data_dir": str(PLUGIN_DATA_ROOT),
            "entries": len(rows),
            "recent_entries": [
                {"key": row[0], "value": row[1], "timestamp": row[2]}
                for row in rows
            ],
        }
    
    def set_cache_entry(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set a cache entry in the LMCache store."""
        try:
            conn = self.db
            conn.execute(
                "INSERT OR REPLACE INTO cache_status (key, value, ttl) VALUES (?, ?, ?)",
                (key, value, ttl),
            )
            conn.commit()
            logger.debug(f"Set LMCache entry: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set LMCache entry {key}: {e}")
            return False
    
    def get_cache_entry(self, key: str) -> Optional[str]:
        """Get a cache entry by key."""
        try:
            conn = self.db
            row = conn.execute(
                "SELECT value FROM cache_status WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get LMCache entry {key}: {e}")
            return None
    
    def remove_cache_entry(self, key: str) -> bool:
        """Remove a cache entry by key."""
        try:
            conn = self.db
            conn.execute(
                "DELETE FROM cache_status WHERE key = ?", (key,)
            )
            conn.commit()
            logger.debug(f"Removed LMCache entry: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove LMCache entry {key}: {e}")
            return False
    
    def record_optimization(
        self,
        model_name: str,
        context_length: int,
        ttft_ms: float,
        throughput: float,
        provider: str = "",
    ) -> bool:
        """Record optimization statistics."""
        try:
            conn = self.db
            conn.execute(
                """INSERT INTO optimization_stats 
                   (model_name, context_length, ttft_ms, throughput, provider) 
                   VALUES (?, ?, ?, ?, ?)""",
                (model_name, context_length, ttft_ms, throughput, provider),
            )
            # Also update model_context_lengths if context_length changed
            conn.execute(
                """INSERT OR REPLACE INTO model_context_lengths 
                   (model_name, provider, context_length, last_updated) 
                   VALUES (?, ?, ?, ?)""",
                (model_name, provider, context_length, int(time.time())),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record optimization: {e}")
            return False
    
    def get_optimization_stats(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get optimization statistics, optionally filtered by model name."""
        try:
            conn = self.db
            if model_name:
                rows = conn.execute(
                    """SELECT model_name, context_length, ttft_ms, throughput, provider, timestamp 
                       FROM optimization_stats 
                       WHERE model_name = ?
                       ORDER BY timestamp DESC LIMIT 50""",
                    (model_name,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT model_name, context_length, ttft_ms, throughput, provider, timestamp 
                       FROM optimization_stats 
                       ORDER BY timestamp DESC LIMIT 50""",
                ).fetchall()
            
            return [
                {
                    "model_name": row[0],
                    "context_length": row[1],
                    "ttft_ms": row[2],
                    "throughput": row[3],
                    "provider": row[4],
                    "timestamp": row[5],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get optimization stats: {e}")
            return []
    
    def get_model_context_lengths(self) -> List[Dict[str, Any]]:
        """Get all model context lengths by provider."""
        try:
            conn = self.db
            rows = conn.execute(
                """SELECT model_name, provider, context_length, last_updated 
                   FROM model_context_lengths 
                   ORDER BY last_updated DESC LIMIT 100"""
            ).fetchall()
            
            return [
                {
                    "model_name": row[0],
                    "provider": row[1],
                    "context_length": row[2],
                    "last_updated": row[3],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get model context lengths: {e}")
            return []
    
    def clear_all(self) -> bool:
        """Clear all cache entries."""
        try:
            conn = self.db
            conn.execute("DELETE FROM cache_status")
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear all cache entries: {e}")
            return False
    
    def reset_db(self) -> bool:
        """Reset the entire database."""
        try:
            db_path = PLUGIN_DATA_ROOT / "data.db"
            
            if self._db_conn is not None:
                try:
                    self._db_conn.close()
                except Exception:
                    pass
                self._db_conn = None
            
            if db_path.exists():
                db_path.unlink()
                logger.info(f"Removed LMCache database: {db_path}")
            
            # Re-initialize schema
            self._init_schema()
            
            return True
        except Exception as e:
            logger.error(f"Failed to reset LMCache database: {e}")
            return False


# Singleton instance
_plugin_instance: Optional[LMCachePlugin] = None


def get_plugin() -> LMCachePlugin:
    """Get the singleton LMCache plugin instance."""
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = LMCachePlugin()
    return _plugin_instance


# Tool handler functions

def lmcache_status(_args: Optional[Dict[str, Any]] = None) -> str:
    """Tool: Get LMCache status."""
    plugin = get_plugin()
    status = plugin.get_status()
    return json.dumps(status)


def lmcache_set_entry(args: Dict[str, Any]) -> str:
    """Tool: Set a cache entry."""
    key = args.get("key", "")
    value = args.get("value", "")
    ttl = args.get("ttl", 300)
    
    plugin = get_plugin()
    success = plugin.set_cache_entry(key, value, ttl)
    
    result = {"success": success, "key": key}
    if success:
        result["message"] = f"Cache entry '{key}' set successfully"
    else:
        result["message"] = f"Failed to set cache entry '{key}'"
    
    return json.dumps(result)


def lmcache_get_entry(args: Dict[str, Any]) -> str:
    """Tool: Get a cache entry."""
    key = args.get("key", "")
    
    plugin = get_plugin()
    value = plugin.get_cache_entry(key)
    
    result = {"success": value is not None, "key": key}
    if value is not None:
        result["value"] = value
        result["message"] = f"Found cache entry: {key}"
    else:
        result["message"] = f"Cache entry not found: {key}"
    
    return json.dumps(result)


def lmcache_remove_entry(args: Dict[str, Any]) -> str:
    """Tool: Remove a cache entry."""
    key = args.get("key", "")
    
    plugin = get_plugin()
    success = plugin.remove_cache_entry(key)
    
    result = {"success": success, "key": key}
    if success:
        result["message"] = f"Cache entry '{key}' removed successfully"
    else:
        result["message"] = f"Failed to remove cache entry '{key}'"
    
    return json.dumps(result)


def lmcache_record_optimization(args: Dict[str, Any]) -> str:
    """Tool: Record optimization statistics."""
    model_name = args.get("model_name", "")
    context_length = args.get("context_length", 0)
    ttft_ms = args.get("ttft_ms", 0.0)
    throughput = args.get("throughput", 0.0)
    provider = args.get("provider", "")
    
    plugin = get_plugin()
    success = plugin.record_optimization(model_name, context_length, ttft_ms, throughput, provider)
    
    result = {"success": success, "model_name": model_name}
    if success:
        result["message"] = f"Optimization recorded for {model_name}"
    else:
        result["message"] = f"Failed to record optimization for {model_name}"
    
    return json.dumps(result)


def lmcache_get_optimization_stats(args: Optional[Dict[str, Any]] = None) -> str:
    """Tool: Get optimization statistics."""
    model_name = args.get("model_name") if args else None
    
    plugin = get_plugin()
    stats = plugin.get_optimization_stats(model_name)
    
    result = {"success": True, "stats": stats}
    result["message"] = f"Retrieved {len(stats)} optimization records"
    
    return json.dumps(result)


def lmcache_get_model_context_lengths(args: Optional[Dict[str, Any]] = None) -> str:
    """Tool: Get model context lengths by provider.
    
    Returns model name, provider, and context length for all tracked models.
    Useful for tracking context limits across different AI providers (OpenAI, NVIDIA, 
    Nous, custom local, etc.).
    """
    plugin = get_plugin()
    models = plugin.get_model_context_lengths()
    
    result = {"success": True, "models": models}
    result["message"] = f"Retrieved {len(models)} model context length records"
    
    return json.dumps(result)


def lmcache_clear_all(args: Optional[Dict[str, Any]] = None) -> str:
    """Tool: Clear all cache entries."""
    plugin = get_plugin()
    success = plugin.clear_all()
    
    result = {"success": success, "message": "All cache entries cleared" if success else "Failed to clear cache"}
    return json.dumps(result)


def lmcache_reset_db(args: Optional[Dict[str, Any]] = None) -> str:
    """Tool: Reset the entire database."""
    plugin = get_plugin()
    success = plugin.reset_db()
    
    result = {"success": success, "message": "Database reset successfully" if success else "Failed to reset database"}
    return json.dumps(result)


def register_tools(ctx: Any) -> None:
    """Register LMCache tools with Hermes context.
    
    This function is called by Hermes during plugin discovery.
    """
    from plugins.registry import registry
    
    registry.register(
        name="lmcache_status",
        toolset="lmcache",
        schema={
            "name": "lmcache_status",
            "description": "Get LMCache KV cache status and recent entries",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lmcache_status,
        check_fn=lambda: True,  # Always available for now
    )
    
    registry.register(
        name="lmcache_set_entry",
        toolset="lmcache",
        schema={
            "name": "lmcache_set_entry",
            "description": "Set a cache entry in LMCache",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Cache key"},
                    "value": {"type": "string", "description": "Cache value"},
                    "ttl": {"type": "integer", "description": "Time to live in seconds", "default": 300},
                },
                "required": ["key", "value"],
            },
        },
        handler=lmcache_set_entry,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_get_entry",
        toolset="lmcache",
        schema={
            "name": "lmcache_get_entry",
            "description": "Get a cache entry from LMCache",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Cache key to retrieve"},
                },
                "required": ["key"],
            },
        },
        handler=lmcache_get_entry,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_remove_entry",
        toolset="lmcache",
        schema={
            "name": "lmcache_remove_entry",
            "description": "Remove a cache entry from LMCache",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Cache key to remove"},
                },
                "required": ["key"],
            },
        },
        handler=lmcache_remove_entry,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_record_optimization",
        toolset="lmcache",
        schema={
            "name": "lmcache_record_optimization",
            "description": "Record optimization statistics for a model",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "Model name"},
                    "context_length": {"type": "integer", "description": "Context length"},
                    "ttft_ms": {"type": "number", "description": "Time to first token in ms"},
                    "throughput": {"type": "number", "description": "Tokens per second"},
                    "provider": {"type": "string", "description": "AI provider name (optional)"},
                },
                "required": ["model_name", "context_length", "ttft_ms", "throughput"],
            },
        },
        handler=lmcache_record_optimization,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_get_optimization_stats",
        toolset="lmcache",
        schema={
            "name": "lmcache_get_optimization_stats",
            "description": "Get optimization statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "Filter by model name (optional)"},
                },
                "required": [],
            },
        },
        handler=lmcache_get_optimization_stats,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_get_model_context_lengths",
        toolset="lmcache",
        schema={
            "name": "lmcache_get_model_context_lengths",
            "description": "Get model context lengths by provider across all models",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lmcache_get_model_context_lengths,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_clear_all",
        toolset="lmcache",
        schema={
            "name": "lmcache_clear_all",
            "description": "Clear all cache entries",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lmcache_clear_all,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    registry.register(
        name="lmcache_reset_db",
        toolset="lmcache",
        schema={
            "name": "lmcache_reset_db",
            "description": "Reset the entire LMCache database",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        handler=lmcache_reset_db,
        check_fn=lambda: True,
        requires_env=[],
    )
    
    logger.info("LMCache tools registered with Hermes registry")