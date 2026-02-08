from django.db import models
from django.contrib.auth.models import User#djangos built in user system

class Trip(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True,blank=True)
    members = models.ManyToManyField(User, related_name="trips")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_trips", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

    def __str__(self):
        return self.name

class TripMember(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="trip_members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, help_text="WhatsApp number with country code (e.g., +919876543210)")
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'whatsapp_number')

    def __str__(self):
        return f"{self.name} ({self.whatsapp_number}) - {self.trip.name}"

    def get_whatsapp_link(self, message):
        """Generate WhatsApp click-to-chat link"""
        # Remove any non-digit characters except +
        number = ''.join(c for c in self.whatsapp_number if c.isdigit() or c == '+')
        if number.startswith('+'):
            number = number[1:]  # Remove + for URL
        encoded_message = message.replace(' ', '%20').replace('\n', '%0A')
        return f"https://wa.me/{number}?text={encoded_message}"

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