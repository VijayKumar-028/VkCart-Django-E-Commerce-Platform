


import email
from email.policy import default

from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
#Verification Email
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.forms import RegistrationForm
from carts.models import Cart, CartItem
from carts.views import _cart_id

from .models import Account

# Create your views here.

def register(request):
    if request.method=='POST':
        form=RegistrationForm(request.POST)
        if form.is_valid():
            first_name=form.cleaned_data['first_name']
            last_name=form.cleaned_data['last_name']
            email=form.cleaned_data['email']
            phone_number=form.cleaned_data['phone_number']
            password=form.cleaned_data['password']
            username=email.split('@')[0]
            user=Account.objects.create_user(first_name=first_name, last_name=last_name, email=email, username=username, password=password) # type: ignore
            user.phone_number=phone_number
            user.save()

            #USER ACTIVATION
            current_site=get_current_site(request)
            mail_subject='Please activate your account'
            message=render_to_string('accounts/account_verification_email.html',{
                'user':user,
                'domain':current_site,
                'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                'token':default_token_generator.make_token(user),
            })
            to_email=email
            send_email=EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            

            # messages.success(request, 'Thank You for registering with us, We have sent you a verification mail to your email address. Please verify it.')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
        form=RegistrationForm()
    context={
        'form':form,
    }

    return render(request, 'accounts/register.html', context)

def login(request):
    if request.method=='POST':
        email=request.POST['email']
        password=request.POST['password']

        user=auth.authenticate(email=email, password=password)

        if user is not None:

            try:
                cart=Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exits=CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exits:
                    cart_item=CartItem.objects.filter(cart=cart)


                    for item in cart_item:
                        item.user=user # type: ignore
                        item.save()
            except:
                pass
            auth.login(request, user)
            
            return redirect('home')
        else:
            messages.error(request, 'Invalid Login Credintials')
            return redirect('login')
    return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

#This function is used to activate the user 
def activate(request, uidb64, token):
    try:
        uid=urlsafe_base64_decode(uidb64).decode()
        user=Account._default_manager.get(pk=uid)
    
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user=None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active=True
        user.save()
        messages.success(request, 'Congratulations! Your account is activated.')
        return redirect('login')
    
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')

@login_required(login_url='login')
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

#this function logic is to send the link to the user mail 
def forgotPassword(request):
    if request.method=="POST":
        email=request.POST['email']
        if Account.objects.filter(email=email).exists():
            user=Account.objects.get(email__exact=email)

            #Reset password email
            current_site=get_current_site(request)
            mail_subject='Please activate your account'
            message=render_to_string('accounts/reset_password_email.html',{
                            'user':user,
                            'domain':current_site,
                            'uid':urlsafe_base64_encode(force_bytes(user.pk)),
                            'token':default_token_generator.make_token(user),
                        })
            to_email=email
            send_email=EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            messages.success(request,'Password reset email has been send to your email address.')
            return redirect('login')

        else:
            messages.error(request,'Account does not exist!')
            return redirect('forgotPassword')
    return render(request, 'accounts/forgotPassword.html')


# this function is used to validate the link we send to user mail
def resetPassword_validate(request,uidb64, token):
    try: 
        uid=urlsafe_base64_decode(uidb64).decode()
        user=Account._default_manager.get(pk=uid)

    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user=None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid']=uid
        messages.success(request, 'Please reset your password.')
        return redirect('resetPassword')
    else:
        messages.error(request, 'This link has been expired')
        return redirect('login')

#This function is the actual logic to reset the password
def resetPassword(request):
    if request.method=='POST':
      password=request.POST['password']
      confirm_password=request.POST['confirm_password']

      if password==confirm_password:
          uid=request.session.get('uid')
          user=Account.objects.get(pk=uid)
          user.set_password(password)
          user.save()
          messages.success(request, 'Password reset successful.')
          return redirect('login')
      else:
          messages.error(request, 'Password does not match.')
          return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')
      


    