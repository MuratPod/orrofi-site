#!/usr/bin/env python3
"""Собрать статический сайт-витрину из showcase/copy.md.

Тексты страниц переносятся дословно. Генератор не переписывает их
и не добавляет неразрывные пробелы.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = ROOT / "showcase" / "copy.md"

NAV = [
    ("index.html", "Главная"),
    ("mi-gestor/index.html", "Mi gestor"),
    ("mi-red/index.html", "Mi red"),
    ("familia/index.html", "Семья"),
    ("uslugi/index.html", "Услуги и счета"),
    ("privacidad/index.html", "Приватность"),
    ("instrukcii/index.html", "Как начать"),
    ("faq/index.html", "Вопросы"),
]

# Кадра нет в design/target-v6. Подпись из copy.md остаётся, текста-заглушки нет.
MISSING_FRAMES = frozenset({"fam-15b"})

# Вторая реплика чата — отдельный кадр, в текстах id тот же (`manager`).
MANAGER_TICKET = "Заявка на визит мастера создана из чата."

LEGACY = [
    (
        "vozmozhnosti/index.html",
        "Возможности",
        "Возможности приложения собраны на главной.",
        "index.html",
        "Главная",
    ),
    (
        "facturas/index.html",
        "Счета",
        "Счета собраны на странице «Услуги и счета».",
        "uslugi/index.html#s-5-7",
        "Услуги и счета",
    ),
    (
        "ajustes/index.html",
        "Настройки",
        "Тема, язык и извещения — на странице «Как начать».",
        "instrukcii/index.html#s-7-6",
        "Как начать",
    ),
]

CSP = (
    "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
    "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'"
)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    rendered = html.escape(text, quote=False)
    rendered = rendered.replace(
        "privacidad@orrofi.es",
        '<a href="mailto:privacidad@orrofi.es">privacidad@orrofi.es</a>',
    )
    return rendered


def prefix_for(rel: str) -> str:
    return "../" * rel.count("/")


def nav_href(prefix: str, target: str) -> str:
    path, _, frag = target.partition("#")
    if path == "index.html":
        href = prefix or "./"
    else:
        href = prefix + path.replace("index.html", "")
    if frag:
        href += "#" + frag
    return href


def asset_id(sid: str, caption: str) -> str:
    if sid == "manager" and caption == MANAGER_TICKET:
        return "manager-solicitud"
    return sid


def frame_exists(sid: str) -> bool:
    dark = ROOT / "assets" / "screens" / "v6" / "dark" / f"{sid}.webp"
    light = ROOT / "assets" / "screens" / "v6" / "light" / f"{sid}.webp"
    return dark.is_file() and light.is_file()


def picture(prefix: str, sid: str, alt: str, eager: bool) -> str:
    loading = "eager" if eager else "lazy"
    priority = ' fetchpriority="high"' if eager else ""
    sizes = "(min-width: 960px) 270px, 78vw"
    dark = f"{prefix}assets/screens/v6/dark/{sid}"
    light = f"{prefix}assets/screens/v6/light/{sid}"
    return (
        "<picture>"
        f'<source media="(prefers-color-scheme: light)" type="image/webp" '
        f'srcset="{light}-430.webp 430w, {light}.webp 860w" sizes="{sizes}">'
        f'<source media="(prefers-color-scheme: light)" type="image/png" '
        f'srcset="{light}.png">'
        f'<source type="image/webp" '
        f'srcset="{dark}-430.webp 430w, {dark}.webp 860w" sizes="{sizes}">'
        f'<img src="{dark}.png" alt="{esc(alt)}" width="430" height="932" '
        f'loading="{loading}" decoding="async"{priority}>'
        "</picture>"
    )


def phone(prefix: str, sid: str, caption: str, eager: bool) -> str:
    file_id = asset_id(sid, caption)
    if file_id in MISSING_FRAMES or not frame_exists(file_id):
        if file_id not in MISSING_FRAMES:
            raise SystemExit(f"Нет кадра {file_id} для подписи: {caption}")
        return (
            '<figure class="phone phone-missing">'
            f"<!-- нет кадра {file_id} в design/target-v6 -->"
            '<div class="screen-gap" aria-hidden="true"></div>'
            f"<figcaption>{esc(caption)}</figcaption>"
            "</figure>"
        )
    return (
        '<figure class="phone">'
        f"{picture(prefix, file_id, caption, eager)}"
        f"<figcaption>{esc(caption)}</figcaption>"
        "</figure>"
    )


def link_href(prefix: str, label: str) -> str:
    if "Mi gestor" in label:
        return nav_href(prefix, "mi-gestor/index.html")
    if "Mi red" in label:
        return nav_href(prefix, "mi-red/index.html")
    return prefix or "./"


def render_nodes(prefix: str, nodes: list, eager_first: bool) -> tuple[str, str, bool]:
    text_parts: list[str] = []
    phones: list[str] = []
    used_eager = False
    for node in nodes:
        kind = node[0]
        if kind == "p":
            text_parts.append(f"<p>{inline(node[1])}</p>")
        elif kind == "steps":
            items = "".join(f"<li>{inline(step)}</li>" for step in node[1])
            text_parts.append(f'<ol class="steps">{items}</ol>')
        elif kind == "button":
            text_parts.append(
                '<p class="actions"><button type="button" class="btn" disabled>'
                f"{esc(node[1])}</button></p>"
            )
        elif kind == "link":
            label = node[1]
            text_parts.append(
                f'<p class="actions"><a class="text-link" href="{link_href(prefix, label)}">'
                f"{esc(label)}</a></p>"
            )
        elif kind == "screen":
            eager = eager_first and not used_eager and not phones
            if eager:
                used_eager = True
            phones.append(phone(prefix, node[1], node[2], eager))
        else:
            raise SystemExit(f"Неизвестный узел {kind}")
    return "".join(text_parts), "".join(phones), used_eager


def render_faq(faq: list[tuple[str, str]]) -> str:
    items = []
    for question, answer in faq:
        items.append(f"<li><h3>{esc(question)}</h3><p>{inline(answer)}</p></li>")
    return (
        '<section class="block" id="voprosy"><div class="wrap">'
        "<h2>Частые вопросы</h2>"
        f'<ol class="faq">{"".join(items)}</ol>'
        "</div></section>"
    )


def render_contact(contact: dict) -> str:
    paras = "".join(f"<p>{inline(p)}</p>" for p in contact["paras"])
    return (
        '<section class="block" id="ostalis-voprosy"><div class="wrap copy">'
        f"<h2>{esc(contact['heading'])}</h2>{paras}"
        "</div></section>"
    )


def intro_html(text: str) -> str:
    """Метка «Вступление:» и пометка «(ссылка)» — указания в исходнике, не текст страницы."""
    body = text
    target = "политике конфиденциальности"
    if target not in body:
        return f"<p>{inline(body)}</p>"
    body = body.replace(" (ссылка)", "")
    before, after = body.split(target, 1)
    return (
        f"<p>{esc(before)}<a href=\"#sitio-privacidad\">{esc(target)}</a>{esc(after)}</p>"
    )


def header(prefix: str, current: str) -> str:
    home = prefix or "./"
    items = []
    for rel, label in NAV:
        href = nav_href(prefix, rel)
        current_attr = ' aria-current="page"' if rel == current else ""
        items.append(f'<li><a href="{href}"{current_attr}>{esc(label)}</a></li>')
    return (
        '<a class="skip" href="#main">К содержанию</a>'
        '<header class="site-header"><div class="wrap topbar">'
        f'<a class="logo" href="{home}">'
        f'<img class="logo-on-dark" src="{prefix}logo/lockup-h-dark.svg" alt="OrroFi" width="118" height="44">'
        f'<img class="logo-on-light" src="{prefix}logo/lockup-h-light.svg" alt="OrroFi" width="118" height="44">'
        "</a>"
        '<button type="button" class="nav-toggle" aria-expanded="false" aria-controls="nav">Меню</button>'
        '<nav class="primary" id="nav" aria-label="Основное меню"><ul>'
        f'{"".join(items)}'
        "</ul></nav></div></header>"
    )


def footer(prefix: str, legal: str) -> str:
    return (
        '<footer class="site-footer"><div class="wrap">'
        f'<p id="sitio-privacidad">{esc(legal)}</p>'
        '<p class="footer-links">'
        f'<a href="{nav_href(prefix, "privacidad/index.html")}">Приватность</a>'
        f'<a href="{nav_href(prefix, "faq/index.html")}">Вопросы</a>'
        f'<a href="{nav_href(prefix, "contacto/index.html")}">Контакты</a>'
        '<a href="mailto:privacidad@orrofi.es">privacidad@orrofi.es</a>'
        "</p></div></footer>"
        f'<script src="{prefix}assets/js/site.js" defer></script>'
    )


def document(rel: str, title: str, description: str, main: str, legal: str) -> str:
    prefix = prefix_for(rel)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="description" content="{esc(description)}">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
        '<meta name="referrer" content="strict-origin-when-cross-origin">\n'
        f"<title>{esc(title)}</title>\n"
        f'<link rel="icon" type="image/png" href="{prefix}icons/ios/AppIcon-60.png">\n'
        f'<link rel="stylesheet" href="{prefix}assets/css/site.css">\n'
        "</head>\n"
        "<body>\n"
        f"{header(prefix, rel)}\n"
        f'<main id="main">\n{main}\n</main>\n'
        f"{footer(prefix, legal)}\n"
        "</body>\n"
        "</html>\n"
    )


def parse_page(chunk: str) -> dict:
    lines = chunk.splitlines()
    header_line = lines[0]
    match = re.match(r"(\d+)\.\s+(.+?)\s+(`.*`)$", header_line.strip())
    if not match:
        raise SystemExit(f"Не разобрал заголовок страницы: {header_line}")
    paths = re.findall(r"`([^`]+)`", header_line)
    page = {
        "num": match.group(1),
        "name": match.group(2).strip(),
        "paths": paths,
        "title": "",
        "description": "",
        "intro": [],
        "blocks": [],
        "faq": [],
        "contact": None,
    }
    mode = "seek"
    current = None
    for raw in lines[1:]:
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith("- **title:**"):
            page["title"] = line.split(":**", 1)[1].strip()
            continue
        if line.startswith("- **description:**"):
            page["description"] = line.split(":**", 1)[1].strip()
            continue
        block_match = re.fullmatch(r"\*\*(\d+\.\d+)\s+(.+)\*\*", line)
        if block_match:
            current = {
                "num": block_match.group(1),
                "heading": block_match.group(2),
                "nodes": [],
            }
            page["blocks"].append(current)
            mode = "block"
            continue
        if line == "**Частые вопросы**":
            mode = "faq"
            current = None
            continue
        if line == "**Остались вопросы?**":
            mode = "contact"
            page["contact"] = {"heading": "Остались вопросы?", "paras": []}
            current = None
            continue
        if line.startswith("Вступление:"):
            page["intro"].append(line.split(":", 1)[1].strip())
            continue
        if mode == "faq":
            faq_match = re.fullmatch(r"\d+\.\s+\*\*(.+?)\*\*\s+(.+)", line)
            if not faq_match:
                raise SystemExit(f"Не разобрал вопрос: {line}")
            page["faq"].append((faq_match.group(1), faq_match.group(2)))
            continue
        if mode == "contact":
            page["contact"]["paras"].append(line)
            continue
        if mode != "block" or current is None:
            raise SystemExit(f"Строка вне блока: {line}")
        screen_match = re.fullmatch(r"- `([^`]+)`:\s*(.+)", line)
        if screen_match:
            current["nodes"].append(("screen", screen_match.group(1), screen_match.group(2)))
            continue
        if line.startswith("- Кнопка:"):
            label = re.search(r"«(.+?)»", line)
            if not label:
                raise SystemExit(f"Нет подписи кнопки: {line}")
            current["nodes"].append(("button", label.group(1)))
            continue
        if line.startswith("- Ссылка:"):
            label = re.search(r"«(.+?)»", line)
            if not label:
                raise SystemExit(f"Нет подписи ссылки: {line}")
            current["nodes"].append(("link", label.group(1)))
            continue
        step_match = re.fullmatch(r"\d+\.\s+(.+)", line)
        if step_match:
            if current["nodes"] and current["nodes"][-1][0] == "steps":
                current["nodes"][-1][1].append(step_match.group(1))
            else:
                current["nodes"].append(["steps", [step_match.group(1)]])
            continue
        current["nodes"].append(("p", line))
    if not page["title"] or not page["description"]:
        raise SystemExit(f"Нет title или description у страницы {page['num']}")
    return page


def load_pages() -> tuple[str, str, list[dict]]:
    text = COPY.read_text(encoding="utf-8")
    legal_match = re.search(r"В подвале каждой страницы: «(.+?)»", text)
    slogan_match = re.search(r"1\. «(.+?)»\. \*\*Выбран", text)
    if not legal_match or not slogan_match:
        raise SystemExit("В copy.md не найдены слоган или текст подвала")
    body = text.split("## Тексты", 1)[1].split("## Вычитка", 1)[0]
    chunks = re.split(r"(?m)^### Страница ", body)[1:]
    pages = [parse_page(chunk) for chunk in chunks]
    if len(pages) != 8:
        raise SystemExit(f"Ожидалось 8 страниц, разобрано {len(pages)}")
    return legal_match.group(1), slogan_match.group(1), pages


def render_page(page: dict, legal: str, slogan: str) -> list[tuple[str, str]]:
    main_parts: list[str] = []
    # Префикс подставим при сборке документа: сначала собираем относительно корня,
    # затем пересоберём для каждой глубины отдельно.
    outputs = []
    files = []
    for path in page["paths"]:
        slug = path.strip("/")
        rel = "index.html" if not slug else f"{slug}/index.html"
        files.append(rel)
    # Все целевые файлы этой страницы лежат на одной глубине, кроме главной.
    for rel in files:
        prefix = prefix_for(rel)
        parts: list[str] = []
        eager = True
        if page["num"] != "1":
            intro = "".join(intro_html(item) for item in page["intro"])
            parts.append(
                '<section class="hero"><div class="wrap copy">'
                f"<h1>{esc(page['name'])}</h1>"
                f'<p class="lead">{inline(page["description"])}</p>'
                f"{intro}</div></section>"
            )
        for index, block in enumerate(page["blocks"]):
            level = "h1" if page["num"] == "1" and index == 0 else "h2"
            text_html, phones_html, used = render_nodes(prefix, block["nodes"], eager)
            if used:
                eager = False
            count = sum(1 for node in block["nodes"] if node[0] == "screen")
            layout = "single" if count <= 1 else "many"
            anchor = "s-" + block["num"].replace(".", "-")
            slogan_html = f'<p class="slogan">{esc(slogan)}</p>' if page["num"] == "1" and index == 0 else ""
            hero = " hero" if page["num"] == "1" and index == 0 else ""
            parts.append(
                f'<section class="block {layout}{hero}" id="{anchor}">'
                f'<div class="wrap block-grid {layout}">'
                f'<div class="copy">{slogan_html}<{level}>{esc(block["heading"])}</{level}>{text_html}</div>'
                f'<div class="phones">{phones_html}</div>'
                "</div></section>"
            )
        if page["faq"]:
            parts.append(render_faq(page["faq"]))
        if page["contact"]:
            parts.append(render_contact(page["contact"]))
        html_page = document(rel, page["title"], page["description"], "\n".join(parts), legal)
        outputs.append((rel, html_page))
    return outputs


def render_legacy(legal: str) -> list[tuple[str, str]]:
    pages = []
    for rel, title, sentence, target, label in LEGACY:
        prefix = prefix_for(rel)
        href = nav_href(prefix, target)
        main = (
            '<section class="hero"><div class="wrap copy">'
            f"<h1>{esc(title)}</h1>"
            f"<p>{esc(sentence)}</p>"
            f'<p class="actions"><a class="text-link" href="{href}">{esc(label)}</a></p>'
            "</div></section>"
        )
        description = sentence
        pages.append((rel, document(rel, f"{title} — OrroFi", description, main, legal)))
    return pages


def main() -> None:
    legal, slogan, pages = load_pages()
    written: list[str] = []
    for page in pages:
        for rel, content in render_page(page, legal, slogan):
            path = ROOT / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(rel)
    for rel, content in render_legacy(legal):
        path = ROOT / rel
        path.write_text(content, encoding="utf-8")
        written.append(rel)
    print(f"wrote {len(written)} pages")
    for rel in written:
        print(rel)


if __name__ == "__main__":
    main()
