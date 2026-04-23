"""
Root conftest.py – adds the agentic-system package to sys.path so that
imports like `from beats import Beat` work inside tests without installing
the package.
"""
import sys
from pathlib import Path

# Make agentic-system importable
sys.path.insert(0, str(Path(__file__).parent.parent / "agentic-system"))

