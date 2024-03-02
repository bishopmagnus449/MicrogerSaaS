from django.db import models
from django.contrib.auth.models import User


class Deployment(models.Model):
    host = models.GenericIPAddressField(unique=True)  # IP address of the host
    port = models.PositiveIntegerField(default=22)  # Port (default: 22)
    user = models.CharField(max_length=255, default='root')  # Username (default: root)
    password = models.CharField(max_length=255)  # Password
    main_domain = models.CharField(max_length=255)  # Domain for users
    admin_domain = models.CharField(max_length=255)  # Domain for admin panel

    app_user = models.CharField(max_length=255)
    app_password = models.CharField(max_length=255)
    app_email = models.EmailField(max_length=255)

    db_host = models.CharField(max_length=255)
    db_port = models.PositiveIntegerField()
    db_user = models.CharField(max_length=255)
    db_password = models.CharField(max_length=255)
    db_name = models.CharField(max_length=255)

    br_user = models.CharField(max_length=255)
    br_password = models.CharField(max_length=255)
    br_vhost = models.CharField(max_length=255)

    stage = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Deployment of Microger on {self.host}"
