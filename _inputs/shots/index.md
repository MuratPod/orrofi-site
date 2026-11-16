# Скриншоты аудита OrroFi (GhoFi) — 16.11.2026

Снято 16.11.2026 около 12:00 (Мадрид). Размеры веб-снимков: mobile 390x844 (@2x), desktop 1440x900. «УСТАРЕЛО» = старый бренд GhoFi (лайм), только для сравнения.

## iOS — реальное приложение (CI-артефакт прогона ios-final PR #94, run 43438430413, 13.11.2026)
Источник: артефакт `assistant-ios-results` (xcresult UI-тестов, симулятор iPhone, демо-данные), извлечено из `GhoFiUITests.xcresult`.

| Файл | Что на нём |
|---|---|
| ios-home-es-dark.png | Inicio (ES, тёмная тема): авария, скорость, счёт 39,00 €, Mi gestor, услуги |
| ios-home-es-light.png | Inicio (ES, светлая тема) |
| ios-home-en-dark.png | Home (EN, тёмная) |
| ios-login-es-dark.png | Вход по телефону/SMS (ES, тёмная) |
| ios-login-es-light.png | Вход (ES, светлая) |
| ios-mi-gestor-chat.png | Чат Mi gestor с ИИ (быстрые ответы, «Hablar con una persona») |
| ios-averia-outage.png | Экран аварии (статусы detectada → técnicos en ruta → resuelta) |
| ios-contratar-fibra.png | Contratar: выбор тарифа фибры |
| ios-pedido-resumen.png | Заказ: резюме (адрес, тариф, визит) |
| ios-pedido-privacidad-consentimiento.png | Заказ: блок защиты данных + согласия |
| ios-pedido-enviado.png | Заказ отправлен |
| ios-metodo-de-pago.png | Способ оплаты (SEPA) |
| ios-avisos.png | Уведомления (Avisos) |
| ios-perfil-dark.png / ios-perfil-light.png | Профиль: тема, язык ES/EN, Face ID, Privacidad, Mi red |
| ios-privacidad-eliminar-cuenta.png | Privacidad: «нельзя удалить аккаунт» при действующих договорах |
| ios-instalacion-cambiar-horario.png | Установка: смена времени визита |
| ios-acceso-bloqueado-otp.png | Вход заблокирован на 15 мин (OTP) |
| ios-snapshot-privacidad-iphone-se.png | Snapshot-тест Privacidad, iPhone SE (`assistant/ios/build/snapshots/privacy-es-se.png` из артефакта) |

## Прототип приложения (актуальный бренд) — https://muratpod.github.io/orrofi-proto/
| Файл | Экран (hash-маршрут) |
|---|---|
| proto-login-mobile.png | `#/login` Entrar |
| proto-home-mobile.png | `#/home` Inicio |
| proto-fibra-mobile.png | `#/fiber` Fibra |
| proto-mi-gestor-mobile.png | `#/manager` Mi gestor |
| proto-facturas-mobile.png | `#/billing` Facturas |
| proto-perfil-mobile.png | `#/profile` Perfil |
| proto-contratar-resumen-mobile.png | `#/order-sum` Contratar · resumen |
| proto-mi-red-mobile.png | `#/net-1` Mi red |
| proto-mi-red-estado-mobile.png | `#/net-4` Estado de la red |
| proto-familia-mobile.png | `#/fam-list` Familia |
| proto-mapa-desktop.png | `#/all` «Mapa del prototipo» (список всех экранов) |

