export VENV=`pwd`/../venv

sudo docker kill healthdata_web
sudo docker kill healthdata_ci_sut_1

$VENV/bin/pytest -q && \
    $VENV/bin/pytest -q health_data/migration_tests.py && \
    sudo docker-compose -f docker-compose.test.yml -p healthdata_ci build && \
    sudo docker-compose -f docker-compose.test.yml -p healthdata_ci up -d && \
    sudo docker logs -f healthdata_ci_sut_1
