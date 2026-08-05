import datetime
import json
from email import message
from http.client import PAYMENT_REQUIRED
from turtle import Turtle

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from carts.models import CartItem
from store.models import Product

from .forms import OrderForm
from .models import Order, OrderProduct, Payment
from .paypal import capture_order, create_order
from .services import complete_order


def payments(request):
    body=json.loads(request.body)
    order=Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    #store the transaction details inside payment model
    payment=Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
    )
    payment.save()

    order.payment=payment
    order.is_ordered=True
    order.save()

    #move the cart items to order product table
    cart_items=CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order = order
        orderproduct.payment = payment
        orderproduct.user = request.user
        orderproduct.product = item.product
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id) # type: ignore
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id) # type: ignore
        orderproduct.variations.set(product_variation)
        orderproduct.save()

        # Reduce the quantity of the sold products
        product = Product.objects.get(id=item.product)
        product.stock -= item.quantity
        product.save()
    # Clear cart
    CartItem.objects.filter(user=request.user).delete()

    #send order received mail to user
    mail_subject='Thank you for your order!'
    message=render_to_string('orders/order_received_email.html',{
        'user':request.user,
        'order':order,
    })
    to_email=request.user.email
    send_email=EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    #send order number and trasaction id back to sendData method via jsonresponse

    data={
        'order_number':order.order_number,
        'transID':payment.payment_id,
    }
    return JsonResponse(data)


    

#order placing function 
@login_required(login_url='login')
def place_order(request):
    current_user = request.user

    # Get cart items for the logged-in user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    # If cart is empty, redirect to store
    if cart_count <= 0:
        return redirect('store')

    total = 0
    quantity = 0
    tax = 0
    grand_total = 0

    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity

    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # Store billing information
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order number
            current_date = datetime.date.today().strftime("%Y%m%d")
            data.order_number = current_date + str(data.id) # type: ignore
            data.save()

            order = Order.objects.get(
                user=current_user,
                is_ordered=False,
                order_number=data.order_number
            )

            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'paypal_client_id': settings.PAYPAL_CLIENT_ID,
            }

            return render(request, 'orders/payments.html', context)

    return redirect('checkout')

def order_complete(request):
    order_number=request.GET.get('order_number')
    transID=request.GET.get('payment_id')

    try:
        order=Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products=OrderProduct.objects.filter(order_id=order.id)

        subtotal=0

        for i in ordered_products:
            subtotal+=i.product_price*i.quantity

        payment=Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')
@csrf_exempt
@require_POST
def create_paypal_order(request):

    body = json.loads(request.body)

    amount = body.get("amount")

    paypal_order = create_order(amount)

    return JsonResponse(paypal_order)

@csrf_exempt
@require_POST
def capture_paypal_order(request):

    body = json.loads(request.body)

    paypal_order_id = body.get("paypal_order_id")
    order_number = body.get("order_number")

    paypal_response = capture_order(paypal_order_id)

    if paypal_response.get("status") == "COMPLETED":

        order = Order.objects.get(
            user=request.user,
            order_number=order_number,
            is_ordered=False,
        )

        payment_data = {
            "payment_id": paypal_response["id"],
            "payment_method": "PayPal",
            "status": paypal_response["status"],
        }

        payment = complete_order(
            request,
            order,
            payment_data,
        )

        return JsonResponse({
            "success": True,
            "order_number": order.order_number,
            "payment_id": payment.payment_id,
        })

    return JsonResponse(paypal_response, status=400)