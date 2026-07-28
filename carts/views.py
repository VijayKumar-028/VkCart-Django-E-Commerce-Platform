import http
from decimal import Decimal
from itertools import product

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from store.models import Product, Variation

from .models import Cart, CartItem

# Create your views here.


def _cart_id(request,):  # getting the session id for the not logged in user, if a user is not login and also had no session id we will be creating the session id
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    current_user = request.user
    product = get_object_or_404(Product, id=product_id)

    # Get selected variations
    product_variation = []

    if request.method == "POST":
        for item in request.POST:
            key = item
            value = request.POST[key]

            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value,
                )
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass

   
    # Logged-in User
   
    if current_user.is_authenticated:

        is_cart_item_exists = CartItem.objects.filter(
            product=product,
            user=current_user
        ).exists()

        if is_cart_item_exists:

            cart_items = CartItem.objects.filter(
                product=product,
                user=current_user
            )

            ex_var_list = []
            item_ids = []

            for item in cart_items:
                existing_variation = sorted(
                    list(item.variations.all()),
                    key=lambda x: x.id
                )
                ex_var_list.append(existing_variation)
                item_ids.append(item.id) # type: ignore

            product_variation = sorted(
                product_variation,
                key=lambda x: x.id
            )

            if product_variation in ex_var_list:

                index = ex_var_list.index(product_variation)
                item = CartItem.objects.get(id=item_ids[index])

                item.quantity += 1
                item.save()

            else:

                cart_item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    user=current_user,
                )

                if product_variation:
                    cart_item.variations.add(*product_variation)

        else:

            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                user=current_user,
            )

            if product_variation:
                cart_item.variations.add(*product_variation)

        return redirect(
    request.META.get("HTTP_REFERER", "store")
)

    # Guest User
   
    else:

        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(
                cart_id=_cart_id(request)
            )

        is_cart_item_exists = CartItem.objects.filter(
            product=product,
            cart=cart
        ).exists()

        if is_cart_item_exists:

            cart_items = CartItem.objects.filter(
                product=product,
                cart=cart
            )

            ex_var_list = []
            item_ids = []

            for item in cart_items:
                existing_variation = sorted(
                    list(item.variations.all()),
                    key=lambda x: x.id
                )
                ex_var_list.append(existing_variation)
                item_ids.append(item.id) # type: ignore

            product_variation = sorted(
                product_variation,
                key=lambda x: x.id
            )

            if product_variation in ex_var_list:

                index = ex_var_list.index(product_variation)
                item = CartItem.objects.get(id=item_ids[index])

                item.quantity += 1
                item.save()

            else:

                cart_item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    cart=cart,
                )

                if product_variation:
                    cart_item.variations.add(*product_variation)

        else:

            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
            )

            if product_variation:
                cart_item.variations.add(*product_variation)

        return redirect(request.META.get("HTTP_REFERER", "store")) # this redirect function is used to stay on the same product page after we add any item to the cart by fetching the current product url, if it fails to fetch the url then it redirect to the store page

def remove_cart(  # removing the cart specific prodcuts
    request, product_id, cart_item_id
):  # this function helps to decrease the product quantity in the cart
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart,id=cart_item_id) #to get cart item

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect("cart")


def remove_cart_item(  # this function is used to remove the direct product from the cart, it is shown as the remove(red button) in the cart
    request, product_id,cart_item_id
):  # this function is to delete the cart item not for decreasing the quantity
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        cart_item.delete()
    except CartItem.DoesNotExist:
        pass

    return redirect("cart")


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0

        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(
                user=request.user,
                is_active=True
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(
                cart=cart,
                is_active=True
            )

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

    except ObjectDoesNotExist:
        cart_items = []

    tax = Decimal(total) * Decimal("0.02")
    grand_total = total + tax

    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "tax": tax,
        "grand_total": grand_total,
    }

    return render(request, "store/cart.html", context)

@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):

    try:
        tax = 0
        grand_total = 0

        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(
                user=request.user,
                is_active=True
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(
                cart=cart,
                is_active=True
            )

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

    except ObjectDoesNotExist:
        cart_items = []

    tax = Decimal(total) * Decimal("0.02")
    grand_total = total + tax

    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "tax": tax,
        "grand_total": grand_total,
    }

    return render(request, "store/checkout.html", context)
