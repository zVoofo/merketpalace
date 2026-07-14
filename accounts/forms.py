from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Organization


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Электронная почта')
    first_name = forms.CharField(max_length=100, label='Имя')
    last_name = forms.CharField(max_length=100, required=False, label='Фамилия')
    phone = forms.CharField(max_length=20, required=False, label='Телефон', widget=forms.TextInput(attrs={'placeholder': '+7 900 000-00-00'}))
    account_type = forms.ChoiceField(
        choices=[('buyer', 'Покупатель'), ('seller', 'Продавец')],
        label='Тип аккаунта',
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password1', 'password2')
        labels = {
            'password1': 'Пароль',
            'password2': 'Подтверждение пароля',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone = self.cleaned_data.get('phone') or None
        if self.cleaned_data['account_type'] == 'seller':
            user.active_role = User.ActiveRole.SELLER
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email или логин')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar', 'first_name', 'last_name', 'phone', 'email')
        labels = {
            'avatar': 'Фото профиля',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Телефон',
            'email': 'Электронная почта',
        }
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '+7 900 000-00-00'}),
        }


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ('name', 'inn', 'ogrn', 'legal_address')
        labels = {
            'name': 'Название компании',
            'inn': 'ИНН',
            'ogrn': 'ОГРН',
            'legal_address': 'Юридический адрес',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class VerifyCodeForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, label='Код подтверждения', widget=forms.TextInput(attrs={'placeholder': '000000', 'autocomplete': 'one-time-code'}))
