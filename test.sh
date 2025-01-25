#!/bin/bash

export VENV=`pwd`/../venv



# Kill running containers
sudo docker kill healthdata_web
sudo docker kill healthdata_ci-sut-1
sudo docker kill healthdata_ci-migration-1

sandbox_files=("mysql-config-healthdata.cnf" "integration_test_secrets")

for file in "${sandbox_files[@]}"
do
    chcon -Rt svirt_sandbox_file_t "$file"
done

set -e

# Run unit tests
$VENV/bin/pytest -q

# Run migration tests
$VENV/bin/pytest -q health_data/migration_tests.py

# Build images
sudo docker compose -f docker-compose.test_secrets.yml -f docker-compose.web.yml -f docker-compose.test.yml -f docker-compose.db.yml -p healthdata_ci build

# Run database migration
./migrate_db_ci.sh

# Run tests
sudo docker compose -f docker-compose.test_secrets.yml -f docker-compose.web.yml -f docker-compose.db.yml -f docker-compose.test.yml -p healthdata_ci up --remove-orphans -d

# Print test logs
sudo docker logs -f healthdata_ci-sut-1
