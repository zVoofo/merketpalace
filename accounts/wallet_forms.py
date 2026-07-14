from django import forms
from decimal import Decimal


class TopUpForm(forms.Form):
    amount = forms.DecimalField(
        min_value=Decimal('100'), max_value=Decimal('500000'),
        decimal_places=2, label='Сумма пополнения (₽)',
        widget=forms.NumberInput(attrs={'placeholder': '1000', 'step': '100'}),
    )
    payment_type = forms.ChoiceField(
        choices=[
            ('card', 'Банковская карта'),
            ('sbp', 'СБП'),
            ('yukassa', 'ЮKassa (демо)'),
        ],
        label='Способ оплаты',
    )
