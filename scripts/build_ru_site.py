#!/usr/bin/env python3
"""Generate static Russian OrroFi visitka from _inputs/plan/screens.md."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENS_MD = ROOT / "_inputs/plan/screens.md"
IOS_SHOTS_DIR = ROOT / "assets" / "screens" / "ios"
FRAMES_JSON = ROOT / "tools/render-screens/frames.json"

# Брендбук в репозиторий не кладём — только замены для вёрстки.
BRANDBOOK_FALLBACK: dict[str, str] = {
    "brandbook-usage-splash-430x932.png": "assets/screens/ios/ios-home-es-dark.png",
    "brandbook-usage-hero-1600x900.png": "assets/screens/ios/ios-home-es-dark.png",
    "brandbook-usage-app-mi-red-430x932.png": "assets/screens/mi-red-1-resumen.png",
}
_SCREEN_ASSETS: dict[str, list[str]] | None = None

# Сведения LSSI / контакты (единый источник).
LEGAL_OWNER = {
    "legal_name": "PADELADA WORLD, S.L. (Sociedad Unipersonal)",
    "short_name": "PADELADA WORLD SL",
    "nif": "B05783238",
    "address": "Calle Josep Pla, 8, Esc. 1, Pta. 1, 17252 Calonge i Sant Antoni (Girona), España",
    "registry": "Registro Mercantil de Girona, hoja GI-80156, inscripción 1.ª",
    "email_privacy": "privacidad@orrofi.es",
}

SITE_PRIVACY_ANCHOR = "sitio-privacidad"

SITE_PRIVACY_TEXT = (
    "Сайт не собирает данные через формы и не использует cookies. "
    "Хостинг GitHub Pages (GitHub, Inc., США) технически получает IP-адрес и сведения "
    "о браузере при открытии страниц. Если вы пишете нам на privacidad@orrofi.es, "
    "PADELADA WORLD SL использует ваше письмо только для ответа (ст. 6(1)(f) RGPD) "
    "и хранит его, пока нужно для ответа. Вы вправе получить доступ к данным, "
    "исправить, удалить или ограничить их, возразить против обработки и подать жалобу "
    "в AEPD (aepd.es). Полная политика конфиденциальности приложения появится до его запуска."
)

FOOTER_COOKIES_LINE = "Сайт не использует cookies и счётчики посещений."


def sanitize_legal_copy(text: str) -> str:
    """Смягчение формулировок по ревью Legal (не меняем материалы в _inputs)."""
    rules = [
        (
            "Нет в открытом виде. Пароль шифруется на iPhone; на сервер уходит только шифр.",
            "Пароль Wi‑Fi защищён при передаче и хранении.",
        ),
        (
            "Пароль шифруется на iPhone; на сервер уходит только шифр, не открытый пароль.",
            "Пароль Wi‑Fi защищён при передаче и хранении.",
        ),
        (
            "Он шифруется на iPhone и на сервер уходит только шифр, не открытый пароль.",
            "Пароль Wi‑Fi защищён при передаче и хранении.",
        ),
        (
            "Пароль роутера шифруется на телефоне",
            "Пароль Wi‑Fi защищён при передаче и хранении",
        ),
        (
            "изолирует гостей от ваших устройств",
            "гостевая сеть отделена от домашней",
        ),
        (
            "Гостевая сеть изолирует гостей от ваших устройств.",
            "Гостевая сеть отделена от домашней.",
        ),
        (
            "но изолирует гостей от ваших устройств",
            "гостевая сеть отделена от домашней",
        ),
        (
            "В рабочие часы по Мадриду (понедельник–пятница, 9:00–20:00) чат передаётся живому сотруднику. История переписки сохраняется.",
            "При необходимости к разговору подключится сотрудник. "
            "История переписки хранится в течение срока, указанного в политике конфиденциальности.",
        ),
        (
            "Нажмите «Hablar con una persona» в рабочие часы по Мадриду.",
            "Нажмите «Hablar con una persona», если нужен сотрудник.",
        ),
        (
            "Вне часов оставьте заявку — приложение честно скажет, когда ответят.",
            "Если сотрудник недоступен, оставьте заявку в чате.",
        ),
        (
            "Введите пароль роутера — он останется зашифрованным на телефоне.",
            "Введите пароль роутера. Пароль Wi‑Fi защищён при передаче и хранении.",
        ),
        (
            "Передача живому сотруднику в часы Пн–Пт 9:00–20:00 (Europe/Madrid)",
            "Передача разговора сотруднику",
        ),
        (
            "заявку примут в службу безопасности",
            "заявку примут в поддержку",
        ),
    ]
    for old, new in rules:
        text = text.replace(old, new)
    return text

NAV = [
    ("index.html", "Главная"),
    ("vozmozhnosti/index.html", "Возможности"),
    ("uslugi/index.html", "Услуги"),
    ("mi-gestor/index.html", "Mi gestor"),
    ("mi-red/index.html", "Mi red"),
    ("familia/index.html", "Семья"),
    ("facturas/index.html", "Счета"),
    ("ajustes/index.html", "Настройки"),
    ("instrukcii/index.html", "Инструкции"),
    ("privacidad/index.html", "Безопасность"),
    ("faq/index.html", "FAQ"),
    ("contacto/index.html", "Контакты"),
]

EXTRA_SCREENS: list[dict] = []

DEL_IDS = [
    "del-entry", "del-owner", "del-16a0", "del-16a", "del-16b", "del-16b2", "del-16c",
    "del-sh-bio", "del-16d", "del-16d2", "del-16e", "del-16e2", "del-16f", "del-16g", "del-16h",
]
RST_IDS = [
    "rst-entry", "rst-owner", "rst-sms", "rst-17m",
    *[f"rst-17{c}" for c in "abcdefghijkl"], "rst-sh-bio", "rst-sh-bio-c",
]
RP_IDS = ["rp-18a", "rp-18b"]

DEL_TITLES = {
    "del-entry": "Удаление данных Mi red — вход",
    "del-owner": "Только владелец может удалить данные сети",
    "del-16a0": "Почта перед удалением",
    "del-16a": "Запрос на удаление данных сети",
    "del-16b": "Подтверждение намерения",
    "del-16b2": "Повторное подтверждение",
    "del-16c": "Проверка Face ID",
    "del-sh-bio": "Системное подтверждение Face ID",
    "del-16d": "Письмо сразу после запроса",
    "del-16d2": "Напоминание за 24 часа",
    "del-16e": "Отмена удаления",
    "del-16e2": "Отмена невозможна",
    "del-16f": "Удаление выполнено",
    "del-16g": "Данные сети стёрты",
    "del-16h": "Итог удаления",
}
RST_TITLES = {sid: f"Сброс Mi red — {sid}" for sid in RST_IDS}
RST_TITLES.update({
    "rst-entry": "Сброс Mi red — вход",
    "rst-owner": "Сброс доступен только владельцу",
    "rst-sms": "Подтверждение по SMS",
    "rst-17m": "Причина сброса",
    "rst-sh-bio": "Face ID для сброса",
    "rst-sh-bio-c": "Повтор Face ID при сбросе",
})
RP_TITLES = {
    "rp-18a": "«Вы видели то, чего не делали?»",
    "rp-18b": "Сигнал принят",
}


def parse_table_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 5:
            continue
        m = re.search(r"`([^`]+)`", parts[1])
        if not m:
            continue
        sid = m.group(1)
        if sid in ("all", "wip"):
            continue
        shot_col = parts[4] if len(parts) > 4 else "Нет"
        rows.append(
            {
                "title": parts[0],
                "id": sid,
                "what": parts[2],
                "function": parts[3],
                "shots_raw": shot_col,
            }
        )
    return rows


def add_extra_screens(rows: list[dict]) -> None:
    existing = {r["id"] for r in rows}
    for sid in DEL_IDS:
        if sid not in existing:
            rows.append(
                {
                    "title": DEL_TITLES.get(sid, sid),
                    "id": sid,
                    "what": "Шаг цепочки удаления данных домашней сети Mi red. Доступно владельцу; секреты роутера при этом не отправляются на сервер в открытом виде.",
                    "function": "Удаление данных Mi red",
                    "shots_raw": "Нет",
                }
            )
    for sid in RST_IDS:
        if sid not in existing:
            rows.append(
                {
                    "title": RST_TITLES.get(sid, sid),
                    "id": sid,
                    "what": "Шаг сброса домашней сети: подтверждения, лимит не чаще трёх раз за 30 дней, уведомления участникам.",
                    "function": "Сброс Mi red",
                    "shots_raw": "Нет",
                }
            )
    for sid in RP_IDS:
        if sid not in existing:
            rows.append(
                {
                    "title": RP_TITLES[sid],
                    "id": sid,
                    "what": "Сообщите в OrroFi, если в журнале сети появилось действие, которого вы не совершали.",
                    "function": "Сигнал о чужих действиях",
                    "shots_raw": "Нет",
                }
            )


PNG_RE = re.compile(r"`([\w.-]+\.png)`")


def load_screen_assets() -> dict[str, list[str]]:
    global _SCREEN_ASSETS
    if _SCREEN_ASSETS is not None:
        return _SCREEN_ASSETS
    _SCREEN_ASSETS = {}
    if not FRAMES_JSON.is_file():
        return _SCREEN_ASSETS
    data = json.loads(FRAMES_JSON.read_text(encoding="utf-8"))
    order: dict[str, list[str]] = defaultdict(list)
    for frame in data.get("frames", []):
        sid = frame.get("screenId")
        file_name = frame.get("file")
        if sid and file_name and file_name not in order[sid]:
            order[sid].append(file_name)
    _SCREEN_ASSETS = dict(order)
    return _SCREEN_ASSETS


def asset_files_for(sid: str, page_slug: str | None = None) -> list[str]:
    files = list(load_screen_assets().get(sid, []))
    if sid == "install" and page_slug == "mi-gestor":
        files.sort(key=lambda x: (0 if x.startswith("gestor") else 1, x))
    elif sid == "install":
        files.sort(key=lambda x: (0 if x.startswith("servicios") else 1, x))
    return files


def resolve_image(path: str) -> tuple[str, bool]:
    p = ROOT / path
    if p.is_file():
        return path, True
    webp = path[:-4] + ".webp" if path.endswith(".png") else path
    if (ROOT / webp).is_file():
        return path, True
    return path, False


def pick_shot_file(
    shots_raw: str, sid: str, page_slug: str | None = None
) -> tuple[str, bool, str]:
    """Return (relative PNG src, file_exists, caption). Prefer iOS in assets/screens/ios/, then proto frames."""
    listed = PNG_RE.findall(shots_raw)

    for name in listed:
        if not name.startswith("ios-"):
            continue
        path = f"assets/screens/ios/{name}"
        if resolve_image(path)[1]:
            return path, True, "Кадр приложения iOS, демонстрационные данные."

    for name in asset_files_for(sid, page_slug):
        path = f"assets/screens/{name}"
        if resolve_image(path)[1]:
            return (
                path,
                True,
                "Кадр прототипа приложения (тёмная тема), демонстрационные данные.",
            )

    for name in listed:
        if name.startswith("brandbook-"):
            fb = BRANDBOOK_FALLBACK.get(name)
            if fb and resolve_image(fb)[1]:
                return fb, True, "Кадр приложения, демонстрационные данные."

    legacy = f"assets/screens/{sid}.png"
    if resolve_image(legacy)[1]:
        return legacy, True, "Кадр прототипа приложения, демонстрационные данные."

    candidates: list[str] = []
    for name in listed:
        if name.startswith("ios-"):
            candidates.append(f"assets/screens/ios/{name}")
    for name in listed:
        if name in BRANDBOOK_FALLBACK:
            candidates.append(BRANDBOOK_FALLBACK[name])
    candidates.extend(f"assets/screens/{n}" for n in asset_files_for(sid, page_slug))
    candidates.append(legacy)

    for path in candidates:
        if resolve_image(path)[1]:
            return path, True, "Кадр приложения, демонстрационные данные."

    fallback = candidates[0] if candidates else legacy
    missing = "Место под кадр: ожидается файл в assets/screens/."
    return fallback, False, missing


def prose_what(what: str, func: str, sid: str) -> str:
    base = sanitize_legal_copy(what.rstrip("."))
    return (
        f"<p>На экране «{html.escape(base)}» собрана часть сценария «{html.escape(func)}». "
        f"Интерфейс приложения на испанском или английском; здесь — смысл на русском.</p>"
    )


def prose_usage(what: str, func: str, sid: str) -> str:
    hints = {
        "login": "Укажите номер телефона, привязанный к договору, и запросите код. SMS приходит в течение минуты; повторная отправка доступна через 60 секунд.",
        "login-code": "Введите пятизначный код из SMS. Код действует пять минут. Если ошиблись — останутся попытки до блокировки.",
        "loginlock": "После пяти неверных кодов вход блокируется на 15 минут. Подождите или свяжитесь с поддержкой через Mi gestor.",
        "manager": "Напишите вопрос обычным текстом или выберите быстрый ответ. Помощник сразу представится как ИИ. Длинные сообщения обрезаются лимитом в 2000 знаков.",
        "handoff": (
            "При необходимости к разговору подключится сотрудник. "
            "История переписки хранится в течение срока, указанного в политике конфиденциальности."
        ),
        "net-0b": "Введите пароль администратора роутера. Пароль Wi‑Fi защищён при передаче и хранении.",
        "fam-14a": "Сверьте шесть цифр с тем, что показывает второй телефон. Так вы убеждаетесь, что приглашаете именно свой дом, а не чужой.",
    }
    text = hints.get(
        sid,
        f"Откройте раздел «{func}» в приложении и дойдите до экрана с идентификатором {sid}. Следуйте подсказкам на экране.",
    )
    text = sanitize_legal_copy(text)
    return f"<p>{html.escape(text)}</p>"


def prose_settings(func: str, sid: str) -> str:
    if "Настройки" in func or sid in ("notifset", "sh-faceid", "profile", "push-why"):
        return "<p>Здесь меняются параметры, которые сохраняются в профиле на этом телефоне: тема, язык, биометрия, типы уведомлений.</p>"
    if sid.startswith("net-") or func.startswith("Mi red"):
        return "<p>Настройки Wi‑Fi, паузы и гостевой сети относятся к домашней сети и не меняют тариф услуги у оператора.</p>"
    return "<p>Отдельного экрана настроек у этого шага нет: значения подтянуты из договора или предыдущих шагов мастера.</p>"


def prose_steps(what: str, sid: str) -> str:
    what_clean = sanitize_legal_copy(what.split(",")[0])
    steps = [
        "Откройте приложение OrroFi на iPhone.",
        f"Дойдите до экрана «{what_clean}».",
        "Прочитайте пояснение и подтвердите действие, если приложение просит согласие или Face ID.",
    ]
    items = "".join(f"<li>{html.escape(s)}</li>" for s in steps)
    return f"<ol>{items}</ol>"


def render_shot(src: str, exists: bool, alt: str, cap: str, depth: int) -> str:
    prefix = "../" * depth
    full_src = prefix + src
    cls = "shot" if exists else "shot missing"
    ph = prefix + "assets/screens/placeholder.svg"
    webp_src = None
    if src.endswith(".png") and exists and (ROOT / src).with_suffix(".webp").is_file():
        webp_src = prefix + src[:-4] + ".webp"
    if webp_src:
        img_tag = (
            f'<picture><source srcset="{html.escape(webp_src)}" type="image/webp">'
            f'<img src="{html.escape(full_src)}" alt="{html.escape(alt)}" width="390" height="844" '
            f'loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\'{html.escape(ph)}\'"></picture>'
        )
    else:
        img_tag = (
            f'<img src="{html.escape(full_src)}" alt="{html.escape(alt)}" width="390" height="844" '
            f'loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\'{html.escape(ph)}\'">'
        )
    return f"""<figure class="{cls}">
{img_tag}
<figcaption>{html.escape(cap)}</figcaption>
</figure>"""


def render_screen_block(screen: dict, depth: int, page_slug: str | None = None) -> str:
    src, exists, cap = pick_shot_file(screen["shots_raw"], screen["id"], page_slug)
    anchor = screen["id"]
    return f"""<article class="screen-block" id="{html.escape(anchor)}">
