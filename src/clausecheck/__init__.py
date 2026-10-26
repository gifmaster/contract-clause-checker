"""clausecheck: transparent, rule-based clause extraction and risk checks for AI and SaaS contracts."""

from .engine import Finding, Result, Rules, Segment, analyse
from .reader import read_bytes, read_file
from .report import to_csv, to_markdown

__all__ = ["Finding", "Result", "Rules", "Segment", "analyse", "read_bytes", "read_file", "to_csv", "to_markdown"]
__version__ = "0.1.0"
