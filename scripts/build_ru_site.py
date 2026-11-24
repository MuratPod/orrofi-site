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

# Старые страницы (Mi gestor, Mi red, Семья, Услуги и счета, Как начать,
# Вопросы) остаются файлами по прежним адресам и в меню не входят.
NAV = [
    ("index.html", "Главная"),
    ("operadores/index.html", "Для операторов"),
    ("privacidad/index.html", "Приватность"),
    ("contacto/index.html", "Контакты"),
]

# Кадров без файла в design/target-v6 нет. Подпись из copy.md остаётся, текста-заглушки нет.
MISSING_FRAMES = frozenset()

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
    for theme in ("dark", "light"):
        base = ROOT / "assets" / "screens" / "v6" / theme
        if not (base / f"{sid}.webp").is_file():
            return False
        if not (base / "android" / f"{sid}.webp").is_file():
            return False
    return True


def dual(text: str, android: str | None) -> str:
    """iPhone wording by default; Android wording only under html.platform-android."""
    if not android:
        return esc(text)
    return (
        f'<span class="copy-iphone">{esc(text)}</span>'
        f'<span class="copy-android">{esc(android)}</span>'
    )


def picture(prefix: str, sid: str, alt: str, eager: bool, platform: str) -> str:
    loading = "eager" if eager else "lazy"
    priority = ' fetchpriority="high"' if eager else ""
    sizes = "(min-width: 960px) 242px, 70vw"
    folder = "android/" if platform == "android" else ""
    dark = f"{prefix}assets/screens/v6/dark/{folder}{sid}"
    light = f"{prefix}assets/screens/v6/light/{folder}{sid}"
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


def slot_phone(prefix: str, sid: str, caption: str, eager: bool) -> str:
    """Пустая рамка iPhone. Картинка — один файл assets/screens-v2/<id>.png.

    Пока файл прозрачный, сквозь него виден нейтральный фон и подпись.
    Непрозрачный снимок того же имени закрывает подпись сам.
    """
    path = ROOT / "assets" / "screens-v2" / f"{sid}.png"
    if not path.is_file():
        raise SystemExit(f"Нет заглушки assets/screens-v2/{sid}.png")
    loading = "eager" if eager else "lazy"
    priority = ' fetchpriority="high"' if eager else ""
    src = f"{prefix}assets/screens-v2/{sid}.png"
    return (
        '<figure class="phone phone-slot">'
        '<div class="device device--iphone device--slot">'
        '<div class="slot-face">'
        f'<p class="slot-caption" aria-hidden="true">{esc(caption)}</p>'
        f'<img src="{src}" alt="{esc(caption)}" width="430" height="932" '
        f'loading="{loading}" decoding="async"{priority}>'
        "</div></div></figure>"
    )


def phone(prefix: str, sid: str, caption: str, eager: bool, android: str | None = None) -> str:
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
        f'<div class="device device--iphone">{picture(prefix, file_id, caption, eager, "ios")}</div>'
        f'<div class="device device--pixel">{picture(prefix, file_id, android or caption, eager, "android")}</div>'
        f"<figcaption>{dual(caption, android)}</figcaption>"
        "</figure>"
    )


def link_href(prefix: str, label: str) -> str:
    if "Mi gestor" in label:
        return nav_href(prefix, "mi-gestor/index.html")
    if "Mi red" in label:
        return nav_href(prefix, "mi-red/index.html")
    return prefix or "./"


def render_nodes(prefix: str, nodes: list, eager_first: bool, lead: bool = False) -> tuple[str, str, bool]:
    text_parts: list[str] = []
    phones: list[str] = []
    used_eager = False
    items: list[str] = []
    questions: list[tuple[str, str]] = []
    lead_open = lead

    def flush_items() -> None:
        nonlocal items
        if not items:
            return
        lis = "".join(f"<li>{inline(item)}</li>" for item in items)
        text_parts.append(f'<ul class="points">{lis}</ul>')
        items = []

    def flush_questions() -> None:
        nonlocal questions
        if not questions:
            return
        lis = []
        for question, answer in questions:
            pending = ' class="pending"' if answer == "[ответ уточняется]" else ""
            lis.append(f"<li><h3>{esc(question)}</h3><p{pending}>{inline(answer)}</p></li>")
        text_parts.append(f'<ol class="faq">{"".join(lis)}</ol>')
        questions = []

    def flush() -> None:
        flush_items()
        flush_questions()

    for node in nodes:
        kind = node[0]
        if kind == "item":
            flush_questions()
            items.append(node[1])
            continue
        if kind == "question":
            flush_items()
            questions.append((node[1], node[2]))
            continue
        flush()
        if kind == "p":
            android = node[2] if len(node) > 2 else None
            if android:
                text_parts.append(
                    f'<p class="copy-iphone">{inline(node[1])}</p>'
                    f'<p class="copy-android">{inline(android)}</p>'
                )
            elif lead_open:
                text_parts.append(f'<p class="lead">{inline(node[1])}</p>')
                lead_open = False
            else:
                text_parts.append(f"<p>{inline(node[1])}</p>")
        elif kind == "steps":
            steps = "".join(f"<li>{inline(step)}</li>" for step in node[1])
            text_parts.append(f'<ol class="steps">{steps}</ol>')
        elif kind == "button":
            text_parts.append(
                '<p class="actions"><button type="button" class="btn" disabled>'
                f"{esc(node[1])}</button></p>"
            )
        elif kind == "mail":
            # TODO: адрес для операторов не выбран, временно privacidad@orrofi.es
            text_parts.append(
                "<!-- TODO: адрес для операторов не выбран, временно mailto:privacidad@orrofi.es -->"
                '<p class="actions"><a class="btn" href="mailto:privacidad@orrofi.es">'
                f"{esc(node[1])}</a></p>"
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
            phones.append(phone(prefix, node[1], node[2], eager, node[3] if len(node) > 3 else None))
        elif kind == "slot":
            eager = eager_first and not used_eager and not phones
            if eager:
                used_eager = True
            phones.append(slot_phone(prefix, node[1], node[2], eager))
        else:
            raise SystemExit(f"Неизвестный узел {kind}")
    flush()
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
        f"<p>{esc(before)}<a href=\"#politika\">{esc(target)}</a>{esc(after)}</p>"
    )


