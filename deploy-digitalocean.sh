#!/bin/bash

set -e

numworkers=1

DOTAGS=healthdata

host_prefix=healthdata

node_image=ubuntu-18-04-x64

node_size=s-1vcpu-1gb

if [ $(docker-machine ls -q|grep -c $host_prefix-master) -eq "0" ]; then
  docker-machine create --driver digitalocean \
		 --digitalocean-size=$node_size \
		 --digitalocean-image $node_image \
		 --digitalocean-access-token $DOTOKEN \
		 --digitalocean-tags $DOTAGS \
		 $host_prefix-master
  master_ip=$(docker-machine ip $host_prefix-master)
  docker-machine ssh $host_prefix-master docker swarm init --advertise-addr $master_ip
fi


for i in $(seq 1 $numworkers); do
    if [ $(docker-machine ls -q|grep -c $host_prefix-$i) -eq "0" ]; then
	docker-machine create --driver digitalocean \
		       --digitalocean-size $node_size \
		       --digitalocean-image $node_image \
		       --digitalocean-access-token $DOTOKEN \
		       --digitalocean-tags $DOTAGS \
		       $host_prefix-$i
    fi
done

join_token=$(docker-machine ssh $host_prefix-master docker swarm join-token -q worker)

transfer_files="docker-compose.yml docker-compose.migrate.yml mysql-config-healthdata.cnf secrets"
rsync -avz -e "docker-machine ssh $host_prefix-master" $transfer_files :

docker-machine ssh $host_prefix-master mkdir -p nginx/ssl

rsync -avz -e "docker-machine ssh $host_prefix-master" nginx/*.conf :nginx

rsync -avz -e "docker-machine ssh $host_prefix-master" nginx/ssl_production/*.pem :nginx/ssl

function isSwarmNode(){
    host=$1
    if [ "$(docker-machine ssh $host docker info | grep Swarm | sed 's/ Swarm: //g')" == "active" ]; then
        true
    else
        false
    fi
}

for i in $(seq 1 $numworkers); do
    host=$host_prefix-$i
    swarm_node=(isSwarmNode $host)
    if [ ! $swarm_node ]; then
	docker-machine ssh $host_prefix-$i \
		       docker swarm join --token $join_token $master_ip:2377
    fi
done

docker-machine ssh $host_prefix-master docker stack deploy -c docker-compose.yml healthdata
