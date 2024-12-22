# Generated by Django 5.1.3 on 2024-11-28 09:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('discount', models.PositiveIntegerField(help_text='discount in percentage')),
                ('active', models.BooleanField(default=True)),
                ('active_date', models.DateField()),
                ('expiry_date', models.DateField()),
                ('created_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='cartorder',
            name='discounts',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='cartorder',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='cartorder',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='cartorder',
            name='return_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cartorder',
            name='return_request_status',
            field=models.CharField(choices=[('New', 'New'), ('Paid', 'Paid'), ('Shipped', 'Shipped'), ('Conformed', 'Conformed'), ('Pending', 'Pending'), ('Delivered', 'Delivered'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled'), ('Return Requested', 'Return Requested'), ('Return Approved', 'Return Approved'), ('Return Rejected', 'Return Rejected')], default='None', max_length=20),
        ),
        migrations.AddField(
            model_name='cartorder',
            name='wallet_balance_used',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='cartorder',
            name='status',
            field=models.CharField(choices=[('New', 'New'), ('Paid', 'Paid'), ('Shipped', 'Shipped'), ('Conformed', 'Conformed'), ('Pending', 'Pending'), ('Delivered', 'Delivered'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled'), ('Return Requested', 'Return Requested'), ('Return Approved', 'Return Approved'), ('Return Rejected', 'Return Rejected')], default='Pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='productorder',
            name='size',
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
        migrations.CreateModel(
            name='CategoryOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_percentage', models.PositiveIntegerField(help_text='discount in percentage')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.category')),
            ],
        ),
        migrations.CreateModel(
            name='ProductOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_percentage', models.PositiveIntegerField(help_text='discount in percentage')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.product')),
            ],
        ),
        migrations.CreateModel(
            name='ReturnReason',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sizing_issues', models.BooleanField(default=False)),
                ('damaged_item', models.BooleanField(default=False)),
                ('incorrect_order', models.BooleanField(default=False)),
                ('delivery_delays', models.BooleanField(default=False)),
                ('customer_service', models.BooleanField(default=False)),
                ('other_reason', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.cartorder')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]