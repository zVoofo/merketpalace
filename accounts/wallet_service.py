from decimal import Decimal
from django.db import transaction
from .models import Wallet, WalletTransaction


def get_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def deposit(user, amount: Decimal, description: str = 'Пополнение кошелька'):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError('Сумма должна быть больше нуля')
    wallet = get_wallet(user)
    wallet.balance += amount
    wallet.save(update_fields=['balance'])
    WalletTransaction.objects.create(
        wallet=wallet, amount=amount,
        tx_type=WalletTransaction.TxType.DEPOSIT,
        description=description,
    )
    return wallet


@transaction.atomic
def pay_from_wallet(user, amount: Decimal, order=None, description: str = 'Оплата заказа'):
    amount = Decimal(str(amount))
    wallet = get_wallet(user)
    if wallet.balance < amount:
        raise ValueError('Недостаточно средств на кошельке')
    wallet.balance -= amount
    wallet.save(update_fields=['balance'])
    WalletTransaction.objects.create(
        wallet=wallet, amount=amount,
        tx_type=WalletTransaction.TxType.PAYMENT,
        description=description, order=order,
    )
    return wallet
