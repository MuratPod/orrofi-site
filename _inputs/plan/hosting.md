# Выкладка сайта на orrofi.com

Проверено 16.11.2026 около 21:00 (Europe/Madrid). **Только чтение:** DNS, зона Cloudflare и репозиторий не менялись, записи не добавлялись и не удалялись, ничего не публиковалось.

Запросы DNS шли через DNS-over-HTTPS (Cloudflare). Ктоis/RDAP — через RDAP Verisign и GoDaddy. Зоны Cloudflare читались коннектором `user-Cloudflare` (список зон и записи зоны `orrofi.es`). Сертификаты проверены прямым TLS-подключением.

На самой машине агента обычный HTTP часто отвечает «500, Server: Pingora» — это сетевой прокси машины, а не сайт. Оценка сайтов сделана по HTTPS и по прямому запросу к адресам GitHub Pages.

---

## 1. Где сейчас orrofi.com

Домен **зарегистрирован у GoDaddy.com, LLC** (IANA 146). Регистрация: 30.10.2026, 02:53 (Europe/Madrid). Срок регистрации до 30.10.2027, 03:53 (Europe/Madrid). В RDAP владелец скрыт («Registration Private»). DNSSEC не включён. Статусы обычные для блокировки у регистратора: запрет удаления, переноса, смены и продления через сторонние каналы (clientDelete/Transfer/Renew/Update Prohibited).

**Серверы имён — у GoDaddy, не у Cloudflare:**

- `ns05.domaincontrol.com`
- `ns06.domaincontrol.com`

SOA тоже на стороне GoDaddy (`dns.jomax.net`, серийный номер зоны 2026103000).

**Записи, которые сейчас отдаёт DNS:**

| Имя | Тип | Значение | TTL |
|---|---|---|---|
| orrofi.com | A | 3.33.130.190 и 15.197.148.33 | 600 с |
| www.orrofi.com | CNAME | orrofi.com | 3600 с |
| orrofi.com | MX, TXT, AAAA, CAA | нет | — |

Адреса A — типичная парковка GoDaddy.

**Что видит посетитель.** По HTTPS и `https://www.orrofi.com` открывается парковочная страница GoDaddy («orrofi.com is parked free, courtesy of GoDaddy.com»). Корень отвечает 200 и скриптом переводит на `/lander`. Снимок: `/workspace/audit/shots/site-orrofi-com-desktop.png` и `site-orrofi-com-mobile.png`.

Сертификаты тоже GoDaddy, на сами имена домена (это не GitHub):

- `orrofi.com` — CN=orrofi.com, издатель GoDaddy TLS Intermediate CA DV, с 01.11.2026, 17:29 до 18.05.2027, 18:29 (Europe/Madrid);
- `www.orrofi.com` — отдельный сертификат, с 10.11.2026, 15:34 до 27.05.2027, 16:34 (Europe/Madrid).

Почты на orrofi.com сейчас нет (нет MX и SPF). Почта проекта живёт на **orrofi.es**.

**Управлять DNS orrofi.com сейчас можно в кабинете GoDaddy.** В коннекторе Cloudflare зоны `orrofi.com` нет (см. раздел 4). Пока Мурат не скажет «да», записи не трогаем и домен с парковки не снимаем.

---

## 2. Где лежит текущий лендинг

