#!/bin/bash

set -e

numworkers=1

DOTAGS=healthdata

host_prefix=healthdata

stack_name=healthdata

node_image=ubuntu-18-04-x64

node_size=s-1vcpu-1gb

sudo docker-compose -f docker-compose.yml build

sudo docker-compose -f docker-compose.yml push

if [ ! -f etc/letsencrypt/options-ssl-nginx.conf ]; then
    curl -L --create-dirs -o etc/letsencrypt/options-ssl-nginx.conf https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf
fi

if [ $(docker-machine ls -q|grep -c $host_prefix-master) -eq "0" ]; then
  docker-machine create --driver digitalocean \
		 --digitalocean-size=$node_size \
		 --digitalocean-image $node_image \
		 --digitalocean-access-token $DOTOKEN \
		 --digitalocean-tags=$DOTAGS \
		 $host_prefix-master
  master_ip=$(docker-machine ip $host_prefix-master)
  docker-machine ssh $host_prefix-master docker swarm init --advertise-addr $master_ip
else
  master_ip=$(docker-machine ip $host_prefix-master)
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

docker-machine ssh $host_prefix-master docker node update --label-add db=true $host_prefix-1
docker-machine ssh $host_prefix-master docker node update --label-add db=false $host_prefix-master

join_token=$(docker-machine ssh $host_prefix-master docker swarm join-token -q worker)

transfer_files="docker-compose.yml docker-compose.migrate.yml mysql-config-healthdata.cnf secrets"
rsync -avz -e "docker-machine ssh $host_prefix-master" $transfer_files :

docker-machine ssh $host_prefix-master mkdir -p nginx/ssl

openssl rsa -in nginx/ssl_production/privkey.pem -out nginx/ssl_production/privkeyrsa.pem

rsync -avz -e "docker-machine ssh $host_prefix-master" nginx/*.conf :nginx
rsync -avz -e "docker-machine ssh $host_prefix-master" etc :

rsync -avz -e "docker-machine ssh $host_prefix-master" nginx/ssl_production/*.pem :nginx/ssl

function isSwarmNode(){
    host=$1
    if [ "$(docker-machine ssh $host docker info | grep Swarm | sed 's/ Swarm: //g')" == "active" ]; then
        swarm_node=1
    else
        swarm_node=0
    fi
}

for i in $(seq 1 $numworkers); do
    host=$host_prefix-$i
    isSwarmNode $host
    if [ $swarm_node == 1 ]; then
        echo "$host_prefix-$i is already a member of the swarm"
    fi
    if [ $swarm_node == 0 ]; then
    echo "Joining node $i to swarm"
	docker-machine ssh $host \
		       docker swarm join --token $join_token $master_ip:2377
    fi
done

export SSL_CHECKSUM=$(openssl x509 -in nginx/ssl_production/fullchain.pem -outform DER \
			  | sha1sum | head -c 40)

if docker-machine ssh $host_prefix-master docker secret inspect ssl_certificate.${SSL_CHECKSUM}
then :
else
    docker-machine ssh $host_prefix-master docker secret create ssl_certificate.${SSL_CHECKSUM} \
		   nginx/ssl/fullchain.pem
fi

if docker-machine ssh $host_prefix-master \
		  docker secret inspect ssl_certificate_key.${SSL_CHECKSUM}
then :
else
    docker-machine ssh $host_prefix-master \
		   docker secret create ssl_certificate_key.${SSL_CHECKSUM} \
		   nginx/ssl/privkey.pem
fi

# Deploy the stack
docker-machine ssh $host_prefix-master SSL_CHECKSUM=${SSL_CHECKSUM} DOMAIN=healthdata.haiducekcannon.site EMAIL=jhaiduce@gmail.com NGINX_UID=101 docker stack deploy -c docker-compose.yml ${stack_name}

# Delete the migration service (in case it still exists from a previous execution)
if docker-machine ssh $host_prefix-master docker service rm ${stack_name}_migration; then :; fi

# Update the database
docker-machine ssh $host_prefix-master SSL_CHECKSUM=${SSL_CHECKSUM} docker stack deploy -c docker-compose.yml -c docker-compose.migrate.yml ${stack_name}

function wait_for_migration {

    while [ 1 ]; do
	desired_state=$( docker-machine ssh $host_prefix-master docker service ps --format '{{.DesiredState}}' ${stack_name}_migration )
	current_state=$( docker-machine ssh $host_prefix-master docker service ps --format '{{.CurrentState}}' ${stack_name}_migration )

	echo 'Migration' $desired_state $current_state

	if [ $desired_state = 'Shutdown' ]; then
	    migration_container=$(docker-machine ssh $host_prefix-master docker service ps --format '{{.ID}}' ${stack_name}_migration)
	    migration_status=$(docker-machine ssh $host_prefix-master docker inspect --format '{{.Status.ContainerStatus.ExitCode}}' $migration_container)
	    return
	fi

	sleep 1
    done
}

# Wait for it to complete
wait_for_migration

docker-machine ssh $host_prefix-master docker service logs ${stack_name}_migration

if [ $migration_status -ne 0 ]; then
    exit 1;
fi

# Delete the migration service
docker-machine ssh $host_prefix-master docker service rm ${stack_name}_migration

# Update images
docker-machine ssh $host_prefix-master docker service update --image jhaiduce/healthdata ${stack_name}_web
