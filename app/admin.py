from django.contrib import admin
from app.models import Feed, Location


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ('account',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'time', 'address')
    readonly_fields = ('locid', 'account', 'uid', 'name', 'time', 'longitude', 'latitude', 'accuracy', 'address')
