#!/usr/bin/env python3
"""Generate static Russian OrroFi marketing site (HTML) from scripts/data/screens.md."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENS_MD = ROOT / "scripts" / "data" / "screens.md"
IOS_SHOTS_DIR = ROOT / "assets" / "screens" / "ios"
FRAMES_JSON = ROOT / "tools/render-screens/frames.json"

# Брендбук в репозиторий не кладём — только замены для вёрстки.
BRANDBOOK_FALLBACK: dict[str, str] = {
    "brandbook-usage-splash-430x932.png": "assets/screens/ios/ios-home-es-dark.png",
    "brandbook-usage-hero-1600x900.png": "assets/screens/ios/ios-home-es-dark.png",
    "brandbook-usage-app-mi-red-430x932.png": "assets/screens/mi-red-1-resumen.png",
}
_SCREEN_ASSETS: dict[str, list[str]] | None = None
MISSING_IMAGES: list[str] = []
PLACEHOLDER_SRC = "assets/screens/placeholder.svg"

# Кадры с служебными заглушками, «Provisional» или бейджем DEMO — не публикуем.
BANNED_SHOT_FILES = frozenset(
    {
        "ios-snapshot-privacidad-iphone-se.png",
        "ios-pedido-privacidad-consentimiento.png",
        "ios-login-es-dark.png",
        "ios-login-es-light.png",
        "ios-mi-gestor-chat.png",
    }
)

PRICE_EXAMPLE_SCREENS = frozenset(
    {
        "home",
        "billing",
        "invoice",
        "paymethod",
        "fiber",
        "mobile",
        "radio",
        "wifi",
        "order",
        "order-sum",
        "order-date",
        "order-done",
        "order-movil",
        "order-movil-ok",
        "sh-gb",
    }
)

PUBLISHED_PAGES = [
    "index.html",
    "vozmozhnosti/index.html",
    "uslugi/index.html",
    "mi-gestor/index.html",
    "mi-red/index.html",
    "familia/index.html",
    "facturas/index.html",
    "ajustes/index.html",
    "instrukcii/index.html",
    "privacidad/index.html",
    "faq/index.html",
    "contacto/index.html",
]

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

META_DESCRIPTIONS: dict[str, str] = {
    "index.html": (
        "OrroFi — домашний интернет, Wi‑Fi и устройства в одном приложении: "
        "видно, кто в сети, почему тормозит связь и что со счетами."
    ),
    "vozmozhnosti/index.html": "Всё, что умеет OrroFi: разделы приложения, кадры и короткие пояснения.",
    "uslugi/index.html": (
        "Оптика, радиодоступ, мобильная связь и Wi‑Fi: заказ, сбои, визит мастера и подключение нового дома."
    ),
    "mi-gestor/index.html": "Помощник OrroFi: короткие ответы, голос, разговор с человеком и заявки.",
    "mi-red/index.html": "Домашняя сеть: роутер, устройства, гости, безопасность и перезапуск.",
    "familia/index.html": "Как добавить телефон близких в домашнюю сеть — по QR и сверке кода.",
    "facturas/index.html": "Счета, подробности платежа и банковское поручение SEPA.",
    "ajustes/index.html": "Профиль, тема, язык, вход по Face ID и уведомления.",
    "instrukcii/index.html": "Короткие шаги по демонстрации OrroFi.",
    "privacidad/index.html": "Вход, данные, удаление и сброс домашней сети, сигнал о чужих действиях.",
    "faq/index.html": "Короткие ответы на частые вопросы об OrroFi.",
    "contacto/index.html": "Кто стоит за OrroFi и как нам написать.",
}
META_DEFAULT = "OrroFi — домашний интернет и Wi‑Fi в одном приложении."

ROUTER_PASSWORD_NEUTRAL = "Пароль защищён при передаче и хранении."

CSP_POLICY = (
    "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
    "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'"
)


def sanitize_legal_copy(text: str) -> str:
    """Смягчение формулировок по ревью Legal и Security."""
    rules = [
        (
            "Нет в открытом виде. Пароль шифруется на iPhone; на сервер уходит только шифр.",
            ROUTER_PASSWORD_NEUTRAL,
        ),
        (
            "Пароль шифруется на iPhone; на сервер уходит только шифр, не открытый пароль.",
            ROUTER_PASSWORD_NEUTRAL,
        ),
        (
            "Он шифруется на iPhone и на сервер уходит только шифр, не открытый пароль.",
            ROUTER_PASSWORD_NEUTRAL,
        ),
        (
            "Пароль роутера шифруется на телефоне",
            ROUTER_PASSWORD_NEUTRAL.rstrip("."),
        ),
        (
            "Пароль Wi‑Fi защищён при передаче и хранении.",
            ROUTER_PASSWORD_NEUTRAL,
        ),
        (
            "Пароль Wi‑Fi защищён при передаче и хранении",
            ROUTER_PASSWORD_NEUTRAL.rstrip("."),
        ),
        (
            "Ввод пароля (секрет остаётся на устройстве)",
            "Ввод пароля роутера",
        ),
        (
            "секрет остаётся на устройстве",
            "ввод на устройстве",
        ),
        (
            "секреты роутера при этом не отправляются на сервер в открытом виде",
            "",
        ),
        (
            "Шаг цепочки удаления данных домашней сети Mi red. Доступно владельцу; .",
            "Шаг удаления данных домашней сети Mi red. Доступно только владельцу.",
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
            f"Введите пароль роутера. {ROUTER_PASSWORD_NEUTRAL}",
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
    ("mi-gestor/index.html", "Помощник (Mi gestor)"),
    ("mi-red/index.html", "Сеть (Mi red)"),
    ("familia/index.html", "Семья"),
    ("facturas/index.html", "Счета"),
    ("ajustes/index.html", "Настройки"),
    ("instrukcii/index.html", "Инструкции"),
    ("privacidad/index.html", "Безопасность"),
    ("faq/index.html", "Вопросы"),
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
RST_TITLES = {
    "rst-entry": "Сброс домашней сети — вход",
    "rst-owner": "Сброс доступен только владельцу",
    "rst-sms": "Подтверждение по SMS",
    "rst-17m": "Причина сброса",
    "rst-17a": "Запрос на сброс сети",
    "rst-17b": "Что изменится после сброса",
    "rst-17c": "Подтверждение намерения",
    "rst-17d": "Код из SMS",
    "rst-17e": "Сброс запланирован",
    "rst-17f": "Письмо участникам сети",
    "rst-17g": "Напоминание перед сбросом",
    "rst-17h": "Отмена сброса",
    "rst-17i": "Сброс отменён",
    "rst-17j": "Слишком частые сбросы",
    "rst-17k": "Сброс выполняется",
    "rst-17l": "Сеть сброшена",
    "rst-sh-bio": "Face ID для сброса",
    "rst-sh-bio-c": "Повтор Face ID при сбросе",
}
RST_WHAT = {
    "rst-entry": "Начало цепочки сброса домашней сети Mi red.",
    "rst-owner": "Если вы не владелец, сброс недоступен — так защищают чужую сеть.",
    "rst-sms": "Подтверждение по SMS, что сброс запрашивает именно владелец.",
    "rst-17m": "Выберите причину: смена роутера, продажа дома или другое.",
    "rst-17a": "Приложение просит подтвердить, что вы хотите сбросить сеть.",
    "rst-17b": "Кратко объясняет, какие данные Wi‑Fi и устройств исчезнут.",
    "rst-17c": "Повторное подтверждение перед серьёзным шагом.",
    "rst-17d": "Ввод одноразового кода из SMS.",
    "rst-17e": "Сброс назначен на время; до него можно передумать.",
    "rst-17f": "Участникам сети уходит письмо о предстоящем сбросе.",
    "rst-17g": "Напоминание, что сброс скоро начнётся.",
    "rst-17h": "Владелец отменяет сброс, пока это возможно.",
    "rst-17i": "Сброс снят, сеть работает как раньше.",
    "rst-17j": "Если сбросов слишком много подряд, приложение попросит подождать.",
    "rst-17k": "Идёт сброс: подождите, не закрывая экран.",
    "rst-17l": "Сеть сброшена; дальше — заново подключить роутер и устройства.",
    "rst-sh-bio": "Система просит Face ID, чтобы никто другой не сбросил сеть.",
    "rst-sh-bio-c": "Повтор Face ID, если первое подтверждение не прошло.",
}
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
                "title": sanitize_legal_copy(parts[0]),
                "id": sid,
                "what": sanitize_legal_copy(parts[2]),
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
                    "what": "Шаг удаления данных домашней сети Mi red. Доступно только владельцу.",
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
                    "what": RST_WHAT.get(
                        sid,
                        "Шаг сброса домашней сети: подтверждения, ограничение частоты и уведомления участникам.",
                    ),
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


def with_price_note(sid: str, caption: str) -> str:
    if sid in PRICE_EXAMPLE_SCREENS and "условн" not in caption:
        return caption.rstrip(".") + ". Цены в демонстрации условные."
    return caption


def pick_shot_file(
    shots_raw: str, sid: str, page_slug: str | None = None
) -> tuple[str, bool, str]:
    """Return (relative PNG src, file_exists, caption). Prefer iOS in assets/screens/ios/, then proto frames."""
    listed = [n for n in PNG_RE.findall(shots_raw) if n not in BANNED_SHOT_FILES]

    for name in listed:
        if not name.startswith("ios-"):
            continue
        path = f"assets/screens/ios/{name}"
        if resolve_image(path)[1]:
            return path, True, with_price_note(sid, "Демонстрационные данные на кадре.")

    for name in asset_files_for(sid, page_slug):
        if name in BANNED_SHOT_FILES:
            continue
        path = f"assets/screens/{name}"
        if resolve_image(path)[1]:
            return path, True, with_price_note(sid, "Демонстрационные данные на кадре.")

    for name in listed:
        if name.startswith("brandbook-"):
            fb = BRANDBOOK_FALLBACK.get(name)
            if fb and resolve_image(fb)[1]:
                return fb, True, with_price_note(sid, "Демонстрационные данные на кадре.")

    legacy = f"assets/screens/{sid}.png"
    if resolve_image(legacy)[1]:
        return legacy, True, with_price_note(sid, "Демонстрационные данные на кадре.")

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
        if Path(path).name in BANNED_SHOT_FILES:
            continue
        if resolve_image(path)[1]:
            return path, True, with_price_note(sid, "Демонстрационные данные на кадре.")

    intended = candidates[0] if candidates else legacy
    if intended != PLACEHOLDER_SRC:
        MISSING_IMAGES.append(f"{sid}: {intended}")
    return PLACEHOLDER_SRC, True, "Кадр появится позже."


SCREEN_SECOND_LINE: dict[str, str] = {
    "billing": "Здесь видны счета и ближайший платёж. Цены в демонстрации условные.",
    "home": "Суммы и тарифы на экране — пример: цены в демонстрации условные.",
    "manager": "Помощник сразу говорит, что он искусственный интеллект.",
    "handoff": "В рабочие часы по мадридскому времени разговор можно передать человеку.",
    "net-0b": ROUTER_PASSWORD_NEUTRAL,
    "fam-14a": "Так вы убеждаетесь, что приглашаете именно свой дом, а не чужой.",
    "login": "Номер должен совпадать с договором.",
    "rp-18a": "Так вы сообщаете о подозрительном действии в аккаунте.",
}


def polish_display_text(text: str) -> str:
    text = sanitize_legal_copy(text.strip())
    pairs = [
        ("IVA 21 % включён, всегда евро", "суммы в евро; на демонстрации налог IVA включён в сумму"),
        ("IVA 21 % уже включён", "налог IVA уже включён в сумму"),
        ("IVA 21 % включён", "налог IVA включён в сумму"),
        (", всегда евро", ""),
        ("всегда евро", "суммы в евро"),
        ("домашней фибры", "домашней оптики"),
        ("домашней фибре", "домашней оптике"),
        ("Услуга «Фибра»", "Услуга «Оптика» (Fibra)"),
        ("Услуга «Радио»", "Услуга «Радиодоступ»"),
        ("Лента извещений", "Лента уведомлений"),
        ("Лента извещений", "Лента уведомлений"),
        ("Какие извещения", "Какие уведомления"),
        ("Извещение:", "Уведомление:"),
        ("извещений", "уведомлений"),
        ("извещения", "уведомления"),
        ("пуш-извещения", "push-уведомления"),
        ("лимит в 2000 знаков", "длинные сообщения приложение сократит"),
        ("лимит 2000 знаков", "длинные сообщения приложение сократит"),
        (
            "таймер повторной отправки (60 с), код живёт 5 мин",
            "таймер повторной отправки; код из SMS действует недолго",
        ),
        ("Блок на 15 минут после 5 неверных попыток", "Вход на время закрывается после нескольких неверных кодов"),
        ("ИИ-помощник", "Помощник"),
        ("тикеты", "заявки"),
        ("Тикеты", "Заявки"),
        ("биометрия", "вход по лицу или отпечатку"),
        ("Фибра", "Оптика"),
        ("фибры", "оптики"),
        ("— радио,", "— радиодоступ,"),
        ("радио, мобильная", "радиодоступ, мобильная"),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    text = re.sub(r"«\s*«+", "«", text)
    text = re.sub(r"»\s*»+", "»", text)
    return text


def screen_copy_html(screen: dict) -> str:
    title = polish_display_text(screen["title"])
    what = polish_display_text(screen["what"])
    func = polish_display_text(screen["function"])
    sid = screen["id"]
    lines: list[str] = []
    primary = what if what else f"{title} — раздел «{func}»."
    lines.append(primary.rstrip("."))
    extra = SCREEN_SECOND_LINE.get(sid)
    if extra:
        lines.append(sanitize_legal_copy(extra.rstrip(".")))
    unique: list[str] = []
    for line in lines:
        cleaned = line.strip().rstrip(".")
        if cleaned and cleaned not in unique:
            unique.append(cleaned)
    unique = unique[:2]
    paras = "".join(f"<p>{html.escape(line)}.</p>" for line in unique)
    return f'<div class="screen-copy">{paras}</div>'


def render_shot(src: str, exists: bool, alt: str, cap: str, depth: int) -> str:
    prefix = "../" * depth
    full_src = prefix + src
    is_placeholder = src.endswith("placeholder.svg")
    cls = "shot" + (" shot-placeholder" if is_placeholder else "")
    ph = prefix + PLACEHOLDER_SRC
    webp_src = None
    if (
        src.endswith(".png")
        and not is_placeholder
        and exists
        and (ROOT / src).with_suffix(".webp").is_file()
    ):
        webp_src = prefix + src[:-4] + ".webp"
    img_attrs = (
        f'class="shot-img" src="{html.escape(full_src)}" alt="{html.escape(alt)}" '
        f'width="390" height="844" loading="lazy" decoding="async" '
        f'data-fallback-src="{html.escape(ph)}"'
    )
    if webp_src:
        img_tag = (
            f'<picture><source srcset="{html.escape(webp_src)}" type="image/webp">'
            f"<img {img_attrs}></picture>"
        )
    else:
        img_tag = f"<img {img_attrs}>"
    return f"""<figure class="{cls}">
{img_tag}
<figcaption>{html.escape(cap)}</figcaption>
</figure>"""


def render_screen_block(screen: dict, depth: int, page_slug: str | None = None) -> str:
    src, exists, cap = pick_shot_file(screen["shots_raw"], screen["id"], page_slug)
    anchor = screen["id"]
    title = polish_display_text(screen["title"])
    return f"""<article class="screen-block" id="{html.escape(anchor)}">
