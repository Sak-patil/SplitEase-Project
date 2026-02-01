from django.contrib import admin
from .models import Trip, Expense, Debt

# Register your models here so they appear in the admin site
admin.site.register(Trip)
admin.site.register(Expense)
admin.site.register(Debt)