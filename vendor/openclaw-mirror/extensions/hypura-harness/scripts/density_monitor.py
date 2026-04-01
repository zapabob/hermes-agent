import os
import ast
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ASI_DENSITY: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
METRICS_PATH = ROOT / "density_metrics.json"

class DensityMonitor:
    def __init__(self, target_dir: Path):
        self.target_dir = target_dir

    def calculate_complexity(self, code: str) -> int:
        """Simple cyclomatic complexity proxy via AST nodes."""
        try:
            tree = ast.parse(code)
            complexity = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                    complexity += 1
            return complexity
        except SyntaxError:
            return 0

    def audit(self) -> dict:
        shards = list(self.target_dir.glob("*.py"))
        total_lines = 0
        total_complexity = 0
        shard_stats = {}

        for shard in shards:
            content = shard.read_text(encoding="utf-8")
            lines = len(content.splitlines())
            complexity = self.calculate_complexity(content)
            total_lines += lines
            total_complexity += complexity
            shard_stats[shard.name] = {
                "lines": lines,
                "complexity": complexity,
                "density": round(complexity / lines, 4) if lines > 0 else 0
            }

        # Intelligence Density Metric (Complexity per Shard over total scale)
        intelligence_density = total_complexity / len(shards) if shards else 0
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "shard_count": len(shards),
            "total_lines": total_lines,
            "total_complexity": total_complexity,
            "intelligence_density": round(intelligence_density, 4),
            "shards": shard_stats
        }
        return metrics

    def save_metrics(self, metrics: dict):
        history = []
        if METRICS_PATH.exists():
            try:
                history = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
                if not isinstance(history, list): history = [history]
            except: history = []
        
        history.append(metrics)
        # Keep last 100 pulses
        METRICS_PATH.write_text(json.dumps(history[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Density Audit Complete. Intelligence Density: {metrics['intelligence_density']}")

if __name__ == "__main__":
    monitor = DensityMonitor(ROOT)
    results = monitor.audit()
    monitor.save_metrics(results)