<header>
<h3>{html.escape(screen['title'])}</h3>
<p class="screen-id">Экран <code>{html.escape(screen['id'])}</code> · {html.escape(screen['function'])}</p>
</header>
<div class="screen-meta">
<dl>
<dt>Что делает</dt>
<dd>{prose_what(screen['what'], screen['function'], screen['id'])}</dd>
<dt>Как пользоваться</dt>
<dd>{prose_usage(screen['what'], screen['function'], screen['id'])}</dd>
<dt>Настройки</dt>
<dd>{prose_settings(screen['function'], screen['id'])}</dd>
<dt>Пошагово</dt>
<dd>{prose_steps(screen['what'], screen['id'])}</dd>
</dl>
</div>
{render_shot(src, exists, f"Экран OrroFi: {screen['title']}", cap, depth)}
</article>"""


def page_for_screen(sid: str, func: str) -> str:
    if sid.startswith("net-") or sid == "net-entry" or sid == "net-sh-mac" or sid == "net-sh-bio" or sid == "net-sh-delcopy":
        return "mi-red"
    if sid.startswith("fam-"):
        return "familia"
    if sid.startswith("del-") or sid.startswith("rst-") or sid.startswith("rp-"):
        return "privacidad"
    if func in ("Mi gestor", "Связь с человеком"):
        return "mi-gestor"
    if func in ("Счета", "Оплата") or sid in ("billing", "invoice", "paymethod", "sterror"):
        return "facturas"
    if func == "Настройки" or sid in ("profile", "notifset", "sh-faceid", "sh-logout", "notif", "push-why"):
        return "ajustes"
    if func == "Приватность" or sid.startswith("sh-delete") or sid in (
        "privacy", "sh-export", "privsched", "sh-faceid-open", "login", "login-code",
        "loginerr", "loginexp", "loginlock", "sh-nocode",
    ):
        return "privacidad"
    if func in (
        "Запуск приложения", "Вход по Face ID", "Вход по SMS", "Подключение нового клиента",
        "Обзор дома", "Аварии", "Визит мастера", "Услуга «Фибра»", "Услуга «Радио»",
        "Услуга «Мобильная связь»", "Услуга «Wi‑Fi»", "Заказ услуги", "Уведомления",
    ) or sid in ("home", "outage", "install", "sh-cita", "fiber", "radio", "mobile", "wifi",
                 "order", "order-date", "order-sum", "order-done", "order-movil", "order-movil-ok",
                 "sh-gb", "sh-pinpuk", "onb", "onbnone", "onb2", "onb3", "stoffline"):
        return "uslugi"
    if func == "Состояния":
        if sid in ("stempty",):
            return "mi-gestor"
        if sid in ("sterror",):
            return "facturas"
        return "uslugi"
    if func in (
        "Mi red: подключение", "Mi red: защита", "Обзор домашней сети", "Устройства в сети",
        "Управление сетью", "Состояние сети", "Безопасность сети", "Управление роутером",
        "Wi‑Fi дома", "Гостевой Wi‑Fi", "Ключи на устройстве", "Оператор и договор",
    ):
        return "mi-red"
    if func == "Семья":
        return "familia"
    return "vozmozhnosti"


def rel_href(target: str, depth: int) -> str:
    if depth == 0:
        return target
    prefix = "../" * depth
    if target == "index.html":
        return prefix
    return prefix + target


def shell(title: str, body: str, depth: int, current: str) -> str:
    nav_links = []
    for href, label in NAV:
        nav_links.append(
            f'<li><a href="{html.escape(rel_href(href, depth))}"'
            + (' aria-current="page"' if href == current else "")
            + f">{html.escape(label)}</a></li>"
        )
    css = rel_href("assets/css/site.css", depth)
    js = rel_href("assets/js/site.js", depth)
    logo = rel_href("logo/lockup-h-dark.svg", depth)
    home = rel_href("index.html", depth)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="OrroFi — домашний интернет и домашняя сеть в одном приложении. Сайт-визитка на русском языке.">
<title>{html.escape(title)} · OrroFi</title>
<link rel="icon" type="image/png" href="{rel_href('icons/ios/AppIcon-60.png', depth)}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<header class="site-header">
<div class="wrap topbar">
<a class="logo" href="{home}"><img src="{logo}" alt="OrroFi" width="160" height="36"></a>
<button type="button" class="nav-toggle" aria-expanded="false" aria-controls="nav">Меню</button>
<nav class="primary" id="nav" aria-label="Основное">
<ul>
{''.join(nav_links)}
</ul>
</nav>
</div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
<div class="wrap">
<p><strong>OrroFi — бренд {html.escape(LEGAL_OWNER["short_name"])}</strong> (NIF {html.escape(LEGAL_OWNER["nif"])}).</p>
<p>{html.escape(FOOTER_COOKIES_LINE)}</p>
<p>
<a href="{rel_href('privacidad/index.html', depth)}">Безопасность и приватность</a>
<a href="{rel_href(f'privacidad/index.html#{SITE_PRIVACY_ANCHOR}', depth)}">Приватность этого сайта</a>
<a href="{rel_href('contacto/index.html', depth)}">Контакты</a>
<a href="mailto:{html.escape(LEGAL_OWNER['email_privacy'])}">{html.escape(LEGAL_OWNER['email_privacy'])}</a>
</p>
<p class="badge-demo">Демонстрационные данные на кадрах приложения. Живая услуга и публикация в магазине — отдельный этап.</p>
</div>
</footer>
<script src="{js}" defer></script>
</body>
</html>"""


