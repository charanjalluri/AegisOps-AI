#!/usr/bin/env python3
"""
AegisOps AI - Apache Kafka Topic Provisioner CLI Entrypoint
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.init_kafka import ensure_topics, TOPIC_CONFIGS, get_topic_names

if __name__ == "__main__":
    servers = sys.argv[1] if len(sys.argv) > 1 else None
    success = ensure_topics(servers)
    sys.exit(0 if success else 1)
