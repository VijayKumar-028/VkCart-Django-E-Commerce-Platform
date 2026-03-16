from decimal import Decimal
from itertools import product

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from store.models import Product

from .models import Cart, CartItem

# Create your views here.


def _cart_id(
    request,
):  # getting the session id for the not logged in user, if a user is not login and also had no session id we will be creating the session id
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):  # adding the products to cart
    product = get_object_or_404(Product, id=product_id)  # to get the product

    try:
        cart = Cart.objects.get(
            cart_id=_cart_id(request)
        )  # get the cart using the cart_id present in the session
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
        cart_item.save()
    return redirect("cart")


def remove_cart(  # removing the cart specific prodcuts
    request, product_id
):  # this function helps to decrease the product quantity in the cart
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect("cart")


def remove_cart_item(  # this function is used to remove the direct product from the cart, it is shown as the remove(red button) in the cart
    request, product_id
):  # this function is to delete the cart item not for decreasing the quantity
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        cart_item.delete()
    except CartItem.DoesNotExist:
        pass

    return redirect("cart")


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
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