Публичный репозиторий [MuratPod/orrofi-site](https://github.com/MuratPod/orrofi-site), описание: «OrroFi website (orrofi.es)». GitHub Pages включены. В корне лежит файл `CNAME` с одной строкой:

```
orrofi.es
```

Кроме лендинга в этом же репозитории есть `chat.html`, `admin.html`, `mock-api.js` и папка `privacidad`. Это демо чата и админки, не визитка приложения. На боевой домен их лучше не тащить (это уже отмечал Web в аудите).

**DNS orrofi.es** идёт через Cloudflare (зона создана 31.10.2026, 20:43 Europe/Madrid; серверы имён `alec.ns.cloudflare.com` и `dahlia.ns.cloudflare.com`). Раньше стояли серверы GoDaddy (`ns61` / `ns62.domaincontrol.com`). Записи сейчас такие (прокси Cloudflare **выключен**, «серое облако», запросы идут напрямую на GitHub):

| Имя | Тип | Значение |
|---|---|---|
| orrofi.es | A | 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (адреса GitHub Pages) |
| www.orrofi.es | CNAME | muratpod.github.io |
| orrofi.es | MX | Cloudflare Email Routing (`route1/2/3.mx.cloudflare.net`) |
| orrofi.es | TXT | SPF (`include:_spf.mx.cloudflare.net`) |
| _dmarc.orrofi.es | TXT | DMARC (`p=quarantine`) |
| cf2024-1._domainkey.orrofi.es | TXT | DKIM для почты Cloudflare |

Ключи и полные почтовые записи здесь не повторяю: они и так видны в публичном DNS. Менять их при выкладке сайта не нужно.

**Как открывается orrofi.es сегодня.**

- По HTTP на адреса GitHub Pages сайт отдаёт **200**, заголовок `Server: GitHub.com`, лендинг OrroFi, в коде стоит `noindex`. Снимки: `site-orrofi-es-http-desktop.png`, `site-orrofi-es-http-mobile.png`.
- По HTTPS сервер тоже отдаёт ту же страницу, но **сертификат чужой**: CN=`*.github.io`, Let's Encrypt, имена только `github.io` / `github.com` и их поддомены. Браузер показывает `NET::ERR_CERT_COMMON_NAME_INVALID`. Снимок: `site-orrofi-es-https-error-desktop.png`.
- https://muratpod.github.io/orrofi-site/ по аудиту 16.11 перенаправлял на http://orrofi.es/ (снимок `pages-orrofi-site-desktop.png`).

Итог: лендинг на GitHub Pages **привязан к orrofi.es**, DNS для этого домена уже правильный, но GitHub **не выпустил сертификат на orrofi.es**. Поэтому «сайт наш, а замочек в браузере — чужой». Ту же ошибку легко повторить на orrofi.com, если добавить домен в Pages и не дождаться своего сертификата.

---

## 3. Что нужно, чтобы выложить визитку на orrofi.com через GitHub Pages

Ниже — план на потом. Сейчас эти шаги **не выполнять**: нет готового сайта и нет отдельного «да» Мурата на смену DNS и публикацию.

### 3.1. Репозиторий и Pages

Варианты (решение за Муратом, когда дойдём до выкладки):

- собрать визитку в уже существующем `MuratPod/orrofi-site` и сменить пользовательский домен с orrofi.es на orrofi.com;
- или завести отдельный репозиторий только под визитку, чтобы не смешивать её с демо чата.

В корне опубликованной ветки нужен файл `CNAME` со строкой:

```
orrofi.com
```

В настройках репозитория: Settings → Pages → Custom domain: `orrofi.com`, дождаться проверки DNS, затем включить **Enforce HTTPS**. Пока сертификат не выпущен, принудительный HTTPS включать рано — будет та же ошибка, что у orrofi.es.

У одного сайта GitHub Pages один пользовательский домен (плюс обычно www того же имени). Одновременно держать и orrofi.com, и orrofi.es как равные адреса Pages не получится. Когда визитка переедет на orrofi.com, для orrofi.es лучше сделать перенаправление (в Cloudflare это можно сделать отдельно, не ломая почту).

Демо `chat.html` / `admin.html` / `mock-api.js` на публичный orrofi.com не выкладывать.

### 3.2. Записи DNS для orrofi.com

GitHub Pages для корня домена не использует CNAME на сам `orrofi.com` (у корня уже стоят A). Нужны адреса Pages и www на `muratpod.github.io`:

```
A      orrofi.com      185.199.108.153
A      orrofi.com      185.199.109.153
A      orrofi.com      185.199.110.153
A      orrofi.com      185.199.111.153
AAAA   orrofi.com      2606:50c0:8000::153
AAAA   orrofi.com      2606:50c0:8001::153
AAAA   orrofi.com      2606:50c0:8002::153
AAAA   orrofi.com      2606:50c0:8003::153
CNAME  www.orrofi.com  muratpod.github.io.
```

Парковочные A `3.33.130.190` и `15.197.148.33` и нынешний CNAME `www → orrofi.com` при этом нужно убрать, иначе часть посетителей останется на заглушке GoDaddy.

После смены DNS: проверить, что `orrofi.com` и `www.orrofi.com` смотрят на Pages; в кабинете GitHub дождаться «DNS check successful»; дождаться сертификата именно на `orrofi.com` / `www.orrofi.com` (не `*.github.io`); только тогда включить Enforce HTTPS и смотреть сайт в обычном браузере без обхода ошибки.

### 3.3. HTTPS — на что обратить внимание

Урок orrofi.es: правильных A-записей мало. Сертификат появляется только когда GitHub принял пользовательский домен и сам выпустил Let's Encrypt на это имя. Если снова придёт `*.github.io`, не «лечить» это оранжевым облаком Cloudflare вслепую:

- при выключенном прокси (как сейчас у orrofi.es) посетитель говорит с GitHub напрямую и обязан получить сертификат GitHub на наше имя;
- при включённом прокси посетитель видит сертификат Cloudflare, а Cloudflare ходит на GitHub. Режим «Full (strict)» к GitHub с сертификатом `*.github.io` не сойдётся. Это обходной путь, а не исправление.

Надёжный путь: **DNS только как DNS** (без прокси) + дождаться сертификата GitHub, как в их инструкции для Pages.

### 3.4. Почта и соседний домен

Почта `hola@orrofi.es` и `privacidad@orrofi.es` завязана на зону orrofi.es. Выкладка визитки на orrofi.com эту почту не заменяет. Менять MX/SPF/DKIM/DMARC у orrofi.es для сайта не нужно. Если позже понадобится почта на @orrofi.com, это отдельное решение Мурата.

---

## 4. Где управлять DNS

Проверено чтением: `whoami` и `GET /zones` в коннекторе Cloudflare, плюс публичный DNS.

**orrofi.com — сейчас только GoDaddy.** В подключённом аккаунте Cloudflare 14 зон, среди них есть `orrofi.es`, зоны `orrofi.com` нет. Значит, записи orrofi.com из Cloudflare не посмотреть и не поменять, пока домен туда не добавят и у регистратора не сменят NS (этого сейчас не делаем).

**orrofi.es — Cloudflare**, коннектор зоны видит, записи прочитаны (раздел 2). Исходный регистратор, судя по старым NS, тоже GoDaddy; сейчас NS уже Cloudflare.

Два рабочих пути на будущее, оба только после «да» Мурата:

1. **Оставить NS у GoDaddy** и в кабинете GoDaddy DNS заменить парковку на записи из раздела 3.2. Проще всего, меньше движений.
2. **Перенести orrofi.com в Cloudflare**, как уже сделали с orrofi.es: добавить зону, прописать те же записи Pages, на стороне GoDaddy сменить NS на `alec` / `dahlia.ns.cloudflare.com`, прокси не включать. Удобнее, если позже понадобятся перенаправление с orrofi.es, правила и почта в одном месте.

Рекомендация, когда дойдём до выкладки: путь 1, если хотим сдвинуться быстрее; путь 2, если Мурат хочет держать оба домена в Cloudflare. В любом случае сначала довести до конца сертификат, и только потом объявлять адрес публично.

Никаких изменений в DNS, Pages и репозиториях в этом этапе не делалось.
