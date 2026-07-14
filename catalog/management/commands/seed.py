from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from catalog.models import Category, Brand, CarMake, CarModel, SearchRequest
from listings.models import Listing
from accounts.models import Organization, Wallet
from accounts.wallet_service import get_wallet, deposit

User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт демо-данные: категории, пользователей, объявления'

    def handle(self, *args, **options):
        self.stdout.write('Создание категорий...')
        cats = {
            'avto': Category.objects.get_or_create(slug='avto', defaults={'name': 'Авто и запчасти', 'sort_order': 1})[0],
            'elektronika': Category.objects.get_or_create(slug='elektronika', defaults={'name': 'Электроника', 'sort_order': 2})[0],
            'uslugi': Category.objects.get_or_create(slug='uslugi', defaults={'name': 'Услуги', 'sort_order': 3})[0],
            'dom': Category.objects.get_or_create(slug='dom', defaults={'name': 'Дом и сад', 'sort_order': 4})[0],
        }
        zapchasti, _ = Category.objects.get_or_create(slug='zapchasti', defaults={'name': 'Запчасти', 'parent': cats['avto'], 'sort_order': 1})
        telefony, _ = Category.objects.get_or_create(slug='telefony', defaults={'name': 'Телефоны', 'parent': cats['elektronika'], 'sort_order': 1})
        kompyutery, _ = Category.objects.get_or_create(slug='kompyutery', defaults={'name': 'Компьютеры', 'parent': cats['elektronika'], 'sort_order': 2})

        bosch, _ = Brand.objects.get_or_create(slug='bosch', defaults={'name': 'Bosch'})
        apple, _ = Brand.objects.get_or_create(slug='apple', defaults={'name': 'Apple'})
        samsung, _ = Brand.objects.get_or_create(slug='samsung', defaults={'name': 'Samsung'})
        bmw, _ = CarMake.objects.get_or_create(name='BMW')
        lada, _ = CarMake.objects.get_or_create(name='Lada')
        CarModel.objects.get_or_create(make=bmw, name='X5')
        CarModel.objects.get_or_create(make=lada, name='Vesta')

        self.stdout.write('Создание пользователей...')
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@marketplace.local', 'first_name': 'Админ', 'is_verified': True}
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('admin123')
        admin.save()

        seller, created = User.objects.get_or_create(
            username='seller',
            defaults={'email': 'seller@marketplace.local', 'first_name': 'Иван', 'last_name': 'Продавцов', 'active_role': 'seller', 'is_verified': True}
        )
        if created:
            seller.set_password('seller123')
            seller.save()
        seller.active_role = 'seller'
        seller.save(update_fields=['active_role'])
        Organization.objects.get_or_create(user=seller, defaults={'name': 'ООО АвтоЗапчасти', 'inn': '7701234567', 'is_verified': True})

        buyer, created = User.objects.get_or_create(
            username='buyer',
            defaults={'email': 'buyer@marketplace.local', 'first_name': 'Анна', 'last_name': 'Покупателева'}
        )
        if created:
            buyer.set_password('buyer123')
            buyer.save()

        for u in (admin, seller, buyer):
            get_wallet(u)
        if Wallet.objects.get(user=buyer).balance < 1000:
            deposit(buyer, 50000, 'Стартовый баланс для тестов')

        demo = [
            (zapchasti, bosch, 'product', 'Тормозные колодки Bosch BMW X5', 'tormoznye-kolodki-bosch-bmw-x5', 'BP1234', 4500, 5500, 15),
            (telefony, apple, 'product', 'iPhone 15 Pro 256GB', 'iphone-15-pro-256gb', 'IP15P', 119990, 129990, 5),
            (telefony, samsung, 'product', 'Samsung Galaxy S24 Ultra', 'samsung-galaxy-s24-ultra', 'SM-S928', 89990, 99990, 8),
            (zapchasti, bosch, 'product', 'Масляный фильтр Bosch Lada Vesta', 'maslyanyj-filtr-bosch-lada', 'P3274', 450, None, 50),
            (zapchasti, bosch, 'product', 'Свечи зажигания NGK комплект', 'svechi-zazhiganiya-ngk', 'NGK-7841', 1200, 1500, 30),
            (zapchasti, bosch, 'product', 'Амортизатор передний BMW 3 Series', 'amortizator-bmw-3', 'BMW-AM-01', 8500, 9900, 6),
            (kompyutery, apple, 'product', 'MacBook Air M3 256GB', 'macbook-air-m3', 'MBA-M3', 109990, None, 3),
            (kompyutery, samsung, 'product', 'Монитор Samsung 27" 144Hz', 'monitor-samsung-27', 'SAM-M27', 24990, 27990, 12),
            (cats['dom'], None, 'product', 'Перфоратор Bosch GBH 2-26', 'perforator-bosch-gbh', 'GBH-226', 15990, 17990, 4),
            (cats['uslugi'], None, 'service', 'Диагностика автомобиля', 'diagnostika-avtomobilya', None, 2500, None, 999),
            (cats['uslugi'], None, 'service', 'Замена масла и фильтров', 'zamena-masla', None, 3500, None, 999),
            (zapchasti, bosch, 'product', 'Ремень ГРМ комплект Gates', 'remen-grm-gates', 'GAT-K015', 6200, None, 10),
            (telefony, apple, 'product', 'AirPods Pro 2', 'airpods-pro-2', 'APP2', 21990, 24990, 20),
            (zapchasti, bosch, 'product', 'Колодки тормозные задние Toyota Camry', 'kolodki-toyota-camry', 'TOY-BR-02', 2800, 3200, 18),
            (cats['dom'], None, 'product', 'Робот-пылесос Xiaomi', 'robot-pylesos-xiaomi', 'XM-RV-01', 18990, 22990, 7),
        ]

        created_count = 0
        for cat, brand, ltype, title, slug, sku, price, old, qty in demo:
            if not Listing.objects.filter(slug=slug).exists():
                Listing.objects.create(
                    user=seller, category=cat, brand=brand, type=ltype,
                    title=title, slug=slug, sku=sku or '', price=price,
                    old_price=old, quantity=qty, status='active',
                    has_warranty=True, published_at=timezone.now(),
                    description=f'Качественный товар: {title}. Быстрая доставка, гарантия.',
                )
                created_count += 1

        if not SearchRequest.objects.exists():
            SearchRequest.objects.create(query='Турбина на BMW X5 E70', description='Нужна оригинал или качественный аналог', status='new', user=buyer)
            SearchRequest.objects.create(query='Дисплей iPhone 14 Pro', description='После падения, нужен OLED', status='new')

        self.stdout.write(self.style.SUCCESS(f'Готово! Добавлено объявлений: {created_count}'))
        self.stdout.write('Admin: admin / admin123 -> /panel/ and /admin/')
        self.stdout.write('Seller: seller / seller123')
        self.stdout.write('Buyer: buyer / buyer123 (wallet 50000 RUB)')
