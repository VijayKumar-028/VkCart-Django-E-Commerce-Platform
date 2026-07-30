import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from carts.models import CartItem
from orders.models import Order

from .forms import OrderForm

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
            }

            return render(request, 'orders/payments.html', context)

    return redirect('checkout')