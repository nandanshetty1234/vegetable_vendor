from django.db import models
from datetime import date

class VegetableSale(models.Model):
    date = models.DateField(default=date.today)  # Default to today's date
    vegetable = models.CharField(max_length=100)
    quantity = models.FloatField(null=True, blank=True)
    purchase_price = models.FloatField(null=True, blank=True)
    selling_price = models.FloatField(null=True, blank=True)

    # These fields are stored but won't be auto-calculated
    total_purchase_price = models.FloatField(null=True, blank=True)
    total_selling_price = models.FloatField(null=True, blank=True)
    profit = models.FloatField(null=True, blank=True)
    loss = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('vegetable', 'date')  # Ensures uniqueness for vegetable + date

    def __str__(self):
        return f"{self.vegetable} - {self.date}"


class DailySummary(models.Model):
    date = models.DateField(unique=True)  # Only one summary per date
    total_purchase_price = models.FloatField(default=0.0)
    total_selling_price = models.FloatField(default=0.0)
    total_profit = models.FloatField(default=0.0)
    total_loss = models.FloatField(default=0.0)

    def __str__(self):
        return f"Summary for {self.date}"
    
class VegetableReport(models.Model):
    date = models.DateField()
    vegetable = models.CharField(max_length=50)
    quantity = models.FloatField()
    purchase_price = models.FloatField()
    selling_price = models.FloatField()
    total_purchase = models.FloatField()
    total_selling = models.FloatField()
    profit = models.FloatField()
    loss = models.FloatField()

    def __str__(self):
        return f"{self.vegetable} - {self.date}"
    

class ReportSummary(models.Model):
    date = models.DateField(unique=True)
    total_purchase = models.FloatField(default=0)
    total_selling = models.FloatField(default=0)
    profit = models.FloatField(default=0)
    loss = models.FloatField(default=0)

    def __str__(self):
        return f"Summary for {self.date}"
    
