#!/usr/bin/env python3
"""Generate static Russian OrroFi marketing site (HTML) from scripts/data/screens.md."""

from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ru_copy  # noqa: E402

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

# На странице услуг iOS-кадр этих экранов показывает адрес, который нельзя публиковать.
# Берём прототип: при съёмке адрес заменяется на «Calle Ejemplo 1».
USLUGI_PROTO_FIRST = frozenset({"fiber", "order", "order-sum"})

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

META_DESCRIPTIONS: dict[str, str] = ru_copy.META
META_DEFAULT = ru_copy.META_DEFAULT

ROUTER_PASSWORD_NEUTRAL = ru_copy.ROUTER_PASSWORD_NEUTRAL

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
            ru_copy.WIFI_PASSWORD_SHOW,
        ),
        (
            "Пароль Wi‑Fi защищён при передаче и хранении",
            ru_copy.WIFI_PASSWORD_SHOW.rstrip("."),
        ),
        (
            "Гостевая сеть отделена от домашней.",
            ru_copy.GUEST_SPLIT,
        ),
        (
            "Гостевая сеть пускает в интернет и отделена от домашней.",
            ru_copy.GUEST_SPLIT,
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
            ru_copy.GUEST_SPLIT,
        ),
        (
            "Гостевая сеть изолирует гостей от ваших устройств.",
            ru_copy.GUEST_SPLIT,
        ),
        (
            "но изолирует гостей от ваших устройств",
            ru_copy.GUEST_SPLIT,
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
    "del-owner", "del-16a0", "del-16b", "del-16b2", "del-16c",
    "del-sh-bio", "del-16e", "del-16e2", "del-16f", "del-16g", "del-16h",
]
RST_IDS = [
    "rst-entry", "rst-owner", "rst-sms", "rst-17m",
    *[f"rst-17{c}" for c in "bdefghijl"], "rst-sh-bio", "rst-sh-bio-c",
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
    if sid in PRICE_EXAMPLE_SCREENS and "пример" not in caption and "условн" not in caption:
        return caption.rstrip(".") + ". Цены на кадре — пример: в демонстрации они условные."
    return caption


def pick_shot_file(
    shots_raw: str, sid: str, page_slug: str | None = None
) -> tuple[str, bool, str]:
    """Return (relative PNG src, file_exists, caption). Prefer iOS in assets/screens/ios/, then proto frames."""
    listed = [n for n in PNG_RE.findall(shots_raw) if n not in BANNED_SHOT_FILES]
    skip_ios = page_slug == "uslugi" and sid in USLUGI_PROTO_FIRST

    if not skip_ios:
        for name in listed:
            if not name.startswith("ios-"):
                continue
            path = f"assets/screens/ios/{name}"
            if resolve_image(path)[1]:
                return path, True, with_price_note(sid, ru_copy.CAPTION_DEMO)

    for name in asset_files_for(sid, page_slug):
        if name in BANNED_SHOT_FILES:
            continue
        path = f"assets/screens/{name}"
        if resolve_image(path)[1]:
            return path, True, with_price_note(sid, ru_copy.CAPTION_DEMO)

    for name in listed:
        if name.startswith("brandbook-"):
            fb = BRANDBOOK_FALLBACK.get(name)
            if fb and resolve_image(fb)[1]:
                return fb, True, with_price_note(sid, ru_copy.CAPTION_DEMO)

    legacy = f"assets/screens/{sid}.png"
    if resolve_image(legacy)[1]:
        return legacy, True, with_price_note(sid, ru_copy.CAPTION_DEMO)

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
            return path, True, with_price_note(sid, ru_copy.CAPTION_DEMO)

    intended = candidates[0] if candidates else legacy
    if intended != PLACEHOLDER_SRC:
        MISSING_IMAGES.append(f"{sid}: {intended}")
    return PLACEHOLDER_SRC, True, ru_copy.CAPTION_LATER


SCREEN_SECOND_LINE: dict[str, str] = {
    "billing": "Здесь видны счета и ближайший платёж. Цены в демонстрации условные.",
    "home": "Суммы и тарифы на экране — пример: цены в демонстрации условные.",
    "manager": "Помощник сразу говорит, что он искусственный интеллект.",
    "handoff": "Если нужен сотрудник, разговор можно передать человеку.",
    "net-0b": ROUTER_PASSWORD_NEUTRAL,
    "fam-14a": "Так вы убеждаетесь, что приглашаете именно свой дом, а не чужой.",
    "login": "Номер должен совпадать с договором.",
    "rp-18a": "Так вы сообщаете о подозрительном действии.",
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


def display_title(screen: dict) -> str:
    raw = ru_copy.TITLES.get(screen["id"], screen["title"])
    return ru_copy.typograph(sanitize_legal_copy(raw))


def screen_copy_html(screen: dict) -> str:
    parts = ru_copy.BLURBS.get(screen["id"])
    if not parts:
        raise SystemExit(f"Нет литературного текста для экрана {screen['id']}")
    paras: list[str] = []
    for part in parts[:2]:
        text = ru_copy.typograph(sanitize_legal_copy(part.strip()))
        if text and text[-1] not in ".!?…":
            text += "."
        paras.append(f"<p>{html.escape(text)}</p>")
    return f'<div class="screen-copy">{"".join(paras)}</div>'


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
<figcaption>{html.escape(ru_copy.typograph(cap))}</figcaption>
</figure>"""


def render_screen_block(screen: dict, depth: int, page_slug: str | None = None) -> str:
    src, exists, cap = pick_shot_file(screen["shots_raw"], screen["id"], page_slug)
    anchor = screen["id"]
    title = display_title(screen)
    return f"""<article class="screen-block" id="{html.escape(anchor)}">
<header>
<h3>{html.escape(title)}</h3>
</header>
{screen_copy_html(screen)}
{render_shot(src, exists, f"Экран OrroFi: {title}", cap, depth)}
</article>"""


def page_for_screen(sid: str, func: str) -> str:
    if sid.startswith("net-") or sid == "net-entry" or sid == "net-sh-bio" or sid == "net-sh-delcopy":
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
    page_title = ru_copy.typograph(page_title)
    if page_title.startswith("OrroFi —") or page_title.startswith("OrroFi\u00a0—"):
        return page_title
    return f"{page_title} · OrroFi"


def shell(title: str, body: str, depth: int, current: str) -> str:
    meta_desc = META_DESCRIPTIONS.get(current, META_DEFAULT)
    nav_links = []
    for href, label in NAV:
        nav_links.append(
            f'<li><a href="{html.escape(rel_href(href, depth))}"'
            + (' aria-current="page"' if href == current else "")
            + f">{html.escape(ru_copy.typograph(label))}</a></li>"
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
<meta name="description" content="{html.escape(ru_copy.typograph(meta_desc))}">
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
<p>OrroFi — бренд {html.escape(LEGAL_OWNER["short_name"])} (NIF {html.escape(LEGAL_OWNER["nif"])}).</p>
<p>{html.escape(FOOTER_COOKIES_LINE)}</p>
<p>
<a href="{rel_href('privacidad/index.html', depth)}">Безопасность и приватность</a>
<a href="{rel_href(f'privacidad/index.html#{SITE_PRIVACY_ANCHOR}', depth)}">Приватность этого сайта</a>
<a href="{rel_href('contacto/index.html', depth)}">Контакты</a>
<a href="mailto:{html.escape(LEGAL_OWNER['email_privacy'])}">{html.escape(LEGAL_OWNER['email_privacy'])}</a>
</p>
<p class="badge-demo">{html.escape(ru_copy.typograph(ru_copy.DEMO_BADGE))}</p>
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


def T(text: str) -> str:
    return html.escape(ru_copy.typograph(sanitize_legal_copy(text)))


def build_index(depth_content: str) -> str:
    hero_img = pick_shot_file("iOS: `ios-home-es-dark.png`", "home")
    src, exists, cap = hero_img
    shot = render_shot(src, exists, ru_copy.SHOT_ALT_HOME, cap, 0)
    lead = T(ru_copy.LEADS["index"] + " Помощник Mi gestor отвечает на вопросы, а раздел Mi red " + ru_copy.INDEX_AFTER_STRONG)
    lead = lead.replace("Mi gestor", "<strong>Mi gestor</strong>", 1).replace("Mi red", "<strong>Mi red</strong>", 1)
    cards = []
    for tag, title, text, links in ru_copy.HOME_CARDS:
        anchors = " · ".join(
            f'<a href="{html.escape(href)}">{T(label)}</a>' for href, label in links
        )
        cards.append(
            f'<div class="card"><p class="tag">{T(tag)}</p><h3>{T(title)}</h3>'
            f"<p>{T(text)}</p><p>{anchors}</p></div>"
        )
    return f"""
<section class="hero"><div class="wrap">
<p class="tag hero-tag">Приложение OrroFi</p>
<h1>{T(ru_copy.INDEX_H1)}</h1>
<p class="lead">{lead}</p>
<div class="hero-actions">
<a class="btn btn-primary" href="vozmozhnosti/">Возможности</a>
<a class="btn btn-secondary" href="instrukcii/">Как начать</a>
</div>
</div></section>
<section><div class="wrap">
<div class="gallery">{shot}</div>
</div></section>
<section><div class="wrap">
<h2>{T(ru_copy.PILLARS_TITLE)}</h2>
<div class="grid-3">
{''.join(cards)}
</div>
</div></section>
<section><div class="wrap">
<h2>{T(ru_copy.GALLERY_TITLE)}</h2>
<div class="gallery">
{_gallery_shot("`gestor-1-chat.png`", "manager", "Чат Mi gestor", 0)}
{_gallery_shot("iOS: `ios-pedido-resumen.png`", "order-sum", "Сводка заказа", 0)}
{_gallery_shot("Брендбук: `brandbook-usage-app-mi-red-430x932.png`", "net-1", "Раздел Mi red", 0)}
{_gallery_shot("iOS: `ios-perfil-dark.png`", "profile", "Профиль", 0)}
</div>
</div></section>
<section><div class="wrap status-banner">
<h2>{T(ru_copy.STATUS_TITLE)}</h2>
<p>{T(ru_copy.STATUS_BODY)}</p>
</div></section>
{depth_content}
"""


def build_vozmozhnosti(
    screens_by_page: dict, functions: dict[str, list[dict]], depth: int = 1
) -> str:
    cards = []
    for page_href, title, desc in ru_copy.FEATURE_CARDS:
        cards.append(
            f'<div class="card"><h3>{T(title)}</h3><p>{T(desc)}</p>'
            f'<p><a href="{rel_href(page_href, depth)}">{T(ru_copy.MORE)}</a></p></div>'
        )
    toc = []
    for func in sorted(functions):
        flist = functions[func]
        screen = flist[0]
        page = page_for_screen(screen["id"], func)
        if func == "Mi red: защита":
            href = rel_href(f"{page}/index.html", depth)
        else:
            href = rel_href(f"{page}/index.html#{screen['id']}", depth)
        label = ru_copy.FUNC_TITLES.get(func, func)
        toc.append(
            f'<li><a href="{html.escape(href)}">{T(polish_display_text(label))}</a></li>'
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Возможности OrroFi</h1>
<p class="lead">{T(ru_copy.LEADS["vozmozhnosti"])}</p>
</div></section>
<section><div class="wrap"><h2>{T(ru_copy.SECTIONS_TITLE)}</h2><div class="grid-3">{''.join(cards)}</div></div></section>
<section><div class="wrap"><h2>{T(ru_copy.ALPHA_TITLE)}</h2><ul class="toc">{''.join(toc)}</ul>
<p class="note">{T(ru_copy.TOC_NOTE)}</p>
</div></section>
"""


def build_topic_screens(screens: list[dict], page_slug: str) -> str:
    depth = 1
    blocks = "".join(render_screen_block(s, depth, page_slug) for s in screens)
    toc = "".join(
        f'<li><a href="#{html.escape(s["id"])}">{html.escape(display_title(s))}</a></li>'
        for s in screens
    )
    return f"""
<section><div class="wrap">
<nav aria-label="Экраны на странице"><h2>{T(ru_copy.TOPIC_TOC)}</h2><ul class="toc">{toc}</ul></nav>
</div></section>
<section><div class="wrap">{blocks}</div></section>
"""


def build_topic_page(title: str, lead: str, screens: list[dict], page_slug: str) -> str:
    return f"""
<section class="hero"><div class="wrap">
<h1>{T(title)}</h1>
<p class="lead">{T(lead)}</p>
</div></section>
{build_topic_screens(screens, page_slug)}
"""



def build_instrukcii() -> str:
    items = []
    for title, link, steps in ru_copy.INSTRUCTIONS:
        sl = "".join(f"<li>{T(s)}</li>" for s in steps)
        items.append(
            f'<li><h2 class="step-title">{T(title)}</h2><ol>{sl}</ol>'
            f'<p><a href="../{html.escape(link)}">{T(ru_copy.WATCH)}</a></p></li>'
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Инструкции</h1>
<p class="lead">{T(ru_copy.LEADS["instrukcii"])}</p>
</div></section>
<section><div class="wrap"><ol class="steps">{''.join(items)}</ol></div></section>
"""


def build_faq() -> str:
    items = []
    for q, a in ru_copy.FAQ:
        items.append(
            f"<details><summary>{T(q)}</summary>"
            f"<p>{T(a)}</p></details>"
        )
    return f"""
<section class="hero"><div class="wrap">
<h1>Вопросы и ответы</h1>
<p class="lead">{T(ru_copy.LEADS["faq"])}</p>
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
    privacy_link = (
        f'<a href="../privacidad/index.html#{SITE_PRIVACY_ANCHOR}">«Приватность на этом сайте»</a>'
    )
    return f"""
<section class="hero"><div class="wrap">
<h1>Контакты</h1>
<p class="lead">{T(ru_copy.LEADS["contacto"])}</p>
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
<p><strong>{T("По вопросам персональных данных:")}</strong> <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a></p>
<p>{T(ru_copy.CONTACT_BEFORE)} {privacy_link}.</p>
</div>
</div></section>
"""


def build_privacidad_intro() -> str:
    o = LEGAL_OWNER
    return f"""
<p class="lead">{T(ru_copy.LEADS["privacidad"])}</p>
<p>{T("По вопросам данных:")} <a href="mailto:{html.escape(o['email_privacy'])}">{html.escape(o['email_privacy'])}</a>. {T(ru_copy.PRIVACY_AEPD)}</p>
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


def visible_text(raw: str) -> str:
    raw = re.sub(r"<script[\s\S]*?</script>", " ", raw)
    raw = re.sub(r"<style[\s\S]*?</style>", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return raw


def assert_public_copy() -> None:
    joined = "\n".join((ROOT / page).read_text(encoding="utf-8") for page in PUBLISHED_PAGES)
    required = [
        SITE_PRIVACY_TEXT,
        FOOTER_COOKIES_LINE,
        ROUTER_PASSWORD_NEUTRAL,
        ru_copy.RETENTION_PHRASE,
        "OrroFi — бренд PADELADA WORLD SL.",
        "Ответственный за обработку персональных данных (responsable del tratamiento)",
        LEGAL_OWNER["address"],
        LEGAL_OWNER["email_privacy"],
        ru_copy.GUEST_FAQ,
        ru_copy.GUEST_SPLIT,
    ]
    for phrase in required:
        if phrase not in joined:
            raise SystemExit("Пропала утвержденная формулировка: " + phrase[:80])
    banned = (
        "hola@orrofi.es",
        "Сайт-визитка",
        "идентификатор",
        "появится здесь, когда будут готовы",
        "в рабочие часы",
        "9:00",
        "20:00",
        "бесплатно",
        "App Store",
        "бета",
        "аккаунт",
        "тикет",
        "пуш-",
    )
    for page in PUBLISHED_PAGES:
        raw = (ROOT / page).read_text(encoding="utf-8")
        if "hola@orrofi.es" in raw:
            raise SystemExit(f"{page}: hola@ вернулся")
        text = visible_text(raw)
        for word in banned:
            if word.lower() in text.lower():
                raise SystemExit(f"{page}: в тексте есть «{word}»")
        if re.search(r"(?<![а-яё])шифр", text.lower()):
            raise SystemExit(f"{page}: в тексте есть «шифр»")
        if "assets/screens" in text:
            raise SystemExit(f"{page}: путь к кадру попал в текст")
        for match in re.finditer(r"\d[\d\s\u00a0.,]*\s*(?:€|евро)", text, flags=re.I):
            window = text[max(0, match.start() - 120): match.end() + 120].lower()
            if "пример" not in window:
                raise SystemExit(f"{page}: цена без пометки «пример»: {match.group()!r}")


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
    # Копии настроек сети на сервере и восстановление из них в рабочем коде нет.
    omit_ids = {"net-6", "net-6b", "net-9b", "net-sh-delcopy"}
    screens = [s for s in screens if s["id"] not in omit_ids]
    screens.sort(key=lambda s: (page_for_screen(s["id"], s["function"]), s["function"], s["id"]))

    by_page: dict[str, list[dict]] = defaultdict(list)
    functions: dict[str, list[dict]] = defaultdict(list)
    for s in screens:
        page = page_for_screen(s["id"], s["function"])
        by_page[page].append(s)
        functions[s["function"]].append(s)

    page_meta = {
        "uslugi": ("Услуги и подключение", ru_copy.LEADS["uslugi"], "uslugi/index.html"),
        "mi-gestor": ("Mi gestor", ru_copy.LEADS["mi-gestor"], "mi-gestor/index.html"),
        "mi-red": ("Mi red", ru_copy.LEADS["mi-red"], "mi-red/index.html"),
        "familia": ("Семья", ru_copy.LEADS["familia"], "familia/index.html"),
        "facturas": ("Счета и оплата", ru_copy.LEADS["facturas"], "facturas/index.html"),
        "ajustes": ("Настройки", ru_copy.LEADS["ajustes"], "ajustes/index.html"),
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
                f'<section class="hero"><div class="wrap"><h1>{T(title)}</h1>'
                f"{build_privacidad_intro()}</div></section>"
                + build_site_privacy_section()
                + build_topic_screens(by_page[slug], slug)
            )
        write_page(f"{slug}/index.html", title, body, current)

    write_page("instrukcii/index.html", "Инструкции", build_instrukcii(), "instrukcii/index.html")
    write_page("faq/index.html", "Вопросы и ответы", build_faq(), "faq/index.html")
    write_page("contacto/index.html", "Контакты", build_contacto(), "contacto/index.html")

    missing = [s["id"] for s in screens if s["id"] not in ru_copy.BLURBS or s["id"] not in ru_copy.TITLES]
    if missing:
        raise SystemExit("Нет текста для экранов: " + ", ".join(missing))

    site_anchors = collect_site_anchors(by_page)
    validate_published_site(site_anchors)
    assert_public_copy()

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