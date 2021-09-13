from django.db import models


class Investor(models.Model):
    address = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100)


class UsdRate(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    value = models.FloatField()
    last_update_at = models.DateTimeField(auto_now=True)