def platform_switch() -> str:
    return (
        '<div class="platform-bar"><fieldset class="platform-switch">'
        "<legend>Модель телефона</legend>"
        '<label class="platform-option">'
        '<input type="radio" name="platform" value="iphone" checked>'
        "<span>iPhone</span></label>"
        '<label class="platform-option">'
        '<input type="radio" name="platform" value="android">'
        "<span>Android</span></label>"
        "</fieldset></div>"
    )


def header(prefix: str, current: str, show_platform: bool = True) -> str:
    home = prefix or "./"
    items = []
    for rel, label in NAV:
        href = nav_href(prefix, rel)
        current_attr = ' aria-current="page"' if rel == current else ""
        items.append(f'<li><a href="{href}"{current_attr}>{esc(label)}</a></li>')
    switch = platform_switch() if show_platform else ""
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
        "</ul></nav></div>"
        f"{switch}</header>"
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


def document(
    rel: str,
    title: str,
    description: str,
    main: str,
    legal: str,
    body_class: str = "",
    show_platform: bool = True,
) -> str:
    prefix = prefix_for(rel)
    body = f'<body class="{esc(body_class)}">\n' if body_class else "<body>\n"
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
        f'<script src="{prefix}assets/js/platform.js"></script>\n'
        "</head>\n"
        f"{body}"
        f"{header(prefix, rel, show_platform)}\n"
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
        "layout": "",
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
        if line.startswith("- **layout:**"):
            page["layout"] = line.split(":**", 1)[1].strip()
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
        android_match = re.fullmatch(r"- android:\s*(.+)", line)
        if android_match:
            if current is None or not current["nodes"]:
                raise SystemExit(f"Вариант Android без фразы: {line}")
            previous = current["nodes"][-1]
            variant = android_match.group(1)
            if previous[0] == "p" and len(previous) == 2:
                current["nodes"][-1] = ("p", previous[1], variant)
                continue
            if previous[0] == "screen" and len(previous) == 3:
                current["nodes"][-1] = ("screen", previous[1], previous[2], variant)
                continue
            raise SystemExit(f"Вариант Android не к абзацу и не к подписи: {line}")
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
        if line.startswith("- Письмо:"):
            label = re.search(r"«(.+?)»", line)
            if not label:
                raise SystemExit(f"Нет подписи письма: {line}")
            current["nodes"].append(("mail", label.group(1)))
            continue
        if line.startswith("- Значок:"):
            label = re.search(r"«(.+?)»", line)
            if not label:
                raise SystemExit(f"Нет подписи значка: {line}")
            current["badge"] = label.group(1)
            continue
        if line.startswith("- Кадр:"):
            slot_match = re.fullmatch(r"- Кадр:\s*`([^`]+)`:\s*(.+)", line)
            if not slot_match:
                raise SystemExit(f"Не разобрал кадр: {line}")
            current["nodes"].append(("slot", slot_match.group(1), slot_match.group(2)))
            continue
        if line.startswith("- Пункт:"):
            current["nodes"].append(("item", line.split(":", 1)[1].strip()))
            continue
        if line.startswith("- Вопрос:"):
            question_match = re.fullmatch(r"- Вопрос:\s*«(.+?)»\s+(.+)", line)
            if not question_match:
                raise SystemExit(f"Не разобрал вопрос блока: {line}")
            current["nodes"].append(("question", question_match.group(1), question_match.group(2)))
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
    body = text.split("## Тексты", 1)[1].split("### Вычитка", 1)[0]
    chunks = re.split(r"(?m)^### Страница ", body)[1:]
    pages = [parse_page(chunk) for chunk in chunks]
    if len(pages) != 10:
        raise SystemExit(f"Ожидалось 10 страниц, разобрано {len(pages)}")
    return legal_match.group(1), slogan_match.group(1), pages


