# Generated by Django 5.1.4 on 2024-12-19 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_wishlist_product_attribute'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartorder',
            name='razorpay_signature',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]