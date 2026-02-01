from django.db import models
from django.contrib.auth.models import User#djangos built in user system

class Trip(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(User, related_name="trips")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    CATEGORIES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Stay', 'Stay'),
        ('Other', 'Other'),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="expenses")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    description = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True,null=True, blank=True)

    def __str__(self):
        return f"{self.description} ({self.amount})"

class Debt(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, related_name="debts_to_pay", on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name="debts_to_receive", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('trip', 'from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} owes {self.amount} to {self.to_user}"