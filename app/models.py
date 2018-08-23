from django.db import models


class Feed(models.Model):
    account = models.EmailField(primary_key=True)
    password = models.CharField(max_length=50)


class Location(models.Model):
    locid = models.CharField(max_length=36, primary_key=True)
    account = models.EmailField()
    uid = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    time = models.DateTimeField()
    longitude = models.FloatField()
    latitude = models.FloatField()
    accuracy = models.FloatField()
    address = models.CharField(max_length=200)
