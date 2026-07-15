from django.core.management.base import BaseCommand
from catalog.models import Brand

BRANDS = (
    ('bosch', 'Bosch'), ('denso', 'Denso'), ('mann', 'MANN-FILTER'), ('ngk', 'NGK'),
    ('continental', 'Continental'), ('apple', 'Apple'), ('samsung', 'Samsung'),
    ('xiaomi', 'Xiaomi'), ('huawei', 'Huawei'), ('sony', 'Sony'), ('lg', 'LG'),
    ('philips', 'Philips'), ('dell', 'Dell'), ('hp', 'HP'), ('lenovo', 'Lenovo'),
    ('asus', 'ASUS'), ('nike', 'Nike'), ('ikea', 'IKEA'), ('dewalt', 'DeWalt'),
    ('makita', 'Makita'), ('varta', 'Varta'), ('exide', 'Exide'), ('castrol', 'Castrol'),
    ('shell', 'Shell'), ('bridgestone', 'Bridgestone'), ('michelin', 'Michelin'),
    ('goodyear', 'Goodyear'), ('zf', 'ZF'), ('valeo', 'Valeo'), ('febi', 'Febi'),
    ('gates', 'Gates'),
)


class Command(BaseCommand):
    help = 'Добавляет бренды в справочник (без пересоздания демо-данных)'

    def handle(self, *args, **options):
        created = 0
        for slug, name in BRANDS:
            _, was_created = Brand.objects.get_or_create(slug=slug, defaults={'name': name})
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Бренды: +{created} новых, всего {Brand.objects.count()}'))