def render_page(page: dict, legal: str, slogan: str) -> list[tuple[str, str]]:
    outputs = []
    files = []
    for path in page["paths"]:
        slug = path.strip("/")
        rel = "index.html" if not slug else f"{slug}/index.html"
        files.append(rel)
    v2 = page.get("layout") == "v2"
    for rel in files:
        prefix = prefix_for(rel)
        parts: list[str] = []
        eager = True
        if v2:
            parts.append(
                "<!-- Кадры v2: замените файл assets/screens-v2/<id>.png. "
                "Список id — assets/screens-v2/README.md -->"
            )
        elif page["num"] != "1":
            intro = "".join(intro_html(item) for item in page["intro"])
            parts.append(
                '<section class="hero"><div class="wrap copy">'
                f"<h1>{esc(page['name'])}</h1>"
                f'<p class="lead">{inline(page["description"])}</p>'
                f"{intro}</div></section>"
            )
        seen_headings: set[str] = set()
        for index, block in enumerate(page["blocks"]):
            level = "h1" if index == 0 and (v2 or page["num"] == "1") else "h2"
            text_html, phones_html, used = render_nodes(
                prefix, block["nodes"], eager, lead=v2 and index == 0
            )
            if used:
                eager = False
            count = sum(1 for node in block["nodes"] if node[0] in ("screen", "slot"))
            layout = "single" if count <= 1 else "many"
            anchor = "politika" if block["heading"] == "Политика конфиденциальности сайта" else "s-" + block["num"].replace(".", "-")
            slogan_html = (
                f'<p class="slogan">{esc(slogan)}</p>'
                if page["num"] == "1" and index == 0 and not v2
                else ""
            )
            hero = " hero" if index == 0 and (v2 or page["num"] == "1") else ""
            flip = " flip" if v2 and index % 2 == 1 and phones_html else ""
            badge = block.get("badge")
            badge_html = f' <span class="soon">{esc(badge)}</span>' if badge else ""
            hidden = (
                block["heading"] == "И это ещё не всё" and block["heading"] in seen_headings
            )
            seen_headings.add(block["heading"])
            hclass = ' class="visually-hidden"' if hidden else ""
            copy_html = (
                f'<div class="copy">{slogan_html}<{level}{hclass}>{esc(block["heading"])}'
                f"{badge_html}</{level}>{text_html}</div>"
            )
            if phones_html:
                inner = (
                    f'<div class="wrap block-grid {layout}{flip}">'
                    f"{copy_html}<div class=\"phones\">{phones_html}</div></div>"
                )
            else:
                inner = f'<div class="wrap">{copy_html}</div>'
            parts.append(
                f'<section class="block {layout}{hero}" id="{anchor}">'
                f"{inner}</section>"
            )
        if page["faq"]:
            parts.append(render_faq(page["faq"]))
        if page["contact"]:
            parts.append(render_contact(page["contact"]))
        html_page = document(
            rel,
            page["title"],
            page["description"],
            "\n".join(parts),
            legal,
            body_class="page-v2" if v2 else "",
            show_platform=not v2,
        )
        outputs.append((rel, html_page))
    return outputs


def write_slot_index(pages: list[dict]) -> None:
    lines = [
        "# Кадры v2",
        "",
        "Пустые рамки главной и страницы «Для операторов».",
        "Корпус — существующая рамка iPhone (`assets/device-frames/iphone.svg`).",
        "Нейтральный фон и подпись «Экран: …» рисует страница.",
        "Чтобы вставить снимок, замените один файл: `assets/screens-v2/<id>.png`.",
        "Размер кадра — 430×932, без корпуса телефона.",
        "Прозрачный PNG оставляет подпись видимой; непрозрачный снимок закрывает её.",
        "",
    ]
    seen: set[str] = set()
    for page in pages:
        if page.get("layout") != "v2":
            continue
        lines.append(f"## {page['name']} `{page['paths'][0]}`")
        lines.append("")
        lines.append("| id | подпись | блок |")
        lines.append("| --- | --- | --- |")
        for block in page["blocks"]:
            for node in block["nodes"]:
                if node[0] != "slot":
                    continue
                sid = node[1]
                if sid in seen:
                    raise SystemExit(f"Повтор id кадра {sid}")
                seen.add(sid)
                lines.append(f"| `{sid}` | {node[2]} | {block['heading']} |")
        lines.append("")
    path = ROOT / "assets" / "screens-v2" / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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
    write_slot_index(pages)
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
    for rel in ("index.html", "operadores/index.html"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "assets/screens/v6" in text:
            raise SystemExit(f"{rel} ссылается на старые кадры")
    print(f"wrote {len(written)} pages")
    for rel in written:
        print(rel)


if __name__ == "__main__":
    main()
