FROM python:3.7.2-alpine
FROM node:8-alpine

WORKDIR /app

RUN apk add --update python3 py3-pip python3-dev build-base zlib-dev libjpeg-turbo-dev libpng-dev freetype-dev
RUN pip3 install --trusted-host pypi.python.org Pillow==6.2.0 numpy==1.17.2
RUN pip3 install --upgrade pip
RUN pip3 install --trusted-host pypi.python.org pandas==1.0.1
RUN apk add libffi-dev mariadb-dev

COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt
COPY health_data /app/health_data
COPY setup.py /app
COPY pytest.ini /app
COPY MANIFEST.in /app
COPY CHANGES.txt /app
COPY README.txt /app
RUN pip3 install --trusted-host pypi.python.org -e .

COPY pyramid_start.sh /app

EXPOSE 80

ENV NAME World

RUN addgroup --system appuser && \
    adduser --system -s /bin/sh --no-create-home appuser appuser

RUN apk add libcap

RUN setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python3.8

USER appuser

HEALTHCHECK CMD curl --fail http://localhost/ || exit 1

CMD ["/app/pyramid_start.sh"]
