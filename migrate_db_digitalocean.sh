#!/bin/bash

set -e

host_prefix=healthdata

# Migrate database
docker-machine ssh $host_prefix-master docker stack deploy -c docker-compose.yml -c docker-compose.migrate.yml healthdata

# Wait for migration to finish
while true; do
    num_containers=$(docker-machine ssh $host_prefix-master docker service ps -q -f desired-state=running healthdata_migration|wc -l)
    if [ $num_containers==0 ]; then break
    fi
done

# Print migration logs
docker-machine ssh $host_prefix-master docker service logs healthdata_migration

# Delete migration service
docker-machine ssh $host_prefix-master docker service rm healthdata_migration
