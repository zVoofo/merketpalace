"""Разбивает style.css на модули с предсказуемым порядком каскада (@layer)."""
from pathlib import Path

CSS_DIR = Path(__file__).resolve().parent.parent / 'static' / 'css'
SRC = CSS_DIR / 'style.css'
text = SRC.read_text(encoding='utf-8')

# Конфликтные глобальные классы → изолированный блок дашборда
text = text.replace('.stats{', '.dash-stats{')
text = text.replace('.stat{', '.dash-stat{')
text = text.replace('.stat__num', '.dash-stat__num')
text = text.replace('.stat__label', '.dash-stat__label')

# Дубль .price-range
dup = '.price-range{display:flex;flex-direction:column;gap:8px}'
if text.count(dup) > 1:
    first = text.index(dup)
    second = text.index(dup, first + 1)
    text = text[:second] + text[second + len(dup):]


def between(start: str | None, end: str | None) -> str:
    s = 0 if start is None else text.index(start)
    e = len(text) if end is None else text.index(end)
    return text[s:e].strip()


chunks: dict[str, list[str]] = {
    'reset': [],
    'tokens': [],
    'layout': [],
    'components': [],
    'blocks': [],
    'responsive': [],
}

head = between(None, '/* --- Шапка --- */')
if ':root{' in head:
    pre, post = head.split(':root{', 1)
    chunks['reset'].append(pre.strip())
    chunks['tokens'].append(':root{' + post.strip())
else:
    chunks['reset'].append(head)

SLICES = [
    ('layout', '/* --- Шапка --- */', '/* --- Карточки каталога --- */'),
    ('components', '/* --- Карточки каталога --- */', '/* --- Галерея --- */'),
    ('blocks', '/* --- Галерея --- */', '@media(max-width:768px)'),
    ('responsive', '@media(max-width:768px)', '/* --- Вход / регистрация --- */'),
    ('blocks', '/* --- Вход / регистрация --- */', None),
]

for layer, start, end in SLICES:
    part = between(start, end)
    if part:
        chunks[layer].append(part)

for name, key in [
    ('reset.css', 'reset'),
    ('tokens.css', 'tokens'),
    ('layout.css', 'layout'),
    ('components.css', 'components'),
    ('blocks.css', 'blocks'),
    ('responsive.css', 'responsive'),
]:
    body = '\n\n'.join(chunks[key]).strip() + '\n'
    (CSS_DIR / name).write_text(body, encoding='utf-8')

main = """/* MarketPlace — точка входа. Редактируйте модули в static/css/, не монолит. */
@layer reset, tokens, base, layout, components, blocks, responsive;

@import url('reset.css') layer(reset);
@import url('tokens.css') layer(tokens);
@import url('layout.css') layer(layout);
@import url('components.css') layer(components);
@import url('blocks.css') layer(blocks);
@import url('responsive.css') layer(responsive);
"""
(CSS_DIR / 'main.css').write_text(main, encoding='utf-8')

SRC.write_text("/* Совместимость: подключайте main.css */\n@import url('main.css');\n", encoding='utf-8')
print('split ok')
