"""Storage layer for NebiusBench benchmark results."""

from benchmark.storage.database import get_db, init_db
from benchmark.storage.repository import BenchmarkRepository

__all__ = ["get_db", "init_db", "BenchmarkRepository"]
