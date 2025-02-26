from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,  # Delete members when user is deleted
        related_name='members'
    )

    # Stores member information from Excel
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    account_number = models.CharField(max_length=50)
    year = models.PositiveIntegerField()  # New field
    monthly_contributions = models.JSONField(default=dict)  # Stores {month: amount}
    # Add default annual_target if missing
    annual_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=6000.00
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('account_number', 'year')  # Prevent duplicate entries

    @property
    def total_contributed(self):
        return sum(float(amt) for amt in self.monthly_contributions.values())

    @property
    def total_deficit(self):
        return sum(self.deficits().values())

    def deficits(self):
        deficits = {}
        # Calculate total paid for Jan-Mar
        total_paid = sum(float(self.monthly_contributions.get(month, 0)) 
                        for month in ['January', 'February', 'March'])
        
        # Calculate deficit only for March if total is less than annual target
        if total_paid < float(self.annual_target):
            deficits['March'] = float(self.annual_target) - total_paid
        
        # No deficits for other months
        for month in ['January', 'February', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']:
            deficits[month] = 0.0
            
        return deficits
