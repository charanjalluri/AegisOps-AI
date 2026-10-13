#!/usr/bin/env python3
"""
Alias runner for scripts/reset_demo.py
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.reset_demo import reset_demo

if __name__ == "__main__":
    reset_demo()
