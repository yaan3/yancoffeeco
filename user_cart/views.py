import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache, cache_control
from django.template.loader import get_template, render_to_string
from django.db import IntegrityError
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from io import BytesIO


import uuid
import random
import logging
from decimal import Decimal
from datetime import datetime

from store.models import *
from accounts.models import Address, Wallet
from store.decorators import blocked_user_required
from user_cart.utils import render_to_pdf

import sweetify
import razorpay
from xhtml2pdf import pisa



logger = logging.getLogger(__name__)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


#=========================================== view, add, remove, increase, decrease in cart =================================================================================================================================


@blocked_user_required
@login_required
def view_cart(request):
    if request.session.get('order_success'):
        del request.session['order_success']
        return render(request, 'user_cart/cart.html', {'cart_items': [], 'total_cart_price': 0, 'discounts': 0, 'total_after_discount': 0})

    user = request.user
    # Filter cart items to exclude blocked products
    items = CartItem.objects.filter(user=user, is_deleted=False, product__is_blocked=False)
    total_cart_price = Decimal(0)
    cart_items = []

    for cart_item in items:
        product_attribute = cart_item.product
        if product_attribute:
            price = product_attribute.price
            cart_item.subtotal = price * cart_item.quantity
            total_cart_price += cart_item.subtotal
            cart_items.append(cart_item)

    discounts = Decimal(0)
    applied_coupon_id = request.session.get('applied_coupon_id')

    if request.method == "POST":
        if 'apply_coupon' in request.POST:
            coupon_code = request.POST.get('coupon_code')
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(
                        code=coupon_code,
                        active=True,
                        active_date__lte=timezone.now(),
                        expiry_date__gte=timezone.now()
                    )
                    discounts = (total_cart_price * coupon.discount) / 100
                    request.session['applied_coupon_id'] = coupon.id
                    sweetify.toast(request, f"Coupon {coupon_code} applied successfully!", icon='success', timer=3000)
                except Coupon.DoesNotExist:
                    sweetify.toast(request, "Invalid coupon code or the coupon has expired.", icon='error', timer=3000)
        
        elif 'remove_coupon' in request.POST:
            if applied_coupon_id:
                del request.session['applied_coupon_id']
                sweetify.toast(request, "Coupon removed successfully.", icon='success', timer=3000)
            return redirect('cart:view_cart')

    if applied_coupon_id and not discounts:
        try:
            coupon = Coupon.objects.get(id=applied_coupon_id, active=True)
            discounts = (total_cart_price * coupon.discount) / 100
        except Coupon.DoesNotExist:
            del request.session['applied_coupon_id']
            messages.error(request, "The applied coupon is no longer valid.")
    total_after_discount = total_cart_price - discounts

    context = {
        'cart_items': cart_items,
        'total_cart_price': total_cart_price,  # This remains the sum of the original prices
        'discounts': discounts,
        'total_after_discount': total_after_discount,  # This shows the total after applying the discount
        'coupons': Coupon.objects.filter(active=True),  # Show available coupons
    }

    return render(request, 'user_cart/cart.html', context)
        




