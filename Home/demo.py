from .models import Pizza, Orders, Address, Profile, Contact
from django import forms
from django.views.generic.edit import FormMixin
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView


# Form for adding pizza to cart
class AddToCartForm(forms.Form):
    sno = forms.IntegerField(widget=forms.HiddenInput())


# Menu ListView with formMixin for handling POST
class MenuListView(LoginRequiredMixin, FormMixin, ListView):
    model = Pizza
    template_name = "Home/menu.html"
    context_object_name = "pizzas"
    login_url = "/log_in/"
    redirect_field_name = "next"
    form_class = AddToCartForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user
        current_user = self.request.user

        # Calculate total orders quantity
        orders_of_current_user = Orders.objects.filter(User=current_user)
        total_orders_list = [
            order.quantity for order in orders_of_current_user]
        context['totalOrders'] = sum(
            total_orders_list) if total_orders_list else 0

        # Get first order object if exists
        context['firstobjectofcurrentuser'] = orders_of_current_user.first()

        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        try:
            sno = form.cleaned_data['sno']

            # Get pizza details
            pizza = get_object_or_404(Pizza, sno=sno)
            p_name = pizza.Pizza_name
            p_desc = pizza.Pizza_desc
            p_price = pizza.Pizza_price

            # Check if user has an address
            if not Address.objects.filter(User=self.request.user).exists():
                messages.success(self.request, "Please provide an address!")
                return redirect("/profile/")

            # Handle quantity in menu
            existing_order = Orders.objects.filter(
                User=self.request.user, Pizza_name=p_name)

            if not existing_order.exists():
                # Create new order
                Orders.objects.create(
                    Pizza_name=p_name,
                    Pizza_desc=p_desc,
                    Pizza_price=p_price,
                    User=self.request.user
                )
            else:
                # Update quantity of existing order
                order = existing_order.first()
                if order.quantity == 0:
                    existing_order.update(quantity=1)
                else:
                    existing_order.update(quantity=order.quantity + 1)

            return redirect("menu")

        except Exception as e:
            messages.error(self.request, f"An error occurred: {str(e)}")
            return redirect(self.login_url)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid form submission")
        return self.get(self.request)


# Pizza Detail View
class PizzaDetailView(LoginRequiredMixin, DetailView):
    model = Pizza
    template_name = "Home/pizza_detail.html"
    context_object_name = "pizza"
    pk_url_kwarg = "sno"
    login_url = "/log_in/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current user orders
        current_user = self.request.user
        orders_of_current_user = Orders.objects.filter(User=current_user)

        # Calculate total orders
        total_orders_list = [
            order.quantity for order in orders_of_current_user]
        context['totalOrders'] = sum(
            total_orders_list) if total_orders_list else 0

        return context


# Cart/Orders ListView
class OrderListView(LoginRequiredMixin, ListView):
    model = Orders
    template_name = "Home/cart.html"
    context_object_name = "orders"
    login_url = "/log_in/"

    def get_queryset(self):
        return Orders.objects.filter(User=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate total price
        orders = self.get_queryset()
        total_price = sum(order.Pizza_price *
                          order.quantity for order in orders)
        context['total_price'] = total_price

        # Calculate total orders
        total_orders = sum(order.quantity for order in orders)
        context['totalOrders'] = total_orders

        return context


# Profile View
class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "Home/profile.html"
    context_object_name = "user_profile"
    login_url = "/log_in/"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user profile
        user_profile = Profile.objects.filter(User=self.request.user).first()
        if not user_profile:
            user_profile = Profile.objects.create(User=self.request.user)
        context['profile'] = user_profile

        # Get user address
        user_address = Address.objects.filter(User=self.request.user).first()
        context['address'] = user_address

        # Calculate total orders
        orders = Orders.objects.filter(User=self.request.user)
        total_orders = sum(order.quantity for order in orders)
        context['totalOrders'] = total_orders

        return context


# Address Form for creating/updating address
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }


# Address Create/Update View
class AddressCreateUpdateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = "Home/address_form.html"
    success_url = reverse_lazy('profile')
    login_url = "/log_in/"

    def form_valid(self, form):
        # Set the user before saving
        form.instance.User = self.request.user

        # Check if an address already exists for this user
        existing_address = Address.objects.filter(
            User=self.request.user).first()
        if existing_address:
            # Update the existing address instead of creating a new one
            existing_address.address = form.cleaned_data['address']
            existing_address.save()
            messages.success(self.request, "Address updated successfully!")
            return HttpResponseRedirect(self.get_success_url())

        messages.success(self.request, "Address added successfully!")
        return super().form_valid(form)


# Profile Update Form
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_Image']
        widgets = {
            'profile_Image': forms.FileInput(attrs={'class': 'form-control'})
        }


# Profile Update View
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileUpdateForm
    template_name = "Home/profile_update.html"
    success_url = reverse_lazy('profile')
    login_url = "/log_in/"

    def get_object(self):
        # Get or create profile for the current user
        profile, created = Profile.objects.get_or_create(
            User=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully!")
        return super().form_valid(form)


# Contact Form
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['query']
        widgets = {
            'query': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'})
        }


# Contact Create View
class ContactCreateView(LoginRequiredMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = "Home/contact.html"
    success_url = reverse_lazy('contact')
    login_url = "/log_in/"

    def form_valid(self, form):
        # Set the user before saving
        form.instance.User = self.request.user
        messages.success(
            self.request, "Your message has been sent successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate total orders for navbar display
        orders = Orders.objects.filter(User=self.request.user)
        total_orders = sum(order.quantity for order in orders)
        context['totalOrders'] = total_orders

        return context


# URLs configuration
"""
from django.urls import path
from .views import (
    MenuListView, 
    PizzaDetailView, 
    OrderListView, 
    ProfileView,
    AddressCreateUpdateView,
    ProfileUpdateView,
    ContactCreateView
)

urlpatterns = [
    path('menu/', MenuListView.as_view(), name='menu'),
    path('pizza/<int:sno>/', PizzaDetailView.as_view(), name='pizza_detail'),
    path('cart/', OrderListView.as_view(), name='cart'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('address/', AddressCreateUpdateView.as_view(), name='address'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('contact/', ContactCreateView.as_view(), name='contact'),
]
"""