def write_page(rel_path: str, title: str, body: str, current: str) -> None:
    depth = 0 if "/" not in rel_path else rel_path.count("/")
    out = ROOT / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(shell(title, body, depth, current), encoding="utf-8")


def _gallery_shot(shots_raw: str, sid: str, alt: str, depth: int) -> str:
    src, exists, cap = pick_shot_file(shots_raw, sid)
    return render_shot(src, exists, alt, cap, depth)


def build_index(depth_content: str) -> str:
    hero_img = pick_shot_file("iOS: `ios-home-es-dark.png`", "home")
    src, exists, cap = hero_img
    shot = render_shot(src, exists, "Главный экран OrroFi", cap, 0)
    return f"""
<section class="hero"><div class="wrap">
<p class="tag" style="font-weight:800;color:var(--accent);text-transform:uppercase;font-size:14px">Приложение OrroFi</p>
<h1>Весь домашний интернет и домашняя сеть — в одном приложении</h1>
<p class="lead">OrroFi помогает видеть услуги, счета и аварии, общаться с умным помощником <strong>Mi gestor</strong> и управлять домашней сетью в разделе <strong>Mi red</strong> — без лишних звонков и с заботой о защите пароля Wi‑Fi.</p>
<div class="hero-actions">
<a class="btn btn-primary" href="vozmozhnosti/">Возможности</a>
<a class="btn btn-secondary" href="instrukcii/">Как начать</a>
</div>
</div></section>
<section><div class="wrap">
<div class="gallery">{shot}</div>
</div></section>
<section><div class="wrap">
<h2>Три опоры</h2>
<div class="grid-3">
<div class="card"><p class="tag">Услуги</p><h3>Фибра, радио, мобильная связь и Wi‑Fi</h3>
<p>Скорость, статус линий, заказ подключения и честные экраны аварии или визита мастера.</p>
<p><a href="uslugi/">Услуги и подключение</a></p></div>
<div class="card"><p class="tag">Помощник</p><h3>Mi gestor</h3>
<p>ИИ сразу представляется, отвечает кратко и при необходимости подключает сотрудника.</p>
<p><a href="mi-gestor/">Подробнее о Mi gestor</a></p></div>
<div class="card"><p class="tag">Дом</p><h3>Mi red и семья</h3>
<p>Устройства в сети, пауза интернета, гостевой Wi‑Fi и безопасное добавление телефона близких по QR.</p>
<p><a href="mi-red/">Mi red</a> · <a href="familia/">Семья</a></p></div>
</div>
</div></section>
<section><div class="wrap">
<h2>Кадры приложения</h2>
<div class="gallery">
{_gallery_shot("iOS: `ios-mi-gestor-chat.png`", "manager", "Чат Mi gestor", 0)}
{_gallery_shot("iOS: `ios-pedido-resumen.png`", "order-sum", "Сводка заказа", 0)}
{_gallery_shot("Брендбук: `brandbook-usage-app-mi-red-430x932.png`", "net-1", "Раздел Mi red", 0)}
{_gallery_shot("iOS: `ios-perfil-dark.png`", "profile", "Профиль", 0)}
</div>
</div></section>
<section><div class="wrap status-banner">
<h2>Честный статус</h2>
<p>Сейчас вы видите <strong>готовое демо-приложение</strong> OrroFi с фиктивными данными. Боевой биллинг, операторская связь и облако ещё не подключены; публикация в App Store — следующий шаг после закрытой беты. Мы не обещаем того, чего в живой услуге пока нет.</p>
</div></section>
{depth_content}
"""