@blocked_user_required
@login_required
def add_to_cart(request):
    try:
        # Retrieve data from the POST request
        product_id = request.POST.get('product_id')
        product_attr_id = request.POST.get('selected_size')
        quantity = request.POST.get('quantity', 1)

        # Validate product ID
        if not product_id:
            sweetify.toast(request, 'Invalid product.', icon='error')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Validate size selection
        if not product_attr_id:
            sweetify.toast(request, 'Please select a size before adding the product to the cart.', icon='error')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            sweetify.toast(request, 'Invalid quantity. Please select a valid quantity.', icon='error')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Get the product attribute (variant)
        product_attr = get_object_or_404(ProductAttribute, id=product_attr_id)

        # Check stock availability and enforce max limit before creating cart item
        cart = Cart.objects.get_or_create(user=request.user)[0]

        # Check if the product is already in the cart
        existing_cart_item = CartItem.objects.filter(user=request.user, cart=cart, product=product_attr).first()
        current_quantity = existing_cart_item.quantity if existing_cart_item else 0

        # Determine the new total quantity
        new_total_quantity = current_quantity + quantity

        if new_total_quantity > 5:  # Enforce max limit of 5
            sweetify.toast(request, "You cannot add more than 5 items of this product to your cart.", icon='error')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        if new_total_quantity > product_attr.stock:  # Enforce stock limit
            sweetify.toast(request, f"Only {product_attr.stock} items are available in stock.", icon='error')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Add or update the CartItem after validation
        if existing_cart_item:
            existing_cart_item.quantity = new_total_quantity
            existing_cart_item.save()
        else:
            CartItem.objects.create(
                user=request.user,
                cart=cart,
                product=product_attr,
                quantity=quantity
            )

        # Remove the product from the wishlist (if it exists)
        Wishlist.objects.filter(user=request.user, product_attribute=product_attr).delete()

        # Success message
        sweetify.toast(request, 'Product successfully added to cart.', icon='success')

    except ProductAttribute.DoesNotExist:
        sweetify.toast(request, 'The selected product variant does not exist.', icon='error')
    except Exception as e:
        logger.error(f"Unexpected error in add_to_cart: {e}")
        sweetify.toast(request, 'An unexpected error occurred. Please try again.', icon='error')

    # Redirect back to the appropriate page
    return redirect(request.META.get('HTTP_REFERER', '/'))





def redirect_to_source(source, product_id):
    """
    Redirect based on the source of the add-to-cart action.
    """
    if source == 'wishlist':
        return redirect('store:wishlist')
    elif source == 'product_detail':
        return redirect('store:product_view', product_pid=product_id)
    return redirect('store:product_list')





@blocked_user_required
@login_required
def increase_quantity(request, cart_item_id, cart_id):
    try:
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart_id=cart_id)
        product_attribute = cart_item.product

        # Check if quantity exceeds stock
        if cart_item.quantity + 1 > product_attribute.stock:
            return JsonResponse({'error': 'Cannot add more than available stock.'}, status=202)

        if cart_item.quantity < 5:  # Check max limit
            cart_item.quantity += 1
            cart_item.save()
            total = cart_item.quantity * product_attribute.price
            total_sum = sum(item.quantity * item.product.price for item in CartItem.objects.filter(cart_id=cart_id))
            return JsonResponse({'q': cart_item.quantity, 'total': total, 'total_sum': total_sum}, status=200)
        else:
            return JsonResponse({'error': 'Max limit reached for this product.'}, status=202)

    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found.'}, status=404)



@blocked_user_required
@login_required
def decrease_quantity(request, cart_item_id, cart_id):
    try:
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart_id=cart_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            total = cart_item.quantity * cart_item.product.price
            total_sum = sum(item.quantity * item.product.price for item in CartItem.objects.filter(cart_id=cart_id))
            return JsonResponse({'q': cart_item.quantity, 'total': total, 'total_sum': total_sum}, status=200)
        else:
            return JsonResponse({'error': 'Quantity cannot be less than 1'}, status=400)
    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)
   

@blocked_user_required
@login_required
@require_POST
def remove_from_cart(request, cart_item_id):
    
    cart_item = get_object_or_404(CartItem, pk=cart_item_id)
    cart_item.delete()
    sweetify.toast(request, 'Item removed from cart successfully',timer=3000, icon='success')
    return JsonResponse({'message': 'Item removed from cart successfully'}, status=200)


#=========================================== apply coupon =================================================================================================================================


