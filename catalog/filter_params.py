"""Проверка и нормализация параметров фильтров каталога."""

from decimal import Decimal, InvalidOperation

MAX_FILTER_PRICE = 50_000_000
MIN_FILTER_PRICE = 0
ALLOWED_SORT = frozenset({'new', 'price_asc', 'price_desc', 'rating', 'popular'})
ALLOWED_TYPES = frozenset({'product', 'service'})
ALLOWED_CONDITIONS = frozenset({'new', 'used', 'refurbished'})
ALLOWED_RATINGS = frozenset({'3', '4', '4.5'})


def _parse_positive_int(raw: str, *, label: str, errors: list[str], max_value: int) -> int | None:
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        value = int(Decimal(raw))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(f'{label} должна быть целым числом')
        return None
    if value < 0:
        errors.append(f'{label} не может быть отрицательной')
        return None
    if value > max_value:
        errors.append(f'{label} слишком большая (максимум {max_value:,} ₽)'.replace(',', ' '))
        return None
    return value


def _parse_id(raw: str, *, label: str, allowed_ids: set[str], errors: list[str]) -> str | None:
    raw = (raw or '').strip()
    if not raw:
        return None
    if not raw.isdigit():
        errors.append(f'Некорректный фильтр: {label}')
        return None
    if raw not in allowed_ids:
        errors.append(f'{label} не найден в каталоге')
        return None
    return raw


def _parse_choice(raw: str, *, label: str, allowed: frozenset[str], errors: list[str]) -> str | None:
    raw = (raw or '').strip()
    if not raw:
        return None
    if raw not in allowed:
        errors.append(f'Некорректное значение: {label}')
        return None
    return raw


def parse_catalog_filters(
    get_params,
    *,
    category_ids: set[str],
    brand_ids: set[str],
    make_ids: set[str],
    price_cap: int,
) -> tuple[dict, list[str]]:
    """Возвращает очищенные фильтры и список ошибок."""
    errors: list[str] = []
    price_cap = max(MIN_FILTER_PRICE, min(int(price_cap or MAX_FILTER_PRICE), MAX_FILTER_PRICE))

    price_min = _parse_positive_int(
        get_params.get('price_min', ''),
        label='Минимальная цена',
        errors=errors,
        max_value=MAX_FILTER_PRICE,
    )
    price_max = _parse_positive_int(
        get_params.get('price_max', ''),
        label='Максимальная цена',
        errors=errors,
        max_value=MAX_FILTER_PRICE,
    )

    if price_min is not None and price_max is not None and price_min > price_max:
        errors.append('Минимальная цена не может быть больше максимальной')
        price_min, price_max = price_max, price_min

    if price_min is not None and price_min > price_cap and price_max is None:
        errors.append(f'Минимальная цена завышена для текущего каталога (до {price_cap:,} ₽)'.replace(',', ' '))

    in_stock = get_params.get('in_stock') == '1'
    preorder = get_params.get('preorder') == '1'
    if in_stock and preorder:
        errors.append('Нельзя одновременно выбрать «В наличии» и «Под заказ»')
        preorder = False

    sort = _parse_choice(get_params.get('sort', 'new'), label='сортировка', allowed=ALLOWED_SORT, errors=errors) or 'new'

    page_raw = (get_params.get('page') or '').strip()
    page = 1
    if page_raw:
        try:
            page = int(page_raw)
            if page < 1:
                errors.append('Номер страницы должен быть больше 0')
                page = 1
            elif page > 5000:
                errors.append('Слишком большой номер страницы')
                page = 1
        except (TypeError, ValueError):
            errors.append('Номер страницы должен быть числом')
            page = 1

    cleaned = {
        'q': (get_params.get('q') or '').strip(),
        'category': _parse_id(get_params.get('category', ''), label='категория', allowed_ids=category_ids, errors=errors),
        'brand': _parse_id(get_params.get('brand', ''), label='бренд', allowed_ids=brand_ids, errors=errors),
        'type': _parse_choice(get_params.get('type', ''), label='тип товара', allowed=ALLOWED_TYPES, errors=errors),
        'condition': _parse_choice(get_params.get('condition', ''), label='состояние', allowed=ALLOWED_CONDITIONS, errors=errors),
        'make': _parse_id(get_params.get('make', ''), label='марка авто', allowed_ids=make_ids, errors=errors),
        'rating': _parse_choice(get_params.get('rating', ''), label='рейтинг', allowed=ALLOWED_RATINGS, errors=errors),
        'sort': sort,
        'price_min': price_min,
        'price_max': price_max,
        'in_stock': in_stock,
        'preorder': preorder,
        'warranty': get_params.get('warranty') == '1',
        'sale': get_params.get('sale') == '1',
        'photo': get_params.get('photo') == '1',
        'page': page,
    }
    return cleaned, errors
