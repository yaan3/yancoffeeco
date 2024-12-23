import random, sweetify
from accounts.backends import EmailBackend
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from .forms import SignUpForm
from .models import User
from accounts.models import *
from django.contrib.auth import get_user_model
from .models import Wallet, Referral, UserManager
import sweetify
from django.db import IntegrityError
from django.core.mail import get_connection
from django.core.mail import EmailMessage
from dotenv import load_dotenv
import os




User = get_user_model()
#=========================================== User Signin, login, logout =========================================================================================================

from django.db import transaction, IntegrityError

def perform_signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        print('sgds')
        if form.is_valid():
            username = form.cleaned_data.get("username")
            email = form.cleaned_data.get("email")
            password1 = form.cleaned_data["password1"]
            password2 = form.cleaned_data["password2"]
            phone_number = form.cleaned_data['phone_number']
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")
            entered_referral_code = form.cleaned_data.get("referral_code", "")
            print('referal', entered_referral_code)
            print('hello')

            if password1 != password2:
                sweetify.toast(request, "Entered passwords don't match", icon='info', timer=3000)
                return redirect("accounts:perform_signup")

            if User.objects.filter(email=email).exists():
                sweetify.toast(request, "Email already used!", icon='info', timer=3000)
                return redirect("accounts:perform_signup")

            referrer = None
            if entered_referral_code:
                try:
                    referrer = Referral.objects.get(my_referral=entered_referral_code)
                except Referral.DoesNotExist:
                    sweetify.toast(request, "Invalid referral code", icon='error', timer=3000)
                    return redirect("accounts:perform_signup")

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        first_name=first_name,
                        last_name=last_name,
                        username=username,
                        phone_number=phone_number,
                        email=email,
                        password=password1,
                    )

                    if referrer:
                        referrer_wallet = Wallet.objects.get(user=referrer.user)
                        referrer_wallet.balance += 250
                        referrer_wallet.save()

                        WalletHistory.objects.create(
                            wallet=referrer_wallet,
                            transaction_type="Credit",
                            amount=250,
                            reason="Referral bonus for referring a new user"
                        )

                        user_wallet = Wallet.objects.get(user=user)
                        user_wallet.balance += 250
                        user_wallet.save()

                        WalletHistory.objects.create(
                            wallet=user_wallet,
                            transaction_type="Credit",
                            amount=250,
                            reason="Referral bonus for signing up using a referral code"
                        )
                    else:
                        sweetify.toast(request, "User already has a wallet", icon='error', timer=3000)

            except IntegrityError as e:
                print(f"Error during signup: {str(e)}") 
                sweetify.toast(request, "An error occurred during signup: " + str(e), icon='error', timer=3000)
                return redirect("accounts:perform_signup")

            request.session["user_id"] = user.username
            sent_otp(request) 
            return render(request, "account/otp.html", {"email": email})
    else:
        form = SignUpForm()

    context = {
        "title": "Signup",
        "form": form,
    }
    return render(request, "account/signup.html", context)



@never_cache
def perform_login(request):
    if request.user.is_authenticated:
        sweetify.toast(request, "You are already logged in", icon='warning', timer=3000)
        return redirect("store:home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                sweetify.toast(request, "Access restricted!", icon='warning', timer=3000)
                return redirect("accounts:login")
        except User.DoesNotExist:
            sweetify.toast(request, "User doesn't Exist", icon='warning', timer=3000)
            return redirect("accounts:login")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.verified:
                login(request, user)
                request.session["user_logged_in"] = True
                sweetify.toast(request, f"You have logged in as {user.username}", icon='success', timer=3000)
                return redirect("store:home")
            else:
                sweetify.toast(request, "Please verify your account using OTP", icon='error', timer=3000)
                request.session["user_id"] = user.id
                sent_otp(request)
                return redirect("accounts:otp_verification_login")
        else:
            sweetify.toast(request, "Invalid username or password", icon='warning', timer=3000)
            return redirect("accounts:login")
    context = {
        "title": "Login",
    }
    return render(request, "account/login.html", context)


@never_cache
def perform_logout(request):
    logout(request)
    sweetify.toast(request, "You have logged out", icon='success', timer=3000)
    return redirect("store:home")


#=========================================== Send, resend and verify otp =========================================================================================================


def sent_otp(request):
    otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
    request.session["otp"] = otp

    email = request.POST.get("email")
    subject = "OTP for Sign Up"
    message = f"Your OTP for sign up is {otp}. Please use this code to complete your registration."

    connection = get_connection(
                host='smtp.gmail.com',
                port=587,
                username='amalnian@gmail.com',
                password='esfw uaoj yxpu qzwk',
                use_tls=True,
    )

    email_message = EmailMessage(subject, message, 'amalnian@gmail.com', [email], connection=connection)
    email_message.send()

    return render(request, "account/otp.html")




def resend_otp(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if user:
            otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
            request.session["otp"] = otp
            
            subject = "OTP for Sign Up"
            message = f"Your OTP for sign up is {otp}. Please use this code to complete your registration."

            connection = get_connection(
                host='smtp.gmail.com',
                port=587,
                username='amalnian@gmail.com',
                password='esfw uaoj yxpu qzwk',
                use_tls=True,
            )

            email_message = EmailMessage(subject, message, 'amalnian@gmail.com', [email], connection=connection)
            email_message.send()

            sweetify.toast(request, "OTP has been resent successfully!", icon='success', timer=3000)
        else:
            sweetify.toast(request, "User with this email does not exist!", icon='error', timer=3000)
        
        return redirect("accounts:otp_verification")
    
    return render(request, "account/resend_otp.html")


def otp_verification(request):
    if request.method == "POST":
        otp_ = request.POST.get("otp")
        user_id = request.session.get("user_id")
        print('inside verify')

        if otp_ == request.session.get("otp"):
            user = User.objects.get(username=user_id)
            print('user id and name', user, user_id)
            user.verified = True
            user.save()
            request.session.flush()  
            sweetify.toast(request, "OTP verified successfully.", icon='success', timer=3000)

            user = authenticate(request, username=user.username, password=user.password)

            if user is not None:
                login(request, user)
                return redirect("store:home")
            else:
                return redirect("accounts:login")
        else:
            sweetify.toast(request, "Invalid OTP. Please try again.", icon='error', timer=3000)
            return redirect("accounts:otp_verification")

    return render(request, "account/otp.html")


def otp_verification_login(request):
    if request.method == "POST":
        otp_ = request.POST.get("otp")
        user_id = request.session.get("user_id")
        user = User.objects.all()

        if otp_ == request.session["otp"]:
            user = User.objects.get(id=user_id)
            user.verified = True
            user.save()
            request.session.flush()
            sweetify.toast(request, "OTP verified successfully.", icon='success', timer=3000)

            user = authenticate(request, user=user)

            if user is not None:
                login(request, user)
                return redirect("store:home")
            else:
                return redirect("accounts:login") 
        else:
            sweetify.toast(request, "Invalid OTP. Please try again.", icon='error', timer=3000)
            return redirect("accounts:otp_verification")
    else:
        return render(request, "account/otp1.html")