# Health Data

This is a Pyramid web application that provides interfaces to enter and view health data for a small number of people.

It consists of a database and web interface for tracking the following information:

- Period/menstrual cycle, including
  - Temperature
  - Period intensity
  - Menstrual flow rate
  - Cervical fluid
- Height and weight
- Body temperature
- Blood pressure and heart rate
- General symptoms and notes

## Set up the development environment

1. Clone and change directory into your newly created project.

  ```console
  git clone https://github.com/jhaiduce/healthdata.git
  cd healthdata
  ```

2. Create a Python virtual environment.

  ```console
  python3 -m venv ../venv
  export VENV=`pwd`/../venv
  ```

3. Upgrade packaging tools.

  ```console
$VENV/bin/pip install --upgrade pip setuptools
```

4. Install the project in editable mode with its testing requirements.

  ```console
$VENV/bin/pip install -e ".[testing]"
```

5. Initialize and upgrade the database

  ```console
$VENV/bin/initialize_healthdata_db development.ini
```

6. Run unit tests.

  ```console
$VENV/bin/pytest
```

7. Start the application on a local test server

  ```console
$VENV/bin/pserve development.ini
```

## Deployment

The project includes files and scripts to deploy the application to virtual machines on the Digital Ocean cloud services. The scripts use Docker Swarm to manage the application and its components.

### Initial deployment

1. Generate secrets for the pre-deployment tests

  ```console
$VENV/bin/python generate_secrets.py --secretsdir=integration_test_secrets --ini-filename=integration_test.ini --ini-template=integration_test.ini.tpl
```

2. Run the pre-deployment tests

  ```console
./test.sh
```

  Make sure the above tests pass before continuing.

3. Generate secrets for the production environment

  ```console
$VENV/bin/python generate_secrets.py
```

4. Generate site certificates

  a. Install [certbot](https://certbot.eff.org/en) on your development machine or another local system

  b. Obtain site certificates for your production domain using [certbot-dns-digitalocean](https://certbot-dns-digitalocean.readthedocs.io/en/stable/)

  c. Locate the files `privkey.pem` and `fullchain.pem` in `/etc/letsencrypt/live/example.com` and copy them to `nginx/ssl_production` in your `healthdata` project directory.

4. Deploy the application to the production environment

  ```
./deploy-digitalocean.sh
```

### Updating the deployed application

1. Run the pre-deployment tests

  ```console
./test.sh
```

  Make sure the above tests pass before continuing.

2. Deploy the application to the production environment

  ```
./deploy-digitalocean.sh
```

### Updating the site certificates

1. Obtain new certificates following the instructions in the [certbot-dns-digitalocean](https://certbot-dns-digitalocean.readthedocs.io/en/stable/) documentation.

2. Copy the files `privkey.pem` and `fullchain.pem` from `/etc/letsencrypt/live/example.com` to `nginx/ssl_production` in your `healthdata` project directory

3. Change the names of the secrets `ssl_certificate` and `ssl_certificate_key` in `docker-compose.yml`

  This is required because Docker secrets cannot be changed after creation. To work around this, we create new secrets by changing the secret names in `docker-compose.yml`.

4. Run the deployment script to copy the new certificates to the production environment and update the application to use them

```
./deploy-digitalocean.sh
```