def build_vozmozhnosti(screens_by_page: dict, functions: dict) -> str:
    cards = []
    links = [
        ("uslugi/", "Вход, услуги, заказ, аварии", "Фибра, радио, мобильная связь, Wi‑Fi, визит мастера."),
        ("mi-gestor/", "Mi gestor", "Чат с ИИ, голосовой ввод, передача человеку, тикеты."),
        ("mi-red/", "Mi red", "Роутер, устройства, гости, безопасность, перезапуск."),
        ("familia/", "Семья", "QR, сверка кода, добавление и удаление телефона."),
        ("facturas/", "Счета и оплата", "Список счетов, карточка, SEPA."),
        ("ajustes/", "Настройки", "Тема, язык ES/EN, Face ID, уведомления."),
        ("privacidad/", "Безопасность и приватность", "Вход, шифрование, выгрузка и удаление данных."),
    ]
    for href, title, desc in links:
        count = len(screens_by_page.get(href.rstrip("/"), []))
        cards.append(
            f'<div class="card"><h3>{html.escape(title)}</h3><p>{html.escape(desc)}</p>'
            f"<p>На сайте описано экранов: <strong>{count}</strong>.</p>"
            f'<p><a href="{href}">Подробнее</a></p></div>'
        )
    toc = []
    for func in sorted(functions):
        toc.append(f"<li><a href=\"#fn-{re.sub(r'[^a-z0-9]+', '-', func.lower())}\">{html.escape(func)}</a></li>")
    return f"""
<section class="hero"><div class="wrap">
<h1>Возможности OrroFi</h1>
<p class="lead">Полное оглавление приложения: каждая функция разобрана на отдельных страницах со скриншотами и пошаговыми пояснениями.</p>
</div></section>
<section><div class="wrap"><h2>Разделы сайта</h2><div class="grid-3">{''.join(cards)}</div></div></section>
<section><div class="wrap"><h2>Функции по алфавиту</h2><ul class="toc">{''.join(toc)}</ul>
<p class="note">Всего функций в карте приложения: <strong>{len(functions)}</strong>. Каждая перечислена хотя бы на одной тематической странице.</p>
</div></section>
"""


