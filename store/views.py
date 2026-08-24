from itertools import product
from math import prod

from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from requests.utils import is_valid_cidr

from carts.models import CartItem
from carts.views import _cart_id
from category.models import Category
from orders.models import OrderProduct

from .forms import ReviewForm
from .models import Product, ProductGallery, ReviewRating

# Create your views here.


def store(request, category_slug=None):  # Bringing the store page with pagination
    categories = None
    products = None

    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        paginator = Paginator(products, 6)
        page = request.GET.get("page")
        paged_products = paginator.get_page(page)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True).order_by("id")
        paginator = Paginator(products, 6)
        page = request.GET.get("page")
        paged_products = paginator.get_page(page)
        product_count = products.count()

    context = {
        "products": paged_products,
        "product_count": product_count,
    }
    return render(request, "store/store.html", context)

#detailed products
def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists() # type: ignore
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None

    # Get the reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True) # type: ignore

    # Get the product gallery
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id) # type: ignore

    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
    }
    return render(request, 'store/product_detail.html', context)
  


def search(request):  # Search Functionality by the keyword searched by the user
    if "keyword" in request.GET:
        keyword = request.GET["keyword"]
        if (
            keyword
        ):  # checking if the keyword we searched for blank or not , if it is not blank then if works not if condition not works
            products = Product.objects.order_by("created_date").filter(
                Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
            )
            product_count = products.count()
            context = {
                "products": products,
                "product_count": product_count,
            }
    return render(request, "store/store.html", context)

def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')

    if request.method == 'POST':

        try:
            # Check whether the user has already reviewed this product
            review = ReviewRating.objects.get(
                user=request.user,
                product_id=product_id
            )

            # Existing review -> update it
            form = ReviewForm(request.POST, instance=review)

            if form.is_valid():
                form.save()

                messages.success(
                    request,
                    'Thank you! Your review has been updated.'
                )

        except ReviewRating.DoesNotExist:

            # No existing review -> create a new one
            form = ReviewForm(request.POST)

            if form.is_valid():
                review = form.save(commit=False)

                review.ip = request.META.get('REMOTE_ADDR')
                review.product_id = product_id
                review.user = request.user

                review.save()

                messages.success(
                    request,
                    'Thank you! Your review has been submitted.'
                )
            

        return redirect(url)

    return redirect(url)
            