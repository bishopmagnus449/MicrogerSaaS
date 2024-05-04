import re
from typing import Optional

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from paramiko.ssh_exception import AuthenticationException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
from fabric import Connection, Config
from invoke import Responder, UnexpectedExit, Result
from . import models
from django.shortcuts import render


class TestView(APIView):

    @staticmethod
    def get(request: Request):
        log = request.query_params.get('log')
        _send_log(log)
        return Response({'status': True, 'log': log})


def _send_log(log: str, color: str = 'grey'):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)('log_group', {'type': 'log_message', 'message': log, 'color': color})


def _send_progress(percentage: int):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)('progress_group', {'type': 'progress', 'percentage': percentage})


class Deployment:
    _connection: Connection
    _deployment: models.Deployment

    def __init__(self, data):
        self.host = data.get('host')
        self.port = data.get('port')
        self.user = data.get('username')
        self.password = data.get('password')
        self.github_pat = data.get('github_key')

        app_config = data.get('app')
        db_config = data.get('database')
        br_config = data.get('broker')

        self.admin_domain = app_config.get('adminDomain')
        self.user_domain = app_config.get('userDomain')
        self.app_user = app_config.get('username')
        self.app_password = app_config.get('password')
        self.app_email = app_config.get('email', 'admin@admin.com')

        self.db_host = db_config.get('host')
        self.db_port = db_config.get('port')
        self.db_name = db_config.get('name')
        self.db_user = db_config.get('username')
        self.db_password = db_config.get('password')

        self.br_user = br_config.get('username')
        self.br_password = br_config.get('password')
        self.br_vhost = br_config.get('vhost')

        self.sudo_pass = Responder(
            pattern=r'\[sudo\] password',
            response=f"{self.password}\n",
        )
        self.prompt_bypass = Responder(
            pattern=r'What do you want to do about',
            response='2\n'  # Keep the local version
        )

        self.stage_functions = {
            1: self._update_system,
            2: self._install_dependencies,
            3: self._configure_database,
            4: self._configure_broker,
            5: self._configure_microger_user,
            6: self._clone_project_repository,
            7: self._configure_project_environment,
            8: self._configure_project_services,
            9: self._configure_celery_worker,
            10: self._configure_nginx,
            11: self._register_domain_certs,
            12: self._restart_services,
        }
        self.stage_progress = [5, 15, 35, 40, 45, 50, 70, 75, 80, 85, 90, 95, 100]

    def start_setup(self) -> tuple[bool, Optional[str]]:
        _send_progress(0)
        deployment_data = {
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "main_domain": self.user_domain,
            "admin_domain": self.admin_domain,
            "app_user": self.app_user,
            "app_password": self.app_password,
            "app_email": self.app_email,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "db_password": self.db_password,
            "br_user": self.br_user,
            "br_password": self.br_password,
            "br_vhost": self.br_vhost,
        }
        self._deployment, _ = models.Deployment.objects.update_or_create(defaults=deployment_data, host=self.host)

        if not self._verify_github_key():
            return False, 'Provided github pat is invalid'
        self._create_ssh_connection()

        for stage in range(self._deployment.stage + 1, len(self.stage_functions) + 1):
            stage_func = self.stage_functions.get(stage)
            if stage_func:
                try:
                    _send_progress(self.stage_progress[stage - 1])
                    success = stage_func()
                except UnexpectedExit as e:
                    success = False
                    _send_log(
                        f'Command "{e.result.command}" failed with exit code {e.result.exited}, stderr: {e.result.stderr}',
                        'danger')
                if success:
                    self._deployment.stage = stage
                    self._deployment.save()
                    _send_progress(self.stage_progress[stage])
                else:
                    return False, 'Installation failed due to previous error.'
        _send_log('Installation completed.', 'success')
        return True, None

    def _verify_github_key(self, key: str = None):
        key = key or self.github_pat
        _send_log('Checking github pat...', 'info')
        headers = {"Authorization": f"token {key}"}
        response = requests.get('https://api.github.com/repos/realSamy/PyMicroger', headers=headers)
        if response.status_code != 200:
            _send_log('Provided github pat is invalid', 'danger')
            return False
        _send_log('Github pat verification was successful.', 'success')
        return True

    def _create_ssh_connection(self):
        _send_log(f'Connecting to {self.user}@{self.host}:{self.port} using ssh', 'info')
        try:
            config = Config(overrides={'sudo': {'password': self.password}})
            self._connection = Connection(self.host, self.user, self.port, connect_kwargs={'password': self.password},
                                          config=config)
            self._connection.run('whoami')
            command = """echo "export GNUTLS_CPUID_OVERRIDE=0x1" >> .bashrc
echo "export DEBIAN_FRONTEND=noninteractive" >> .bashrc"""
            self._connection.sudo(command)
            _send_log(f'Connected to {self.host}', 'success')
        except AuthenticationException:
            _send_log(f'Authentication for {self.host} failed, please (re)check the username or password.',
                      'danger')
            raise AuthenticationException
        except UnexpectedExit as e:
            _send_log(
                f'Command "{e.result.command}" failed with exit code {e.result.exited}, stderr: {e.result.stderr}',
                'danger')

    def _update_system(self):
        _send_log(f'Updating modules\' database', 'info')
        command = 'apt-get update && apt-get -o Dpkg::Options::=--force-confold -s upgrade -y'
        try:
            self._connection.sudo(command, watchers=[self.prompt_bypass])
        except UnexpectedExit as e:
            _send_log(
                f'Command "{e.result.command}" failed with exit code {e.result.exited}, stderr: {e.result.stderr}',
                'danger')
            if 'It is held by process' in e.result.stderr:
                self._terminate_process(self._extract_process_id(e.result.stderr))
            return self._update_system()
        _send_log(f'Modules updated', 'success')
        return True

    def _install_dependencies(self):
        try:
            _send_log(f'Preparing for linux dependencies installation...', 'info')
            command = 'apt-get install -y wget gnupg ca-certificates curl'
            self._connection.sudo(command, watchers=[self.prompt_bypass])

            _send_log(f'Preparing rabbitmq repo...', 'info')
            command = (
                'wget -O- https://github.com/rabbitmq/signing-keys/releases/download/2.0/rabbitmq-release-signing-'
                'key.asc | sudo apt-key add -')
            self._connection.sudo(command, watchers=[self.prompt_bypass])

            _send_log(f'Preparing node.js repo...', 'info')
            command = """mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list"""
            self._connection.sudo(command)

            _send_log(f'Installing linux modules, this can take a while...', 'info')
            command = 'apt-get update && apt-get install -y nginx python3-pip python3-dev python3-certbot-nginx postgresql postgresql-contrib git rabbitmq-server nodejs python3-venv supervisor'
            self._connection.sudo(command, watchers=[self.prompt_bypass])

            _send_log(f'Linux modules installed successfully.', 'success')
            return True
        except UnexpectedExit as e:
            _send_log(f'Following error occurred: {e.result.stderr}, retrying...', 'info')
            return self._install_dependencies()

    def _configure_database(self):
        _send_log(f'Configuring database...', 'info')
        command = f"""sudo -u postgres psql -c "CREATE USER {self.db_user} WITH PASSWORD '{self.db_password}';"
sudo -u postgres psql -c "CREATE DATABASE {self.db_name} OWNER {self.db_user} ENCODING 'UTF8';" """
        self._connection.sudo(command)
        return True

    def _configure_broker(self):
        _send_log(f'Configuring broker...', 'info')
        command = "systemctl start rabbitmq-server && rabbitmq-plugins enable rabbitmq_management &"
        self._connection.sudo(command)
        self._connection.run("wait")

        command = f"""rabbitmqctl add_user "{self.br_user}" "{self.br_password}" &&
rabbitmqctl set_user_tags {self.br_user} administrator &&
rabbitmqctl add_vhost "{self.br_vhost}" &&
rabbitmqctl set_permissions -p / {self.br_user} ".*" ".*" ".*" &&
rabbitmqctl set_permissions -p "{self.br_vhost}" "{self.br_user}" ".*" ".*" ".*" """
        self._connection.sudo(command)
        self._connection.run("wait")

        self._connection.sudo("service rabbitmq-server restart")
        self._connection.run("wait")
        return True

    def _configure_microger_user(self):
        _send_log('Configuring microger user...', 'info')
        command = f"""useradd -m microger
usermod -aG sudo microger
echo "microger:{self.app_password}" | chpasswd
echo "export GNUTLS_CPUID_OVERRIDE=0x1" >> /home/microger/.bashrc"""
        self._connection.sudo(command)
        return True

    def _clone_project_repository(self):
        _send_log('Downloading project files...', 'info')
        command = f"""su -l -c "
                    mkdir -p /home/microger/web/repositories/
                    cd /home/microger/web/repositories/
                    git clone https://oauth2:{self.github_pat}@github.com/realSamy/PyMicroger.git
                    cd PyMicroger
                    pip3 install -r requirements.txt
                    git clone https://oauth2:{self.github_pat}@github.com/realSamy/VueMicroger.git
                    cd VueMicroger
                    npm install
                    npm run build
                    cd ..
                    mkdir -p templates/panel/
                    cp staticfiles/index.html templates/panel/
                " microger """

        self._connection.sudo(command)
        return True

    def _configure_project_environment(self):
        _send_log('Configuring project environment...', 'info')
        env_content = f"""# Django
SECRET_KEY='fl2flvdk^-bij)foc-b!k2)loc!k2))2k&)o9dk^ij))-9an(%aqoc-b!k2)fl2k&)o9dk^ij)h2&tzby@1lap!h3n#!z)e'
DEBUG=''

# Office
AUTHORITY='https://login.microsoftonline.com/common'
OFFICE_LOGIN_REDIRECT='https://outlook.com'
OFFICE_QUERY='\"wire transfer\" OR \"invoice\" OR \"bank transfer\" OR \"payment\" OR \"wiring instructions\" OR \"capital call\" OR \"investment\" OR \"Account payable\" OR \"invoice payment\" \"ACH payment\" OR \"outgoing payment\" OR \"controller\" OR \"Remittance\" OR \"Transfer instruction\" OR \"Payment instructions\" OR \"international payment\" OR \"fund transfer\" OR \"fund\" OR \"bank\" OR \"sort code\" OR \"bsb\" OR \"wire details\" OR \"iban\" OR \"facture\" OR \"distribution\"'

# Gmail
GMAIL_LOGIN_REDIRECT='https://gmail.com'
GMAIL_QUERY='has:attachment'

# Database
DB_USER={self.db_user}
DB_PASSWORD={self.db_password}
DB_NAME={self.db_name}
DB_HOST={self.db_host}
DB_PORT={self.db_port}
DB_CONN_MAX_AGE=0

# Domains
MAIN_DOMAIN={self.user_domain}
ADMIN_DOMAIN={self.admin_domain}

# Broker
BR_USER={self.br_user}
BR_PASSWORD={self.br_password}
BR_VHOST={self.br_vhost}

#Proxy list file
PROXY_LIST='proxies.txt'
PROXY_ENABLED=false"""
        command = f"""echo "{env_content}" > /home/microger/web/repositories/PyMicroger/.env """
        self._connection.sudo(command)
        return True

    def _configure_project_services(self):
        _send_log('Configuring project services...', 'info')
        command = rf"""su -l -c "/bin/bash -c \"
            cd /home/microger/web/repositories/PyMicroger/
            python3 manage.py makemigrations
            python3 manage.py migrate
            python3 manage.py shell << EOF
from django.contrib.auth import get_user_model; User = get_user_model()
User.objects.create_superuser('{self.app_user}', '{self.app_email}', '{self.app_password}')
EOF
            screen -dmS celery_worker bash -c 'celery -A config worker -l info'
        \"" microger """
        self._connection.sudo(command)
        return True

    def _configure_celery_worker(self):
        _send_log('Configuring celery worker...', 'info')
        command = """mkdir -p /var/log/celery
chown microger /var/log/celery
echo '[program:celery]
command=/home/microger/web/repositories/PyMicroger/celery_runner.sh
directory=/home/microger/web/repositories/PyMicroger
user=microger
numprocs=1
stdout_logfile=/var/log/celery/microger.log
stderr_logfile=/var/log/celery/microger_error.log
environment=PYTHONPATH="/home/microger/.local/bin/python"
autostart=true
autorestart=true
startsecs=10
stopwaitsecs = 600' > /etc/supervisor/conf.d/microger.conf
chmod +x /home/microger/web/repositories/PyMicroger/celery_runner.sh
supervisorctl reread
supervisorctl update
supervisorctl start celery"""
        self._connection.sudo(command)
        return True

    def _configure_nginx(self):
        _send_log('Configuring nginx backend...', 'info')
        command = """chown -R microger:microger /home/microger
chmod -R 775 /home/microger
chgrp -R www-data /home/microger

ufw allow 'Nginx Full'

echo "[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target" > /etc/systemd/system/gunicorn.socket

echo "[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=microger
Group=www-data
WorkingDirectory=/home/microger/web/repositories/PyMicroger/
ExecStart=/home/microger/.local/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/gunicorn.service

sed -i "/server_names_hash_bucket_size/s/# *//;s/server_names_hash_bucket_size .*/server_names_hash_bucket_size 128;/" "/etc/nginx/nginx.conf"
"""
        self._connection.sudo(command)
        return True

    def _register_domain_certs(self):
        _send_log('Registering domains\' ssl certificates...', 'info')
        command = (f'certbot --register-unsafely-without-email --nginx --agree-tos -n '
                   f'-d "{self.admin_domain}" '
                   f'-d "{self.user_domain}"')
        self._connection.sudo(command)

        command = rf"""echo "server {{
        listen 80;
        listen [::]:80;
    server_name {self.admin_domain};

    location = /favicon.ico {{ access_log off; log_not_found off; }}
    location /static/ {{
        alias /home/microger/web/repositories/PyMicroger/staticfiles/;
    }}

    location /media/ {{
        alias /home/microger/web/repositories/PyMicroger/media/;
    }}

    location / {{
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }}

    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/\$host/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/\$host/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}}

server {{
        server_name www.{self.user_domain};
        return 301 \$scheme://{self.user_domain}\$request_uri;
}}
server {{
        server_name www.{self.admin_domain};
        return 301 \$scheme://{self.admin_domain}\$request_uri;
}}" > /etc/nginx/sites-available/microger

ln -s /etc/nginx/sites-available/microger /etc/nginx/sites-enabled
rm -rf /etc/nginx/sites-enabled/default """
        self._connection.sudo(command)

        command = """chown -R www-data:www-data /etc/letsencrypt/
chmod -R 755 /etc/letsencrypt/"""
        self._connection.sudo(command)
        return True

    def _restart_services(self):
        _send_log('Restarting server services...', 'info')
        command = """systemctl daemon-reload
systemctl restart gunicorn
systemctl restart nginx
systemctl start supervisor
systemctl enable supervisor
systemctl enable gunicorn
systemctl enable nginx
systemctl enable postgresql
systemctl enable rabbitmq-server"""
        self._connection.sudo(command)
        return True

    @staticmethod
    def _extract_process_id(stderr):
        match = re.search(r'It is held by process (\d+)', stderr)
        if match:
            return match.group(1)

    def _terminate_process(self, process_id):
        if not process_id:
            return False
        command = f'kill {process_id}'
        self._connection.sudo(command)


def renderHome(request):
    return render(request, 'index.html')


class NewDeploymentAPI(APIView):
    def post(self, request: Request):
        deployment = Deployment(request.data)
        try:
            status, error = deployment.start_setup()
            return Response({'status': status, 'error': error})
        except Exception as e:
            return Response({'status': False, 'error': str(e)})
