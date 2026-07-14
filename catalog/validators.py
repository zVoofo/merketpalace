import re

CYR_VOWELS = set('аеёиоуыэюя')
CYR_CONSONANTS = set('бвгджзйклмнпрстфхцчшщ')
LAT_VOWELS = set('aeiouy')
LAT_CONSONANTS = set('bcdfghjklmnpqrstvwxz')

# Слова/части слов, которые всегда пропускаем (товары, бренды)
ALLOWED_KEYWORDS = {
    'iphone', 'samsung', 'bosch', 'bmw', 'lada', 'toyota', 'audi', 'mercedes',
    'kolodki', 'filtr', 'maslo', 'shiny', 'disk', 'akb', 'akkumulyator',
    'телефон', 'колодки', 'фильтр', 'масло', 'шины', 'диск', 'аккумулятор',
    'запчаст', 'деталь', 'насос', 'ремень', 'амортизатор', 'свеч', 'ламп',
    'ноутбук', 'монитор', 'пылесос', 'перфоратор', 'дрель', 'iphone', 'айфон',
}


def _max_consonant_run(word: str, vowels: set, consonants: set) -> int:
    run = max_run = 0
    for ch in word.lower():
        if ch in vowels:
            run = 0
        elif ch in consonants:
            run += 1
            max_run = max(max_run, run)
    return max_run


def _vowel_ratio(word: str, vowels: set) -> float:
    letters = [c for c in word.lower() if c.isalpha()]
    if not letters:
        return 0
    return sum(1 for c in letters if c in vowels) / len(letters)


