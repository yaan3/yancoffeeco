from django.db import models
from django.utils.safestring import mark_safe
from accounts.models import *
from django.utils import timezone
# Create your models here.

class Size(models.Model):
    size = models.CharField(max_length=50)
    
    def __str__(self):
        return self.size

def generic_directory_path(instance,filename):
    model_name = instance.__class__.__name__.lower()

    pk = instance.pid if hasattr(instance,'pid') else None

    if pk:
        return f'{model_name}_{pk}/{filename}'
    else:
        return f'{model_name}_unknown/{filename}'

class Category(models.Model):
    c_id = models.BigAutoField(unique=True, primary_key=True)
    c_name = models.CharField(max_length = 50, null=True)
    c_image = models.ImageField(upload_to='category',default='category.jpg')
    is_blocked = models.BooleanField(default=False)
    class Meta:
        verbose_name_plural = "Categories"

    def category_image(self):
        if self.c_image:
            return mark_safe('<img src="%s" width="50" height="50" />' % (self.c_image.url))
        else:
            return "No Image Available"


    def __str__(self):
        return self.c_name


class Product(models.Model):
    p_id = models.BigAutoField(unique=True, primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, related_name="products")
    title = models.CharField(default="product")
    description = models.TextField(null=True, blank=True, default="This is the product")
    specifications = models.TextField(null=True, blank=True)
    shipping = models.TextField(null=True)
    availability = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    latest = models.BooleanField(default=False)
    popular = models.BooleanField(default=False)
    image = models.ImageField(upload_to='product_images', default='product.jpg')

    class Meta:
        verbose_name_plural = "Products"
        
    def __str__(self):
        return self.title

    def get_applicable_offer_percentage(self):
        product_offer = ProductOffer.objects.filter(product=self, is_active=True).first()
        category_offer = CategoryOffer.objects.filter(category=self.category, is_active=True).first()
        
        product_discount = product_offer.discount_percentage if product_offer else 0
        category_discount = category_offer.discount_percentage if category_offer else 0
        
        total_discount = product_discount + category_discount
        return total_discount

class ProductImages(models.Model):
    images = models.ImageField(upload_to='product_images', default='product.jpg')
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Product Images'

class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_attributes')
    size = models.ForeignKey(Size, on_delete=models.CASCADE, default=None, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=1.99)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.IntegerField(default=1)
    is_blocked = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    related = models.ManyToManyField('self', blank=True)
    date = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.size:
            return f"{self.product.title} - {self.size.size} - Price: {self.price}"
        else:
            return f"{self.product.title} - No Size - Price: {self.price}"

    def reduce_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
            return True
        return False

    def check_stock(self, quantity):
        return self.stock >= quantity


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_attribute = models.ForeignKey(ProductAttribute, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.product.title}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    quantity = models.PositiveBigIntegerField(default=1)
    is_deleted = models.BooleanField(default=False)
    size = models.CharField(max_length=10, blank=True, null=True)
    

    def product_image(self):
        first_image = self.product.p._images.first()
        if first_image:
            return first_image.Images.url
        return None
    
    def __str__(self):
        return f'{self.quantity} x {self.product} in {self.cart}'

class CartOrder(models.Model):
    STATUS = (
        ('New', 'New'),
        ('Paid', 'Paid'),
        ('Shipped', 'Shipped'),
        ('Confirmed', 'Confirmed'),
        ('Pending', 'Pending'),
        ('Payment Pending', 'Payment Pending'),
        ('Delivered', 'Delivered'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Return Requested', 'Return Requested'),
        ('Return Approved', 'Return Approved'),
        ('Return Rejected', 'Return Rejected'),
        ('Failed', 'Failed'),  # Add this for failed payment scenarios
    )

    payment_choices = (
        ('COD', 'COD'),
        ('Razorpay', 'Razorpay'),
        ('Wallet', 'Wallet'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    wallet_balance_used = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=100, choices=payment_choices)
    order_number = models.CharField(max_length=20, default=None)
    order_total = models.FloatField(null=True, blank=True)
    discounts = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_ordered = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=True)
    updated_at = models.DateTimeField(auto_now=True)
    selected_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    order_address = models.CharField(max_length=100, null=False, blank=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)  # New field for payment signature
    status = models.CharField(max_length=20, choices=STATUS, default='Pending')
    return_request_status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='None'
    )
    return_reason = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Cart Orders"

    def __str__(self):
        return self.order_number

    def clear_cart(self):
        cart = Cart.objects.filter(user=self.user).first()
        if cart:
            cart.items.all().delete()


class ProductOrder(models.Model):
    order = models.ForeignKey(CartOrder, related_name='items', on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    size = models.CharField(max_length=10, null=True, blank=True)
    product_price = models.FloatField(default=0)
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    variations = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.product.title} - {self.quantity} x {self.product_price}"

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.PositiveIntegerField(help_text='discount in percentage')
    active = models.BooleanField(default=True)
    active_date = models.DateField()
    expiry_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_active(self):
        today = timezone.now().date()
        return self.active and self.active_date <= today <= self.expiry_date

    def apply_discount(self, total_amount):
        if self.is_active():
            discount_amount = (self.discount / 100) * total_amount
            return total_amount - discount_amount
        return total_amount

from django.utils.timezone import now

from django.utils.timezone import now

class ProductOffer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.PositiveIntegerField(help_text='Discount in percentage')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def is_currently_active(self):
        """
        Dynamically check if the offer is active based on start and end dates.
        """
        today = now().date()
        return self.is_active and self.start_date <= today <= self.end_date


class CategoryOffer(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    discount_percentage = models.PositiveIntegerField(help_text='Discount in percentage')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def is_currently_active(self):
        """
        Dynamically check if the offer is active based on start and end dates.
        """
        today = now().date()
        return self.is_active and self.start_date <= today <= self.end_date



class ReturnReason(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE)
    sizing_issues = models.BooleanField(default=False)
    damaged_item = models.BooleanField(default=False)
    incorrect_order = models.BooleanField(default=False)
    delivery_delays = models.BooleanField(default=False)
    customer_service = models.BooleanField(default=False)
    other_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Return Reason for Order {self.order.id} by {self.user.username}'