<header>
<h3>{html.escape(title)}</h3>
</header>
{screen_copy_html(screen)}
{render_shot(src, exists, f"Экран OrroFi: {title}", cap, depth)}
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


def document_title(page_title: str) -> str:
    if page_title.startswith("OrroFi —"):
        return page_title
    return f"{page_title} · OrroFi"


def shell(title: str, body: str, depth: int, current: str) -> str:
    meta_desc = META_DESCRIPTIONS.get(current, META_DEFAULT)
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
<meta name="description" content="{html.escape(meta_desc)}">
<meta http-equiv="Content-Security-Policy" content="{CSP_POLICY}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{html.escape(document_title(title))}</title>
<link rel="icon" type="image/png" href="{rel_href('icons/ios/AppIcon-60.png', depth)}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<header class="site-header">
<div class="wrap topbar">
<a class="logo" href="{home}"><img src="{logo}" alt="OrroFi" width="98" height="36"></a>
<button type="button" class="nav-toggle" aria-expanded="false" aria-controls="nav">Меню</button>
<nav class="primary" id="nav" aria-label="Основное меню">
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
<p><strong>OrroFi</strong> · {html.escape(LEGAL_OWNER["short_name"])} (NIF {html.escape(LEGAL_OWNER["nif"])}), правообладатель бренда OrroFi.</p>
<p>{html.escape(FOOTER_COOKIES_LINE)}</p>
<p>
<a href="{rel_href('privacidad/index.html', depth)}">Безопасность и приватность</a>
<a href="{rel_href(f'privacidad/index.html#{SITE_PRIVACY_ANCHOR}', depth)}">Приватность этого сайта</a>
<a href="{rel_href('contacto/index.html', depth)}">Контакты</a>
<a href="mailto:{html.escape(LEGAL_OWNER['email_privacy'])}">{html.escape(LEGAL_OWNER['email_privacy'])}</a>
</p>
<p class="badge-demo">На кадрах — демонстрационные данные. Живая услуга и публикация в магазине приложений ещё впереди.</p>
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
<p class="tag hero-tag">Приложение OrroFi</p>
<h1>Весь домашний интернет и домашняя сеть — в одном приложении</h1>
<p class="lead">OrroFi помогает следить за услугами, счетами и сбоями, писать помощнику <strong>Mi gestor</strong> и управлять домашней сетью в разделе <strong>Mi red</strong> — чаще без звонка в поддержку. Пароль роутера в открытом виде мы не забираем.</p>
<div class="hero-actions">
<a class="btn btn-primary" href="vozmozhnosti/">Возможности</a>
<a class="btn btn-secondary" href="instrukcii/">Как начать</a>
</div>
</div></section>
<section><div class="wrap">
<div class="gallery">{shot}</div>
</div></section>
<section><div class="wrap">
<h2>На чём держится OrroFi</h2>
<div class="grid-3">
<div class="card"><p class="tag">Услуги</p><h3>Оптика, радиодоступ, мобильная связь и Wi‑Fi</h3>
<p>Скорость и состояние связи, заказ подключения, сбой и визит мастера — без прикрас.</p>
<p><a href="uslugi/">Услуги и подключение</a></p></div>
<div class="card"><p class="tag">Помощник</p><h3>Mi gestor</h3>
<p>Помощник сразу говорит, что он искусственный интеллект, отвечает коротко и в рабочие часы может передать разговор человеку.</p>
<p><a href="mi-gestor/">Подробнее о Mi gestor</a></p></div>
<div class="card"><p class="tag">Дом</p><h3>Mi red и семья</h3>
<p>Устройства в сети, пауза интернета, гостевой Wi‑Fi и добавление телефона близких по QR и сверке кода.</p>
<p><a href="mi-red/">Mi red</a> · <a href="familia/">Семья</a></p></div>
</div>
</div></section>
<section><div class="wrap">
<h2>Кадры приложения</h2>
<div class="gallery">
{_gallery_shot("`gestor-1-chat.png`", "manager", "Чат Mi gestor", 0)}
{_gallery_shot("iOS: `ios-pedido-resumen.png`", "order-sum", "Сводка заказа", 0)}
{_gallery_shot("Брендбук: `brandbook-usage-app-mi-red-430x932.png`", "net-1", "Раздел Mi red", 0)}
{_gallery_shot("iOS: `ios-perfil-dark.png`", "profile", "Профиль", 0)}
</div>
</div></section>
<section><div class="wrap status-banner">
<h2>Честный статус</h2>
<p>Сейчас это демонстрация OrroFi с вымышленными данными. Живые счета, связь с оператором и публикация в App Store ещё впереди — после закрытой беты. Мы не обещаем того, чего пока нет.</p>
</div></section>
{depth_content}
"""


def build_vozmozhnosti(
    screens_by_page: dict, functions: dict[str, list[dict]], depth: int = 1
) -> str:
    cards = []
    links = [
        ("uslugi/index.html", "uslugi", "Вход, услуги, заказ, сбои", "Оптика, радиодоступ, мобильная связь, Wi‑Fi, визит мастера."),
        ("mi-gestor/index.html", "mi-gestor", "Mi gestor", "Чат с помощником, голос, разговор с человеком, заявки."),
        ("mi-red/index.html", "mi-red", "Mi red", "Роутер, устройства, гости, безопасность, перезапуск."),
        ("familia/index.html", "familia", "Семья", "QR, сверка кода, добавление и удаление телефона."),
        ("facturas/index.html", "facturas", "Счета и оплата", "Счета, подробности платежа и SEPA."),
        ("ajustes/index.html", "ajustes", "Настройки", "Тема, язык (испанский и английский), вход по Face ID, уведомления."),
        ("privacidad/index.html", "privacidad", "Безопасность и приватность", "Вход, защита данных, выгрузка и удаление."),
    ]
    for page_href, _slug, title, desc in links:
        cards.append(
            f'<div class="card"><h3>{html.escape(title)}</h3><p>{html.escape(desc)}</p>'
            f'<p><a href="{rel_href(page_href, depth)}">Подробнее</a></p></div>'
        )
    toc = []
    for func in sorted(functions):
        flist = functions[func]
        screen = flist[0]
        page = page_for_screen(screen["id"], func)
        href = rel_href(f"{page}/index.html#{screen['id']}", depth)
        toc.append(
            f'<li><a href="{html.escape(href)}">{html.escape(polish_display_text(func))}</a></li>'
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Возможности OrroFi</h1>
<p class="lead">Всё, что умеет OrroFi: разделы приложения, кадры и короткие пояснения.</p>
</div></section>
<section><div class="wrap"><h2>Разделы сайта</h2><div class="grid-3">{''.join(cards)}</div></div></section>
<section><div class="wrap"><h2>Функции по алфавиту</h2><ul class="toc">{''.join(toc)}</ul>
<p class="note">Ниже — все возможности, о которых рассказывает этот сайт.</p>
</div></section>
"""


