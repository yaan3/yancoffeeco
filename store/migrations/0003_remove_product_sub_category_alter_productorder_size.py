# Generated by Django 5.1.3 on 2024-11-29 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_coupon_cartorder_discounts_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='sub_category',
        ),
        migrations.AlterField(
            model_name='productorder',
            name='size',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]