from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from carts.models import CartItem
from store.models import Product

from .models import OrderProduct, Payment


def complete_order(request, order, payment_data):

    # Store transaction details inside Payment model
    payment = Payment(
        user=request.user,
        payment_id=payment_data["payment_id"],
        payment_method=payment_data["payment_method"],
        amount_paid=order.order_total,
        status=payment_data["status"],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move the cart items to Order Product table
    cart_items = CartItem.objects.filter(user=request.user)

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

        product_variation = item.variations.all()
        orderproduct.variations.set(product_variation)

        # Reduce the quantity of the sold products
        product = item.product
        product.stock -= item.quantity
        product.save()

    # Clear cart
    CartItem.objects.filter(user=request.user).delete()

    # Send order received email to customer
    mail_subject = "Thank you for your order!"
    message = render_to_string(
        "orders/order_received_email.html",
        {
            "user": request.user,
            "order": order,
        },
    )

    send_email = EmailMessage(
        mail_subject,
        message,
        to=[request.user.email],
    )
    send_email.send()

    return payment