from django import forms
from .models import Product
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import date

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'base_price', 'image']

class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email'
        })
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
            'placeholder': 'Дата рождения'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'date_of_birth', 'password1', 'password2')

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Логин'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Пароль'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Повторите пароль'}),
        }



