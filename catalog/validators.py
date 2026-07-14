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

    # Двойные символы в начале: цц..., аа...
    if len(w) >= 4 and w[0] == w[1] and w[0] not in (CYR_VOWELS | LAT_VOWELS):
        if _vowel_ratio(w, CYR_VOWELS | LAT_VOWELS) < 0.35:
            return True

    letters_only = re.sub(r'[^a-zа-яё]', '', w)
    if len(letters_only) >= 7 and len(set(letters_only)) / len(letters_only) > 0.85:
        if _vowel_ratio(w, CYR_VOWELS | LAT_VOWELS) < 0.25:
            return True

    return False


def _contains_allowed_keyword(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in ALLOWED_KEYWORDS)


def _word_looks_valid(word: str) -> bool:
    if len(word) < 2:
        return False
    low = word.lower()
    if low in ALLOWED_KEYWORDS or any(kw in low for kw in ALLOWED_KEYWORDS if len(kw) >= 4):
        return True
    if word.isdigit():
        return len(word) >= 3
    if _is_keyboard_mash(word):
        return False
    # Нормальное слово: есть гласные и не более 3 согласных подряд
    vowels = CYR_VOWELS | LAT_VOWELS
    if _vowel_ratio(word, vowels) < 0.1 and len(word) > 3:
        return False
    return True


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

    # Если одно "слово" и оно длинное без пробелов — доп. проверка
    if len(words) == 1 and len(words[0]) >= 5 and not valid_words:
        return False, 'Запрос похож на случайный набор букв'

    # Все слова должны быть валидными (кроме коротких предлогов/артикулов)
    for w in words:
        if len(w) <= 2:
            continue
        if not _word_looks_valid(w) and not w.isdigit():
            return False, f'«{w}» не похоже на название товара. Проверьте запрос'

    return True, ''
