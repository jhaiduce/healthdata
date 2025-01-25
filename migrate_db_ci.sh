#!/bin/bash

set -e

# Migrate database
sudo docker compose -f docker-compose.test_secrets.yml -f docker-compose.db.yml -f docker-compose.migrate.yml -p healthdata_ci up -d

exitcode=$(sudo docker wait healthdata_ci_migration_1)

# Print migration logs
sudo docker logs healthdata_ci_migration_1

exit $exitcode