def build_topic_screens(screens: list[dict], page_slug: str) -> str:
    depth = 1
    blocks = "".join(render_screen_block(s, depth, page_slug) for s in screens)
    toc = "".join(
        f'<li><a href="#{html.escape(s["id"])}">{html.escape(s["title"])}</a></li>' for s in screens
    )
    return f"""
<section><div class="wrap">
<nav aria-label="Экраны на странице"><h2>Содержание</h2><ul class="toc">{toc}</ul></nav>
</div></section>
<section><div class="wrap">{blocks}</div></section>
"""


def build_topic_page(title: str, lead: str, screens: list[dict], page_slug: str) -> str:
    return f"""
<section class="hero"><div class="wrap">
<h1>{html.escape(title)}</h1>
<p class="lead">{lead}</p>
</div></section>
{build_topic_screens(screens, page_slug)}
"""


INSTRUKCII = [
    ("Вход по телефону и SMS", "uslugi/index.html#login", [
        "Откройте OrroFi и введите номер телефона, привязанный к договору.",
        "Запросите код. SMS действует пять минут; повторная отправка — через 60 секунд.",
        "Если код не приходит — откройте подсказку «Не приходит код» и проверьте сеть.",
        "После пяти ошибок вход блокируется на 15 минут.",
    ]),
    ("Заказ услуги и визит мастера", "uslugi/index.html#order-sum", [
        "На главной выберите услугу или раздел «Contratar».",
        "Укажите тариф, дату визита и проверьте адрес в сводке.",
        "Подтвердите согласия на обработку данных.",
        "Чтобы перенести визит — откройте установку и отправьте заявку; её подтверждает человек.",
    ]),
    ("Что делать при аварии", "uslugi/index.html#outage", [
        "На главной появится карточка аварии со статусом.",
        "Следите за этапами: обнаружена → техники в пути → устранена.",
        "Задайте вопрос Mi gestor, если нужны подробности.",
    ]),
    ("Счета и способ оплаты", "facturas/index.html", [
        "Откройте список счетов: суммы в евро, IVA 21 % уже включён.",
        "Откройте карточку счёта для деталей (в демо PDF может отсутствовать).",
        "Проверьте SEPA в способе оплаты.",
    ]),
    ("Mi gestor и живой сотрудник", "mi-gestor/index.html#manager", [
        "Напишите вопрос; помощник представится как ИИ.",
        "Нажмите «Hablar con una persona» в рабочие часы по Мадриду.",
        "Вне часов оставьте заявку — приложение честно скажет, когда ответят.",
    ]),
    ("Включить Mi red", "mi-red/index.html#net-0b", [
        "В профиле откройте Mi red и разрешите доступ к локальной сети iOS.",
        "Введите пароль роутера — он останется зашифрованным на телефоне.",
        "Дождитесь списка устройств и оценки канала.",
    ]),
    ("Добавить телефон семьи", "familia/index.html#fam-13a", [
        "На новом телефоне откройте приглашение с QR.",
        "Существующий телефон дома сканирует код и подтверждает добавление.",
        "Сверьте шесть цифр. При несовпадении приглашение отменится.",
    ]),
    ("Пауза интернета, гости, перезагрузка", "mi-red/index.html#net-1e", [
        "Пауза временно отключает интернет для выбранных устройств.",
        "Гостевая сеть отделена от домашней.",
        "Перезапуск роутера занимает около двух минут — приложение предупредит.",
    ]),
    ("Выгрузка и удаление аккаунта", "privacidad/index.html#privacy", [
        "В приватности запросите выгрузку данных на почту.",
        "Удаление аккаунта может быть запрещено при действующих договорах.",
    ]),
    ("Удаление или сброс Mi red", "privacidad/index.html#del-entry", [
        "Только владелец может удалить данные сети или сбросить её.",
        "Подтвердите Face ID и дождитесь писем с возможностью отмены.",
        "Если видите чужие действия — подайте сигнал «Я этого не делал».",
    ]),
]


