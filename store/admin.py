from django.contrib import admin

# from django_allauth import sites
from store.models import *

# Register your models here.

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['c_id', 'c_name', 'c_image', 'is_blocked']


admin.site.register(Category, CategoryAdmin)

class ProductAdmin(admin.ModelAdmin):
    list_display = ['category', 'title', 'image', 'description', 'specifications']

admin.site.register(Product, ProductAdmin)

class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'price', 'old_price', 'stock', 'size']

admin.site.register(ProductAttribute, ProductAttributeAdmin)

# class SubcategoryAdmin(admin.ModelAdmin):
#     list_display = ['sid', 'sub_name', 'category']

# admin.site.register(Subcategory, SubcategoryAdmin)



# admin.site.register(Payments)