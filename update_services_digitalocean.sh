#!/bin/bash

set -e

host_prefix=healthdata

# Update services
docker-machine ssh $host_prefix-master docker service update --image jhaiduce/healthdata healthdata_web