def build_instrukcii() -> str:
    items = []
    for title, link, steps in INSTRUKCII:
        sl = "".join(f"<li>{html.escape(sanitize_legal_copy(s))}</li>" for s in steps)
        items.append(
            f'<li><h3>{html.escape(title)}</h3><ol>{sl}</ol><p><a href="../{html.escape(link)}">Связанные экраны</a></p></li>'
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Инструкции</h1>
<p class="lead">Короткие практические руководства — не реклама, а порядок действий в демо-приложении.</p>
</div></section>
<section><div class="wrap"><ol class="steps">{''.join(items)}</ol></div></section>
"""


FAQ = [
    ("Это уже готовое приложение или только макет?", "Это собранное демо-приложение OrroFi с фиктивными данными. Дизайн и сценарии утверждены; живая услуга и магазин — следующий этап."),
    ("На каких языках говорит приложение?", "Интерфейс — испанский и английский. Этот сайт-визитка — на русском."),
    ("Нужен ли аккаунт, если я ещё не клиент?", "Есть сценарий проверки покрытия и заявки для нового адреса. Без покрытия приложение честно сообщит об этом."),
    ("Видит ли OrroFi пароль моего роутера?", "Пароль Wi‑Fi защищён при передаче и хранении."),
    ("Что видят гости Wi‑Fi?", "Гостевая сеть пускает в интернет и отделена от домашней."),
    ("Можно ли добавить телефон мужа или жены?", "Да, по QR и сверке шести цифр, только с согласия владельца."),
    ("Что, если я не просил удалить сеть?", "Используйте сигнал «Я этого не делал» — заявку примут в поддержку."),
    ("Когда появится в магазине приложений?", "Планируется закрытая бета на iOS. Точную дату публикации мы не называем, пока её не утвердят."),
    ("Есть ли версия для Android?", "Сейчас эталон — iOS. Android в объём этой визитки не входит."),
]


def build_faq() -> str:
    items = []
    for q, a in FAQ:
        items.append(
            f"<details><summary>{html.escape(q)}</summary>"
            f"<p>{html.escape(sanitize_legal_copy(a))}</p></details>"
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Вопросы и ответы</h1>
<p class="lead">Кратко о сомнениях, которые чаще всего возникают у будущих пользователей.</p>
</div></section>
<section><div class="wrap faq">{''.join(items)}</div></section>
"""


def lssi_owner_ru() -> str:
    o = LEGAL_OWNER
    return (
        f"Владелец: {o['legal_name']}. NIF: {o['nif']}. "
        f"Адрес: {o['address']}. Регистрация: {o['registry']}. "
        f"Почта: {o['email_privacy']}."
    )


def lssi_owner_es() -> str:
    o = LEGAL_OWNER
    return (
        f"Titular: {o['legal_name']} · NIF {o['nif']} · "
        f"Domicilio: {o['address']} · Inscrita en el {o['registry']} · {o['email_privacy']}"
    )


def build_contacto() -> str:
    o = LEGAL_OWNER
    return f"""
<section class="hero"><div class="wrap">
<h1>Контакты и сведения о компании</h1>
<p class="lead">Как связаться по вопросам данных и где узнать о владельце сайта.</p>
</div></section>
<section><div class="wrap">
<div class="card">
<h2 id="lssi">Сведения о владельце сайта (ст. 10 LSSI)</h2>
<p>{html.escape(lssi_owner_ru())}</p>
<p lang="es">{html.escape(lssi_owner_es())}</p>
</div>
<div class="card">
<h2>OrroFi</h2>
<p>OrroFi — бренд {html.escape(o['short_name'])}. Ответственный за обработку персональных данных (responsable del tratamiento): {html.escape(o['legal_name'])}, NIF {html.escape(o['nif'])}.</p>
<p><strong>Почта по приватности:</strong> <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a></p>
<p>Полный текст политики конфиденциальности приложения и условия услуги появятся здесь до запуска услуги. О политике этого сайта — в разделе <a href="../privacidad/index.html#{SITE_PRIVACY_ANCHOR}">«Приватность на этом сайте»</a>.</p>
</div>
</div></section>
"""


def build_privacidad_intro() -> str:
    o = LEGAL_OWNER
    return f"""
<p class="lead">Здесь собраны экраны входа, приватности, удаления данных Mi red, сброса сети и сигнала о подозрительных действиях.</p>
<p>Контакт по данным: <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a>. Вы вправе обратиться в испанское агентство AEPD.</p>
"""


def build_site_privacy_section() -> str:
    return f"""
<section id="{SITE_PRIVACY_ANCHOR}"><div class="wrap">
<h2>Приватность на этом сайте</h2>
<p>{html.escape(SITE_PRIVACY_TEXT)}</p>
</div></section>
"""


def shot_available_for_screen(screen: dict) -> bool:
    _, exists, _ = pick_shot_file(screen["shots_raw"], screen["id"])
    return exists


def main() -> None:
    text = SCREENS_MD.read_text(encoding="utf-8")
    screens = parse_table_rows(text)
    add_extra_screens(screens)
    screens.sort(key=lambda s: (page_for_screen(s["id"], s["function"]), s["function"], s["id"]))

    by_page: dict[str, list[dict]] = defaultdict(list)
    functions: dict[str, list[dict]] = defaultdict(list)
    for s in screens:
        page = page_for_screen(s["id"], s["function"])
        by_page[page].append(s)
        functions[s["function"]].append(s)

    page_meta = {
        "uslugi": (
            "Услуги и подключение",
            "Фибра, радио, мобильная связь, Wi‑Fi, заказ, аварии, визит мастера и подключение нового клиента.",
            "uslugi/index.html",
        ),
        "mi-gestor": ("Mi gestor", "Умный помощник, лимиты чата, голос, передача человеку и тикеты.", "mi-gestor/index.html"),
        "mi-red": ("Mi red", "Домашняя сеть: роутер, устройства, гости, безопасность и диагностика.", "mi-red/index.html"),
        "familia": ("Семья", "Безопасное добавление телефона близких в домашнюю сеть.", "familia/index.html"),
        "facturas": ("Счета и оплата", "Список счетов, карточка и SEPA.", "facturas/index.html"),
        "ajustes": ("Настройки", "Профиль, тема, язык, Face ID и уведомления.", "ajustes/index.html"),
        "privacidad": ("Безопасность и приватность", build_privacidad_intro(), "privacidad/index.html"),
    }

    write_page("index.html", "Главная", build_index(""), "index.html")
    write_page(
        "vozmozhnosti/index.html",
        "Возможности",
        build_vozmozhnosti({k: by_page.get(k, []) for k in page_meta}, functions),
        "vozmozhnosti/index.html",
    )

    for slug, (title, lead, current) in page_meta.items():
        body = build_topic_page(title, lead if isinstance(lead, str) else str(lead), by_page[slug], slug)
        if slug == "privacidad":
            body = (
                f'<section class="hero"><div class="wrap"><h1>{html.escape(title)}</h1>'
                f"{build_privacidad_intro()}</div></section>"
                + build_site_privacy_section()
                + build_topic_screens(by_page[slug], slug)
            )
        write_page(f"{slug}/index.html", title, body, current)

    write_page("instrukcii/index.html", "Инструкции", build_instrukcii(), "instrukcii/index.html")
    write_page("faq/index.html", "FAQ", build_faq(), "faq/index.html")
    write_page("contacto/index.html", "Контакты", build_contacto(), "contacto/index.html")

    # Report
    func_no_shot = []
    for func, flist in sorted(functions.items()):
        if not any(shot_available_for_screen(s) for s in flist):
            func_no_shot.append(func)
    report = ROOT / "scripts" / "site_report.txt"
    report.write_text(
        "\n".join(
            [
                f"screens_total={len(screens)}",
                f"functions_total={len(functions)}",
                f"functions_without_committed_shot={len(func_no_shot)}",
                "functions_missing_any_committed_shot:",
                *func_no_shot,
            ]
        ),
        encoding="utf-8",
    )
    print(f"Generated {len(screens)} screens, {len(functions)} functions")
    print(f"Functions without committed screenshot: {len(func_no_shot)}")


if __name__ == "__main__":
    main()