def build_topic_screens(screens: list[dict], page_slug: str) -> str:
    depth = 1
    blocks = "".join(render_screen_block(s, depth, page_slug) for s in screens)
    toc = "".join(
        f'<li><a href="#{html.escape(s["id"])}">{html.escape(polish_display_text(s["title"]))}</a></li>'
        for s in screens
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
    ("Вход по телефону и SMS", "privacidad/index.html#login", [
        "Откройте OrroFi и введите номер телефона, привязанный к договору.",
        "Запросите код. Код из SMS действует недолго; если ошибиться несколько раз, вход на время закрывается.",
        "Если код не приходит — откройте подсказку «Не приходит код» и проверьте сеть.",
    ]),
    ("Заказ услуги и визит мастера", "uslugi/index.html#order-sum", [
        "На главной выберите услугу или «Оформить» («Contratar»).",
        "Укажите тариф, дату визита и проверьте адрес в сводке.",
        "Подтвердите согласия на обработку данных.",
        "Чтобы перенести визит, откройте экран визита мастера и отправьте заявку; её подтвердит человек.",
    ]),
    ("Что делать при аварии", "uslugi/index.html#outage", [
        "На главной появится карточка аварии со статусом.",
        "Следите за этапами: обнаружена → техники в пути → устранена.",
        "Задайте вопрос Mi gestor, если нужны подробности.",
    ]),
    ("Счета и способ оплаты", "facturas/index.html", [
        "Откройте список счетов: суммы в евро; в демонстрации налог IVA уже включён в сумму.",
        "Откройте карточку счёта для деталей (в демонстрации PDF может отсутствовать).",
        "В способе оплаты проверьте банковское поручение SEPA.",
    ]),
    ("Mi gestor и живой сотрудник", "mi-gestor/index.html#manager", [
        "Напишите вопрос; помощник сразу говорит, что он искусственный интеллект.",
        "Нажмите «Поговорить с человеком» («Hablar con una persona») в рабочие часы по мадридскому времени.",
        "Если сотрудник недоступен, оставьте заявку в чате.",
    ]),
    ("Включить Mi red", "mi-red/index.html#net-0b", [
        "В профиле откройте Mi red и разрешите доступ к локальной сети.",
        f"Введите пароль роутера. {ROUTER_PASSWORD_NEUTRAL}",
        "Дождитесь списка устройств и оценки качества сети.",
    ]),
    ("Добавить телефон семьи", "familia/index.html#fam-13a", [
        "На новом телефоне откройте приглашение с QR.",
        "Существующий телефон дома сканирует код и подтверждает добавление.",
        "Сверьте шесть цифр. При несовпадении приглашение отменится.",
    ]),
    ("Пауза интернета, гости, перезагрузка", "mi-red/index.html#net-1e", [
        "Пауза временно отключает интернет для выбранных устройств.",
        "Гостевая сеть отделена от домашней.",
        "Приложение предупредит, что перезапуск займёт некоторое время.",
    ]),
    ("Выгрузка и удаление аккаунта", "privacidad/index.html#privacy", [
        "В приватности запросите выгрузку данных на почту.",
        "Удаление аккаунта может быть запрещено при действующих договорах.",
    ]),
    ("Удаление или сброс Mi red", "privacidad/index.html#del-entry", [
        "Только владелец может удалить данные сети или сбросить её.",
        "Подтвердите Face ID и дождитесь писем с возможностью отмены.",
        "Если видите чужие действия — откройте «Вы видели то, чего не делали?».",
    ]),
]


