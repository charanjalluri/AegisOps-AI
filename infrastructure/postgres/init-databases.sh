#!/bin/sh
set -e

# ==============================================================================
# AegisOps AI - PostgreSQL Multi-Database Initialization Script
# Executed automatically by postgres entrypoint in /docker-entrypoint-initdb.d/
# ==============================================================================

echo "Initializing AegisOps dual database topology..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 1. Create aegisops_db (internal platform operational state)
    SELECT 'CREATE DATABASE aegisops_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aegisops_db')\gexec

    -- 2. Create demo_payment_db (simulated target service application database)
    SELECT 'CREATE DATABASE demo_payment_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'demo_payment_db')\gexec

    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE aegisops_db TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON DATABASE demo_payment_db TO "$POSTGRES_USER";
EOSQL

# Enable uuid-ossp on aegisops_db
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "aegisops_db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

# Enable uuid-ossp on demo_payment_db
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "demo_payment_db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

echo "AegisOps dual databases (aegisops_db, demo_payment_db) successfully initialized."
