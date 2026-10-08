#!/bin/sh
set -e

# ==============================================================================
# AegisOps AI - Kafka Topics Initialization Wrapper (LF endings enforced)
# ==============================================================================

KAFKA_SERVER="${KAFKA_BOOTSTRAP_SERVERS:-localhost:29092}"
echo "Provisioning Kafka topics on: $KAFKA_SERVER"

python /app/scripts/init-kafka.py "$KAFKA_SERVER" || python scripts/init-kafka.py "$KAFKA_SERVER"
echo "Kafka operational topics provisioned."