@blocked_user_required
@login_required
def apply_coupon(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if coupon.is_active():
                request.session['coupon_id'] = coupon.id
                messages.success(request, "Coupon applied successfully!")
            else:
                messages.error(request, "Coupon is expired or inactive.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    return redirect('cart:view_cart')


#=========================================== checkout and payment method selection =================================================================================================================================

from razorpay.errors import SignatureVerificationError


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def verify_razorpay_signature(order_id, payment_id, signature):
    """Verify the Razorpay payment signature."""
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature,
    }
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        return True
    except SignatureVerificationError:
        return False

@blocked_user_required
@login_required
def checkout(request):
    if request.session.get('payment_completed'):
        return redirect('cart:view_cart')
    
    if request.session.get('order_success'):
        del request.session['order_success']
        return render(request, 'user_cart/cart.html', {'cart_items': [], 'total_cart_price': 0, 'discounts': 0, 'total_after_discount': 0})

    user = request.user
    user_cart = Cart.objects.filter(user=user).first()  # Retrieve user's cart
    total_cart_price = Decimal(0)  # Initialize total cart price
    cart_items = []

    if user_cart:
        # Retrieve all cart items for the user, excluding blocked products
        cart_items = user_cart.items.filter(product__is_blocked=False)
        for cart_item in cart_items:
            product = cart_item.product  # Get the product for the cart item
            cart_item.subtotal = product.price * cart_item.quantity  # Calculate the subtotal for each item
            total_cart_price += cart_item.subtotal  # Add item subtotal to total cart price

    # Apply discounts if a coupon is used
    applied_coupon_id = request.session.get('applied_coupon_id')
    discounts = 0
    if applied_coupon_id:
        try:
            applied_coupon = Coupon.objects.get(id=applied_coupon_id, active=True,
                                                active_date__lte=timezone.now(), expiry_date__gte=timezone.now())
            discounts = (total_cart_price * applied_coupon.discount) / 100  # Calculate the discount
        except Coupon.DoesNotExist:
            request.session.pop('applied_coupon_id', None)

    total_after_discount = total_cart_price - discounts  # Calculate total after discount

    if request.method == 'POST':
        selected_address_id = request.POST.get('existing_address')  # Get the selected address from form
        if selected_address_id:
            try:
                selected_address = Address.objects.get(id=selected_address_id, user=user)  # Get the address
                order_number = str(uuid.uuid4())[:12]  # Generate a unique order number
                new_order = CartOrder.objects.create(
                    user=user,
                    order_number=order_number,
                    order_total=total_after_discount,
                    selected_address=selected_address,
                    discounts=discounts,
                    order_address=selected_address,
                    status='Payment Pending'  # Initially, the order status is 'Payment Pending'
                )

                # Create product orders based on the cart items
                for item in cart_items:
                    ProductOrder.objects.create(
                        order=new_order,
                        user=user,
                        product=item.product.product,
                        quantity=item.quantity,
                        product_price=item.product.price,
                        ordered=True,
                        size=item.product.size,
                        variations=item.product
                    )

                # Store the order ID in the session to process payment
                request.session['order_id'] = new_order.id

                # Redirect to payment method selection page
                return redirect('cart:payment_method_selection', order_id=new_order.id)  # Redirect to payment page
            except Address.DoesNotExist:
                sweetify.toast(request, "Selected address does not exist.", icon='error', timer=3000)
        else:
            sweetify.toast(request, "Please select an address.", icon='error', timer=3000)

    # Provide context to render the checkout page
    context = {
        'items': cart_items,  # List of cart items with their subtotal
        'total_cart_price': total_cart_price,  # Total cart price before discounts
        'discounts': discounts,  # Applied discounts
        'total_after_discount': total_after_discount,  # Total price after discounts
        'user_addresses': Address.objects.filter(user=user),  # Available addresses for the user
    }
    return render(request, 'user_cart/checkout.html', context)




@blocked_user_required
@login_required
def payment_method_selection(request, order_id):
    try:
        order = CartOrder.objects.get(id=order_id, user=request.user)
    except CartOrder.DoesNotExist:
        sweetify.toast(request, "Order does not exist.", icon='error', timer=5000)
        return redirect('cart:checkout')

    items = CartItem.objects.filter(cart=order.user.cart, is_deleted=False)
    total_cart_price = sum(item.product.price * item.quantity for item in items)
    discounts = order.discounts or 0
    total_after_discount = total_cart_price - discounts

    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance = wallet.balance
    except Wallet.DoesNotExist:
        wallet_balance = Decimal(0)

    if request.method == 'POST':
        selected_payment_method = request.POST.get('payment_method')

        if selected_payment_method == 'COD':
            if total_after_discount <= 1000:
                order.payment_method = selected_payment_method
                order.status = 'Pending'
                order.save()

                # Deduct stock for each item in the order
                for item in items:
                    product_attribute = item.product
                    if not product_attribute.reduce_stock(item.quantity):
                        sweetify.toast(request, f"Insufficient stock for {product_attribute.product.title}.", icon='error', timer=5000)
                        return redirect('store:product_view', product_pid=product_attribute.product.id)
                    product_attribute.save()

                order.clear_cart()
                request.session['payment_completed'] = True
                return redirect('cart:order_success', order.id)
            else:
                sweetify.toast(request, "COD is not available for orders above ₹1000.", icon='error', timer=5000)

        elif selected_payment_method == 'Wallet':
            if wallet_balance >= total_after_discount:
                wallet.balance -= total_after_discount
                wallet.save()
                WalletHistory.objects.create(wallet=wallet, transaction_type='Debit', amount=total_after_discount, reason='Purchased Products')

                order.payment_method = selected_payment_method
                order.status = 'Completed'
                order.save()

                # Deduct stock for each item in the order
                for item in items:
                    product_attribute = item.product
                    if not product_attribute.reduce_stock(item.quantity):
                        sweetify.toast(request, f"Insufficient stock for {product_attribute.product.title}.", icon='error', timer=5000)
                        return redirect('store:product_view', product_pid=product_attribute.product.id)
                    product_attribute.save()

                order.clear_cart()
                request.session['payment_completed'] = True
                return redirect('cart:order_success', order.id)
            else:
                sweetify.toast(request, "Insufficient wallet balance.", icon='error', timer=5000)

        elif selected_payment_method == 'Razorpay':
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            if verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
                order.payment_method = selected_payment_method
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = razorpay_signature
                order.status = 'Completed'
                order.save()

                # Deduct stock for each item in the order
                for item in items:
                    product_attribute = item.product
                    if not product_attribute.reduce_stock(item.quantity):
                        sweetify.toast(request, f"Insufficient stock for {product_attribute.product.title}.", icon='error', timer=5000)
                        return redirect('store:product_view', product_pid=product_attribute.product.id)
                    product_attribute.save()

                order.clear_cart()
                request.session['payment_completed'] = True
                return redirect('cart:order_success', order.id)
            else:
                sweetify.toast(request, 'Payment verification failed. Please retry.', icon='error', timer=3000)

    # Create Razorpay Order
    razorpay_data = {
        "amount": int(total_after_discount * 100),
        "currency": "INR",
        "receipt": f"order_{order.id}",
        "payment_capture": 1,
    }
    try:
        razorpay_order = razorpay_client.order.create(data=razorpay_data)
        order.razorpay_order_id = razorpay_order['id']
        order.save()
    except Exception:
        sweetify.toast(request, 'Failed to create Razorpay order.', icon='error', timer=5000)
        return redirect('cart:checkout')

    context = {
        'order': order,
        'items': items,
        'total_cart_price': total_cart_price,
        'discounts': discounts,
        'total_after_discount': total_after_discount,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'wallet_balance': wallet_balance,
    }

    return render(request, 'user_cart/payment_method_selection.html', context)


@csrf_exempt
@login_required
def razorpay_repayment(request, order_id):
    try:
        # Fetch the order for the user
        order = CartOrder.objects.get(id=order_id, user=request.user)
    except CartOrder.DoesNotExist:
        sweetify.toast(request, "Order not found.", icon="error", timer=3000)
        return redirect("cart:order_view", order_id=order_id)

    # Ensure Razorpay order ID exists
    if not order.razorpay_order_id:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = {
            "amount": int(order.order_total * 100),  # Amount in paise
            "currency": "INR",
            "receipt": f"repayment_{order.id}",
        }
        try:
            razorpay_order = client.order.create(data=payment_data)
            order.razorpay_order_id = razorpay_order["id"]
            order.save()
        except Exception as e:
            sweetify.toast(request, "Failed to create Razorpay order.", icon="error", timer=5000)
            return redirect("cart:order_detail", order_id=order_id)

    return render(request, "dashboard/user_order_detail.html", {
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID
    })


from decimal import Decimal
import razorpay
from django.conf import settings

def user_order_detail(request, order_id):
    try:
        order = CartOrder.objects.get(id=order_id, user=request.user)
    except CartOrder.DoesNotExist:
        sweetify.toast(request, "Order not found.", icon="error", timer=5000)
        return redirect("cart:order_history")

    # Generate Razorpay Order ID if it doesn't exist
    if not order.razorpay_order_id:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = {
            "amount": int(order.order_total * 100),  # Amount in paise
            "currency": "INR",
            "receipt": f"order_{order.id}",
        }
        try:
            razorpay_order = client.order.create(data=payment_data)
            order.razorpay_order_id = razorpay_order["id"]
            order.save()
        except Exception as e:
            sweetify.toast(request, "Failed to create Razorpay order.", icon="error", timer=5000)
            return redirect("cart:order_history")

    context = {
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,  # Pass key to template
    }
    return render(request, "user_cart/user_order_detail.html", context)


import razorpay
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect
from store.models import CartOrder

def razorpay_payment_handler(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            }

            try:
                razorpay_client.utility.verify_payment_signature(params_dict)

                # Payment is successful, update order status
                order = CartOrder.objects.get(id=data['order_id'])
                order.status = 'Completed'  # or 'Payment Successful'
                order.save()

                return JsonResponse({'status': 'success'})
            except razorpay.errors.SignatureVerificationError:
                return JsonResponse({'status': 'error', 'message': 'Invalid payment signature'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})









#=========================================== order success and failure =================================================================================================================================

@blocked_user_required
@login_required
def order_success(request, order_id):
    try:
        order = CartOrder.objects.get(id=order_id, user=request.user)
        product_orders = ProductOrder.objects.filter(order=order)

        # Ensure order status is 'Completed' before proceeding
        if order.status != 'Completed':
            sweetify.toast(request, 'Payment not completed yet.', icon='error', timer=3000)
            return redirect('store:home')

        # Mark cart items as deleted (soft delete)
        CartItem.objects.filter(cart__user=request.user, is_deleted=False).update(is_deleted=True)

        # Clear cart after successful payment
        user_cart = Cart.objects.filter(user=request.user).first()
        if user_cart:
            # This will delete all items in the user's cart
            user_cart.items.all().delete()

        # Clear session variables related to payment
        request.session.pop('payment_completed', None)
        request.session.pop('applied_coupon_id', None)  # Also remove coupon if necessary

        context = {
            'order': order,
            'product_orders': product_orders,
        }
        return render(request, 'user_cart/order_success.html', context)

    except CartOrder.DoesNotExist:
        sweetify.toast(request, 'Order does not exist', icon='error', timer=3000)
        return redirect('store:home')




@blocked_user_required
@login_required
def order_failure(request, order_id):
    try:
        order = CartOrder.objects.get(id=order_id, user=request.user)
        product_orders = ProductOrder.objects.filter(order=order)
    except CartOrder.DoesNotExist:
        sweetify.toast(request, 'Order does not exist', icon='error', timer=3000)

#=========================================== invoice things =================================================================================================================================#


@blocked_user_required
@login_required
def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


@blocked_user_required
@login_required
def order_invoice(request, order_id):
    # Fetch the order and related product orders
    order = get_object_or_404(CartOrder, id=order_id, user=request.user)
    product_orders = ProductOrder.objects.filter(order=order)
    # Calculate the total product price and discount amount
    total_product_price = sum(item.product_price for item in product_orders)
    discount_amount = total_product_price - order.order_total
    discount = order.discounts
    print('discount before= ', discount)

    if order.payment_method == "Wallet-Razorpay":
        wallet_amount_used = order.wallet_balance_used
        razor = int(total_product_price) - int(wallet_amount_used)
    else:
        wallet_amount_used = 0
    razor = int(total_product_price) - int(order.discounts)
    print('razor = ', razor)
    print('wallet amount user', wallet_amount_used)
    # Prepare the context
    context = {
        'order': order,
        'product_orders': product_orders,
        'discount_amount': discount_amount,
        'wallet_amount_used': wallet_amount_used,
        'razor': razor,
        'discount': int(order.discounts)
    }
    
    # Render the HTML content
    html_content = render_to_string('user_cart/invoice.html', context)
    
    # Create a BytesIO buffer to hold the PDF
    buffer = BytesIO()
    
    # Convert HTML to PDF
    pdf = pisa.CreatePDF(html_content, dest=buffer)
    
    # Check for errors
    if pdf.err:
        return HttpResponse("Error generating PDF", status=500)
    
    # Get the PDF content from the buffer
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Return the PDF response
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    return response