def _has_repeated_syllable_pattern(word: str) -> bool:
    w = word.lower()
    if len(w) < 4:
        return False
    for size in range(2, len(w) // 2 + 1):
        if len(w) % size == 0:
            part = w[:size]
            if part * (len(w) // size) == w:
                return True
    return False


def _has_repeating_fragment(word: str, min_len: int = 3) -> bool:
    """Обнаруживает повторяющиеся фрагменты: ццуйцуйц, abcabc."""
    w = word.lower()
    if len(w) < min_len * 2:
        return False
    for size in range(min_len, len(w) // 2 + 1):
        for start in range(len(w) - size + 1):
            frag = w[start:start + size]
            if w.count(frag) >= 2 and len(frag) >= min_len:
                return True
    return False


def _is_keyboard_mash(word: str) -> bool:
    """Случайный набор с клавиaturы: много согласных подряд, мало гласных."""
    w = word.lower()
    if len(w) < 4:
        return False

    cyr_letters = [c for c in w if c in CYR_VOWELS or c in CYR_CONSONANTS]
    lat_letters = [c for c in w if c in LAT_VOWELS or c in LAT_CONSONANTS]

    if cyr_letters:
        if _max_consonant_run(w, CYR_VOWELS, CYR_CONSONANTS) >= 4:
            return True
        if len(cyr_letters) >= 5 and _vowel_ratio(w, CYR_VOWELS) < 0.18:
            return True
    if lat_letters:
        if _max_consonant_run(w, LAT_VOWELS, LAT_CONSONANTS) >= 5:
            return True
        if len(lat_letters) >= 6 and _vowel_ratio(w, LAT_VOWELS) < 0.15:
            return True

    if _has_repeated_syllable_pattern(w):
        return True

    if _has_repeating_fragment(w):
        return True

    # Двойные согласные в начале — только для явно длинного мусора
    if len(w) >= 6 and w[0] == w[1] and w[0] not in (CYR_VOWELS | LAT_VOWELS):
        if _vowel_ratio(w, CYR_VOWELS | LAT_VOWELS) < 0.25:
            return True

    letters_only = re.sub(r'[^a-zа-яё]', '', w)
    if len(letters_only) >= 9 and len(set(letters_only)) / len(letters_only) > 0.88:
        if _vowel_ratio(w, CYR_VOWELS | LAT_VOWELS) < 0.2:
            return True

    return False


def _contains_allowed_keyword(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in ALLOWED_KEYWORDS)


def _is_product_token(word: str) -> bool:
    """Артикулы, модели, бренды: X5, 256GB, BMW, GBH-226."""
    if not word:
        return False
    if re.fullmatch(r'[A-Za-z]{2,6}', word):
        return True
    if re.fullmatch(r'[A-Za-z]\d{1,3}', word, re.I):
        return True
    if re.fullmatch(r'\d+[A-Za-z]{1,4}', word, re.I):
        return True
    if re.fullmatch(r'[A-Za-z0-9]+-[A-Za-z0-9]+', word):
        return True
    letters = sum(c.isalpha() for c in word)
    digits = sum(c.isdigit() for c in word)
    return letters >= 2 and digits >= 1 and len(word) >= 4


def _word_looks_valid(word: str) -> bool:
    if len(word) < 2:
        return False
    low = word.lower()
    if low in ALLOWED_KEYWORDS or any(kw in low for kw in ALLOWED_KEYWORDS if len(kw) >= 4):
        return True
    if word.isdigit():
        return len(word) >= 2
    if _is_product_token(word):
        return True
    if _is_keyboard_mash(word):
        return False
    vowels = CYR_VOWELS | LAT_VOWELS
    if _vowel_ratio(word, vowels) < 0.1 and len(word) > 3:
        return False
    return True


def _is_obvious_mash_text(text: str) -> bool:
    """Только явный бред: одно длинное слово-мусор или большинство слов — мусор."""
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ]+', text or '')
    if not words:
        return False
    mash = [w for w in words if len(w) >= 5 and _is_keyboard_mash(w)]
    if len(words) == 1:
        return bool(mash) or (len(words[0]) >= 6 and _is_keyboard_mash(words[0]))
    return len(mash) >= max(2, int(len(words) * 0.6))


def is_valid_listing_text(text: str, *, min_length: int = 3) -> tuple[bool, str]:
    """Мягкая проверка названия/описания объявления (не путать с поиском)."""
    t = (text or '').strip()
    if len(t) < min_length:
        return False, 'Слишком короткий текст'
    if len(t) > 5000:
        return False, 'Слишком длинный текст'
    if re.fullmatch(r'[\d\s\.\-\+\(\)]+', t):
        return False, 'Нельзя использовать только цифры'
    if len(set(t.lower().replace(' ', ''))) == 1:
        return False, 'Текст не может состоять из одинаковых символов'

    if _contains_allowed_keyword(t):
        return True, ''

    if _is_obvious_mash_text(t):
        return False, 'Текст похож на случайный набор букв — укажите реальное название товара'

    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9\-]+', t)
    if not words:
        return False, 'Введите осмысленное название товара'

    significant = [w for w in words if len(w) > 1 or w.isdigit()]
    if not significant:
        return False, 'Введите осмысленное название товара'

    valid_words = [w for w in significant if _word_looks_valid(w)]
    if valid_words:
        return True, ''

    return False, 'Не удалось распознать название товара — проверьте написание'


def is_valid_search_query(query: str) -> tuple[bool, str]:
    q = (query or '').strip()
    if len(q) < 3:
        return False, 'Запрос слишком короткий (минимум 3 символа)'
    if len(q) > 200:
        return False, 'Запрос слишком длинный'
    if re.fullmatch(r'[\d\s\.\-\+\(\)]+', q):
        return False, 'Нельзя искать только цифры'
    if len(set(q.lower().replace(' ', ''))) == 1:
        return False, 'Запрос не может состоять из одинаковых символов'

    if _contains_allowed_keyword(q):
        return True, ''

    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9\-]+', q)
    if not words:
        return False, 'Введите осмысленное название товара'

    valid_words = [w for w in words if _word_looks_valid(w)]
    if not valid_words:
        return False, 'Запрос похож на случайный набор букв. Укажите название товара, например: «тормозные колодки BMW»'

    if _is_obvious_mash_text(q):
        return False, 'Запрос похож на случайный набор букв'

    # Отклоняем только если большинство слов — мусор (не каждое слово отдельно)
    bad = [w for w in words if len(w) > 2 and not _word_looks_valid(w) and not w.isdigit()]
    if bad and len(bad) >= len(words) and not valid_words:
        return False, f'«{bad[0]}» не похоже на название товара. Проверьте запрос'

    return True, ''