def build_instrukcii() -> str:
    items = []
    for title, link, steps in INSTRUKCII:
        sl = "".join(f"<li>{html.escape(sanitize_legal_copy(s))}</li>" for s in steps)
        items.append(
            f'<li><h2 class="step-title">{html.escape(title)}</h2><ol>{sl}</ol>'
            f'<p><a href="../{html.escape(link)}">Смотреть кадры</a></p></li>'
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Инструкции</h1>
<p class="lead">Короткие шаги по демонстрации OrroFi.</p>
</div></section>
<section><div class="wrap"><ol class="steps">{''.join(items)}</ol></div></section>
"""


FAQ = [
    (
        "Это уже готовое приложение или только макет?",
        "Это демонстрация OrroFi с вымышленными данными. Живая услуга и публикация в магазине приложений ещё впереди.",
    ),
    (
        "На каких языках говорит приложение?",
        "Само приложение — на испанском и английском. Этот сайт — на русском.",
    ),
    (
        "Нужен ли аккаунт, если я ещё не клиент?",
        "Можно проверить покрытие и оставить заявку на новый адрес. Если покрытия нет, приложение об этом скажет прямо.",
    ),
    ("Видит ли OrroFi пароль моего роутера?", ROUTER_PASSWORD_NEUTRAL),
    ("Что видят гости Wi‑Fi?", "Гостевая сеть пускает в интернет и отделена от домашней."),
    ("Можно ли добавить телефон мужа или жены?", "Да, по QR и сверке шести цифр, только с согласия владельца."),
    (
        "Что, если я не просил удалить сеть?",
        "Нажмите «Вы видели то, чего не делали?» — мы разберёмся.",
    ),
    (
        "Когда появится в магазине приложений?",
        "Планируется закрытая бета на iOS. Точную дату публикации мы не называем, пока её не утвердят.",
    ),
    (
        "Есть ли версия для Android?",
        "Пока образец приложения — iOS. Про Android расскажем отдельно, когда будет что показать.",
    ),
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
<p class="lead">Короткие ответы на частые вопросы.</p>
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
<h1>Контакты</h1>
<p class="lead">Кто стоит за OrroFi и как нам написать.</p>
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
<p><strong>По вопросам персональных данных:</strong> <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a></p>
<p>Политика конфиденциальности приложения появится здесь, когда будет готова. О политике этого сайта — в разделе <a href="../privacidad/index.html#{SITE_PRIVACY_ANCHOR}">«Приватность на этом сайте»</a>.</p>
</div>
</div></section>
"""


def build_privacidad_intro() -> str:
    o = LEGAL_OWNER
    return f"""
<p class="lead">Вход, данные, удаление и сброс домашней сети, сигнал, если в аккаунте произошло что-то чужое.</p>
<p>По вопросам данных: <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a>. При необходимости можно обратиться в испанское агентство по защите данных (AEPD).</p>
"""


def build_site_privacy_section() -> str:
    return f"""
<section id="{SITE_PRIVACY_ANCHOR}"><div class="wrap">
<h2>Приватность на этом сайте</h2>
<p>{html.escape(SITE_PRIVACY_TEXT)}</p>
</div></section>
"""


def shot_available_for_screen(screen: dict) -> bool:
    src, _, _ = pick_shot_file(screen["shots_raw"], screen["id"])
    return src != PLACEHOLDER_SRC and (ROOT / src).is_file()


IGNORE_LINK_FRAGMENTS = frozenset({"main", "nav", "top"})


def normalize_site_path(path: str) -> str:
    p = path.strip("/")
    if p in ("", "."):
        return "index.html"
    if not p.endswith((".html", ".css", ".js", ".svg", ".png", ".webp", ".woff2", ".txt")):
        return f"{p}/index.html" if not p.endswith("/") else f"{p.rstrip('/')}/index.html"
    return p


def resolve_href(from_page: str, href: str) -> tuple[str | None, str | None]:
    if href.startswith(("mailto:", "http:", "https:", "tel:")):
        return None, None
    frag = ""
    path = href
    if "#" in href:
        path, frag = href.split("#", 1)
    if path.startswith("#") or path == "":
        target = from_page
        return target, frag or None
    base_dir = (ROOT / from_page).parent
    target = (base_dir / path).resolve().relative_to(ROOT).as_posix()
    target = normalize_site_path(target)
    return target, frag or None


def validate_published_site(anchors: dict[str, set[str]]) -> None:
    errors: list[str] = []
    for page in PUBLISHED_PAGES:
        p = ROOT / page
        if not p.is_file():
            errors.append(f"missing page: {page}")
            continue
        text = p.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            target, frag = resolve_href(page, href)
            if target is None:
                continue
            if target not in anchors and not (ROOT / target).is_file():
                errors.append(f"{page}: broken link {href} -> {target}")
            elif (
                frag
                and frag not in IGNORE_LINK_FRAGMENTS
                and target in anchors
                and frag not in anchors[target]
            ):
                errors.append(f"{page}: missing anchor #{frag} in {target}")
        for src in re.findall(r'\b(?:src|srcset)="([^"]+)"', text):
            for part in re.split(r",\s*", src):
                url = part.strip().split()[0] if " " in part.strip() else part.strip()
                if not url or url.startswith("data:"):
                    continue
                tp, _ = resolve_href(page, url)
                if tp and not (ROOT / tp).is_file():
                    errors.append(f"{page}: missing asset {url} -> {tp}")
    if errors:
        raise SystemExit("Site validation failed:\n" + "\n".join(errors[:50]) + (f"\n... +{len(errors)-50}" if len(errors) > 50 else ""))


def collect_site_anchors(by_page: dict[str, list[dict]]) -> dict[str, set[str]]:
    anchors: dict[str, set[str]] = {p: set() for p in PUBLISHED_PAGES}
    for slug, slist in by_page.items():
        rel = f"{slug}/index.html"
        if rel in anchors:
            anchors[rel] = {s["id"] for s in slist}
    anchors["contacto/index.html"].add("lssi")
    anchors["privacidad/index.html"].add(SITE_PRIVACY_ANCHOR)
    return anchors


def main() -> None:
    global MISSING_IMAGES
    MISSING_IMAGES = []
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
            "Оптика, радиодоступ, мобильная связь и Wi‑Fi: заказ, сбои, визит мастера и подключение нового дома.",
            "uslugi/index.html",
        ),
        "mi-gestor": (
            "Mi gestor",
            "Помощник: короткие ответы, голос, разговор с человеком и заявки.",
            "mi-gestor/index.html",
        ),
        "mi-red": (
            "Mi red",
            "Домашняя сеть: роутер, устройства, гости, безопасность и диагностика.",
            "mi-red/index.html",
        ),
        "familia": (
            "Семья",
            "Как добавить телефон близких в домашнюю сеть — по QR и сверке кода.",
            "familia/index.html",
        ),
        "facturas": (
            "Счета и оплата",
            "Счета, подробности платежа и банковское поручение SEPA.",
            "facturas/index.html",
        ),
        "ajustes": (
            "Настройки",
            "Профиль, тема, язык (испанский и английский), вход по Face ID и уведомления.",
            "ajustes/index.html",
        ),
        "privacidad": ("Безопасность и приватность", build_privacidad_intro(), "privacidad/index.html"),
    }

    write_page(
        "index.html",
        "OrroFi — домашний интернет в одном приложении",
        build_index(""),
        "index.html",
    )
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
    write_page("faq/index.html", "Вопросы и ответы", build_faq(), "faq/index.html")
    write_page("contacto/index.html", "Контакты", build_contacto(), "contacto/index.html")

    site_anchors = collect_site_anchors(by_page)
    validate_published_site(site_anchors)

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
                "",
                f"missing_image_placeholders={len(MISSING_IMAGES)}",
                "missing_image_paths:",
                *MISSING_IMAGES,
            ]
        ),
        encoding="utf-8",
    )
    print(f"Generated {len(screens)} screens, {len(functions)} functions")
    print(f"Functions without committed screenshot: {len(func_no_shot)}")


if __name__ == "__main__":
    main()