## Брендбук v5 — https://muratpod.github.io/orrofi-preview/
| Файл | Что / откуда |
|---|---|
| brandbook-home-desktop.png / -mobile.png | Главная брендбука (рендер) |
| brandbook-logo-desktop.png | Раздел `#logo` |
| brandbook-icons-desktop.png | Раздел `#icons` |
| brandbook-usage-desktop.png | Раздел `#usage` |
| brandbook-orro-desktop.png / -mobile.png | `orro/index.html` — персонаж-помощник Orro |
| brandbook-file-overview-v5.png | файл `brandbook/overview-v5.png` (как есть) |
| brandbook-file-brandbook-v5-1…6.png | файлы `brandbook/brandbook-v5-1..6.png` (как есть) |
| brandbook-file-brandbook-v5-7-orro.png | файл `brandbook/brandbook-v5-7-orro.png` (как есть) |
| brandbook-usage-app-mi-red-430x932.png, brandbook-usage-hero-1600x900.png, brandbook-usage-splash-430x932.png | файлы `usage/*.png` (как есть) |
| OUTDATED-brandbook-mi-red-ghofi-mobile.png | УСТАРЕЛО: `orrofi-preview/mi-red/` (старый вид) |

## Веб-клиент (демо на Pages) — https://muratpod.github.io/orrofi-preview/cliente-web/
| Файл | Что |
|---|---|
| brandbook-cliente-web-desktop.png / -mobile.png | `cliente-web/` — лендинг «Your wifi, worth its weight in gold» (тот же, что на orrofi.es) |
| web-demo-entrar-desktop.png / -mobile.png | `entrar.html` — «Sign in to OrroFi» |
| web-demo-chat-mock-desktop.png / -mobile.png | `chat.html?mock=1` — чат Mi gestor (мок); имя OrroFi, но кнопки ещё в лаймовой палитре |
| web-demo-admin-desktop.png / -mobile.png | `admin.html` — вход в админку |

## Дизайн «Mi red», 72 кадра — ветка `design/v5-mynet-delete` (PR #58), файл `design/v5-network/index.html`
| Файл | Что |
|---|---|
| design-mi-red-72-frames-top-desktop.png | начало страницы кадров (рендер локально) |
| design-mi-red-72-frames-mid-desktop.png | ~35 % прокрутки |
| design-mi-red-72-frames-late-desktop.png | ~70 % прокрутки |

## Из main репозитория
| Файл | Что / откуда |
|---|---|
| repo-assistant-web-chat-desktop.png / -mobile.png | `assistant/app/web/chat.html` открыт статикой (без сервера; mock-api.js) |
| repo-assistant-web-admin-desktop.png | `assistant/app/web/admin.html` статикой (экран входа) |
| OUTDATED-repo-design-v5-preview-app-ghofi-mobile.png | УСТАРЕЛО: `design/v5-preview/index.html` (GhoFi, лайм) |
| OUTDATED-repo-design-v5-preview-web-ghofi-desktop.png | УСТАРЕЛО: `design/v5-preview/web/index.html` |
| accounting-proto-01-hoy.png, accounting-proto-09-movil-hoy.png | отдельный продукт «ИИ-бухгалтер»: `accounting/ghofi/prototype/screens/` (как есть) |
| accounting-web-w1-desktop-hoy.png | `accounting/ghofi/web/app/artifacts/W1/desktop-hoy-1360x860.png` (как есть) |

## Домены
| Файл | Что |
|---|---|
| site-orrofi-es-http-desktop.png / -mobile.png | http://orrofi.es — отвечает 200 (GitHub Pages, репо orrofi-site), лендинг OrroFi |
| site-orrofi-es-https-error-desktop.png | https://orrofi.es — ошибка браузера `NET::ERR_CERT_COMMON_NAME_INVALID` (сертификат `*.github.io`) |
| pages-orrofi-site-desktop.png | https://muratpod.github.io/orrofi-site/ → 301 на http://orrofi.es/ (рендер итоговой страницы) |
| site-orrofi-com-desktop.png / -mobile.png | https://orrofi.com → редирект на `/lander`, парковочная страница GoDaddy |

Примечание про «500»: с этой машины любой адрес по plain HTTP (даже http://example.com) отдаёт `500, Server: Pingora` — это сетевой прокси бокса, не сайт. При прямом подключении к IP GitHub Pages (185.199.108.153) http://orrofi.es отдаёт 200.
