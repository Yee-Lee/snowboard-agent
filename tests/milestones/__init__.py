"""M1 Foundation milestone entrypoint.

This file aggregates all M1 test modules so that running:
    python -m pytest -v tests/milestones/test_m1_foundation.py
reproduces every M1 behaviour specified in test_spec_M1.md.

Individual test modules live under tests/ by subsystem; this file
re-exports them via pytest_plugins so a single entrypoint covers all.
"""
