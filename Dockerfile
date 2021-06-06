FROM python:3.8.6-slim-buster

WORKDIR /app

RUN apt -y update
RUN apt -y install python3 python3-pip
RUN pip3 install --upgrade pip
RUN apt -y install libmariadb-dev libmariadb-dev-compat libffi-dev
RUN apt -y install npm
RUN apt -y install git
RUN apt -y install curl

COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt
COPY health_data /app/health_data
COPY setup.py /app
COPY pytest.ini /app
COPY MANIFEST.in /app
COPY CHANGES.txt /app
COPY README.md /app
RUN pip3 install --trusted-host pypi.python.org -e .

COPY pyramid_start.sh /app

EXPOSE 80

ENV NAME World

RUN adduser --system --shell /bin/sh --no-create-home --group appuser

RUN apt -y install libcap2-bin

RUN setcap CAP_NET_BIND_SERVICE=+eip /usr/local/bin/python3.8

USER appuser

HEALTHCHECK CMD curl --fail http://localhost/ || exit 1

CMD ["/app/pyramid_start.sh"]
