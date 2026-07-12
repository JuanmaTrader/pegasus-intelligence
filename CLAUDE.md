# Pegasus Intelligence / Pegasus MarketQuake — Documento Maestro

Estado real al 11-jul-2026 noche. Este documento refleja decisiones tomadas, no el plan original — leer esto antes que `session_09jun2026_pegasus_intel.md` (memoria histórica, superada en precio/niveles).

## Qué es

Segundo producto de pago de Pegasus Trading Tools (junto a [Pegasus Valuation](../pegasus_valuation/CLAUDE.md), que es gratis). Análisis de mercado accionable: régimen, señales por activo, zonas de entrada/salida, y un sistema de alerta temprana ("MarketQuake") basado en confirmación cruzada de sensores institucionales.

**Regla de separación estricta:** Valuation es descriptivo/histórico (gratis). Intelligence es accionable/vigilado en vivo (pago). El mandato de Juanma: "todo lo que se haga en Intelligence debe superar a Valuation en todos los aspectos" — Valuation gratis quedó tan bien que el pago tiene que sentirse claramente superior.

## Las 4 piezas que existían dispersas (auditoría 11-jul)

Nadie las había visto juntas hasta esta noche. Ninguna estaba "mal", solo desconectadas entre sí:

| Pieza | Dónde vive | Estado |
|---|---|---|
| **A · En producción** | `NQH2026/CLOUD/templates/intelligence.html` + `intelligence_engine.py` | Régimen (6 tipos) + macro + briefing automático + 6 activos con señal/score/convergencia + historial. Todo gratis hoy, sin muro real. Tiene una sección "PRO bloqueada" con 4 tarjetas 100% inventadas (Cascade Tracker, Paradox Detector, IV Rank, Screener). |
| **B · Calculado, nunca mostrado** | `intelligence_engine.py` | `compute_iv_rank()` e `_build_entry()` (LONG/SHORT, zona de entrada, stop, TP1, TP2, R:R reales) ya existen y funcionan — el frontend nunca los referencia. Quick win #1: destapar, no construir. |
| **C · Backend standalone con IA real** | `pegasus_intelligence/backend.py` + `dashboard.html` | Nunca conectado a la web real. 5 pestañas (Mercado/Activos/**Swing 3-10d**/Macro/Alertas), 4 horizontes (Intraday/Scalper/Swing/Posición), Claude real por activo (razón en español, sentiment, 3 escenarios), calendario CPI/NFP/FOMC/PPI/EIA con "paradoja" ya redactada a costo $0. Modelo en código (`claude-opus-4-6`) no existe — hay que cambiarlo antes de usar esto. |
| **D · MarketQuake (el sismógrafo)** | `pegasus_intelligence/pegasus_earthquake_early_warning.html` | Mockup puro, sin dato real detrás — botones que "simulan" niveles. 9 sensores de confirmación cruzada (mín. 3 simultáneos para alertar), 4 niveles (Normal/Precaución/Alerta/Crítico). |

**Hallazgo clave:** el pricing de 4 niveles ya se había diseñado el 9-jun-2026 y calzaba casi perfecto con el código — lo que pasó es que, como nunca se construyó el sistema de pago/acceso, **todo salió gratis**. No faltaba estrategia, faltaba infraestructura de auth.

## Nombre — CERRADO

**"Pegasus MarketQuake — Institutional Early Warning System."**

## Precio — CERRADO: FREE + PRO único a $24.99/mes

Se descartaron los 4 niveles del diseño original (FREE/$19.99/$49.99/$99.99) — decisión de Juanma tras análisis de psicología de precios en conjunto:

- **Por qué no 4 niveles:** vender 4 versiones casi idénticas de un producto sin un solo suscriptor todavía genera parálisis de elección. Mejor lanzar simple y segmentar después con datos reales de uso.
- **Por qué no $9.99:** en herramientas financieras el precio es señal de calidad — muy barato genera desconfianza ("¿esto da ventaja institucional de verdad?").
- **Por qué $24.99 y no $19.99/$29.99:** cae en el casillero psicológico de "herramienta seria" sin necesitar mostrar historial/reseñas para justificarlo. Anclado contra lo que un trader ya gasta en datos CME en tiempo real ($50-100+/mes) — $24.99 se siente trivial en comparación.

Todo lo que era "ELITE" en el diseño original (Cascade Tracker, Screener, API) queda como futuro add-on, no como tier a vender ahora.

## Línea gratis/pago

**Gratis:** régimen + macro strip + 6 activos con dirección/score/convergencia (no precio exacto) + briefing + historial de señales + calendario económico con "paradoja" (nuevo, costo $0) + MarketQuake solo niveles Normal y Precaución.

**Pago ($24.99/mes):** zonas de entrada/stop/TP exactas (quick win, ya calculado) + IV Rank real (quick win) + vista Swing 3-10d + MarketQuake completo (Alerta+Crítico) + Screener + Cascade Tracker/Paradox Detector (si se construyen de verdad — nunca mostrar mockups falsos, rompería la confianza que ganó Valuation) + Claude real (fase 2 probablemente, ver costo abajo).

## Cómo se accede — separado del dashboard del bot

Instrucción explícita de Juanma: el mismo botón "Acceder", pero un suscriptor de Intelligence PRO **no debe caer en el dashboard de trading** — debe caer en las herramientas de Intelligence. Hoy `/acceso` es el mismo login para inversor/socio/admin del bot, y el sistema de usuarios no distingue "suscriptor de Intelligence" como rol aparte.

**Esta es la pieza de infraestructura que realmente falta** (no diseño, no dato) — sin esto no hay forma de cobrar nada. Propuesta técnica mínima: agregar un campo de suscripción a Intelligence (separado del rol inversor/socio/admin existente), y que el login redirija según corresponda — a `/bot_dashboard` si es inversor/socio, a una nueva `/intelligence/pro` si es suscriptor de Intelligence.

## Costo de Claude (IA real) — analizado con números reales

Ambas cosas son ciertas a la vez: **por llamada cuesta centavos** (~$0.003 con Haiku 4.5), pero `backend.py` standalone llama a Claude por cada uno de los 6 activos **cada 15 minutos, 24/7** = ~20,000 llamadas/mes. Centavos × volumen = costo real.

| Modelo | Costo aprox./mes (24/7) |
|---|---|
| Haiku 4.5 (recomendado) | ~$55-60/mes |
| Sonnet 5 | ~$110-115/mes |
| Opus 4.8 | ~$280/mes (no recomendado) |

Con Haiku 4.5 + solo horario de mercado (no 24/7): **~$25-30/mes** — se paga solo con 2-3 suscriptores. Modelo actual en código (`claude-opus-4-6`) no existe, hay que cambiarlo.

**Decisión pendiente:** ¿Claude real entra en el lanzamiento inicial o se deja para fase 2 (después de tener los primeros suscriptores que justifiquen el costo)? Recomendación: fase 2.

## Fuentes de datos para MarketQuake — estado real (11-jul noche)

Los 9 sensores originales del prototipo, verificados uno por uno contra fuentes reales:

| Sensor | Estado | Fuente |
|---|---|---|
| Spearman SPY / OBV divergencia / BOP breadth | ✅ ya en Valuation | mismo motor |
| VIX spike / Volumen anómalo | ✅ ya en Intelligence | `intelligence_engine.py` |
| **COT (Commitment of Traders)** | ✅ conectado 11-jul | CFTC Socrata API, sin API key. `fetch_cot_positioning()` |
| **HY Credit Spread** | ✅ conectado 11-jul | FRED (Fed St. Louis), CSV público sin API key. `fetch_hy_credit_spread()` |
| **Dealer positioning** (bonus, no estaba en los 9 originales) | ✅ conectado 11-jul | CFTC TFF + Disaggregated. `fetch_dealer_positioning()` |
| **Gamma Exposure / GEX** (bonus, no estaba en los 9 originales) | ✅ construido 11-jul | Cálculo propio (Black-Scholes) sobre opciones reales de Yahoo Finance. `compute_gamma_exposure()` |
| Put/Call Ratio | ❌ pendiente | Único candidato gratis conocido (CSV de CBOE) murió en 2019, no actualiza |
| COT shift semanal | ✅ (es lo mismo que COT arriba) | — |

**Detalles técnicos importantes de lo conectado:**

- **`fetch_cot_positioning()`** — nombres de contrato CFTC cambiaron desde feb-2022, varios quedaron "muertos" bajo el nombre viejo. Verificado `max(report_date)` de cada uno antes de asumir vigencia:
  - Dow: `"DOW JONES INDUSTRIAL AVG- x $5 - CHICAGO BOARD OF TRADE"` (muerto 2022) → ahora `"DJIA x $5 - CHICAGO BOARD OF TRADE"`
  - Oil/WTI: `"CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"` (muerto 2022) → ahora `"WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE"`
  - NQ: ahora `"NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE"`
- **`fetch_dealer_positioning()`** — NQ/SPY/DOW/DXY vía reporte **TFF** (resource `gpe5-46if`, categoría `dealer_positions_long_all`/`dealer_positions_short_all`, solo cubre futuros financieros). GOLD/OIL vía reporte **Disaggregated** (resource `72hh-3qpy`, categoría `swap_positions_long_all`/`swap__positions_short_all` — ojo con el doble guion bajo en "short", es un typo real de CFTC en el nombre del campo — TFF no cubre materias primas físicas).
- **`compute_gamma_exposure()`** — NQ=F/ES=F son futuros y no tienen cadena de opciones en yfinance. Se usa **QQQ** como proxy de `nq` y **SPY** como proxy de `spy`. Metodología: Black-Scholes gamma por strike × open interest real (misma que usan trackers pagados como SpotGamma, que también son estimaciones con supuestos). Verificado contra prototipo standalone: SPY ~+$3.5-4.2B (LONG GAMMA), QQQ ligeramente negativo (SHORT GAMMA) — rangos razonables. Costo: ~14s extra por ciclo de `update_all()`.
- **Prime brokerage data** — investigado y descartado. No existe como producto de datos independiente en ningún lado, gratis o pago razonable — es exclusivo de ser cliente de la mesa de prime brokerage de un banco (Goldman, Morgan Stanley). No perseguir más.

Todos los sensores nuevos tienen caché propio (6-12h según frecuencia real de la fuente) para no golpear las APIs gratis de más, y están wireados a `update_all()`/`STATE` en `intelligence_engine.py` de producción — **pero todavía sin consumidor en el frontend**. La data ya existe, falta la UI de MarketQuake.

## Orden de construcción sugerido

1. ~~Quick wins gratis sin costo~~ (calendario+paradoja, sensores de datos) — **EN CURSO, 4/6 fuentes de datos ya conectadas**
2. **Sistema de acceso PRO separado del dashboard del bot** — la pieza de infraestructura que realmente falta, sin esto nada se puede cobrar
3. Destapar entry zones + IV Rank reales detrás del muro (ya calculados, solo conectar)
4. UI completa de MarketQuake (Alerta + Crítico) con los sensores ya conectados
5. Swing 3-10d + Screener (trasplantar del dashboard standalone)
6. Claude real — si se decide meterlo, o se deja para cuando haya suscriptores pagando

## ✅ Sistema de acceso PRO — CONSTRUIDO Y VERIFICADO EN PRODUCCIÓN (11-jul noche)

Juanma decidió: cobro automatizado real desde el día uno vía **Lemon Squeezy** (cuenta ya existente de Pegasus Trading Tools, usada antes para los indicadores de TradingView), no manual — "un sistema impresionante... cobrar $10 se siente barato" aplicado también a la operación, no solo al precio.

**Lemon Squeezy (creado 11-jul):**
- Producto "Pegasus Intelligence PRO" — $24.99/mes, 7 días de prueba gratis.
- Webhook configurado: `https://www.pegasustradingtools.com/webhook/lemonsqueezy`, eventos: `subscription_created/updated/cancelled/resumed/expired/paused/unpaused/payment_failed/payment_success`. Secreto guardado como env var `LEMONSQUEEZY_WEBHOOK_SECRET` en Render.

**Flujo construido (100% automático, sin pasos manuales):**
1. Cliente paga en Lemon Squeezy → webhook llega a `/webhook/lemonsqueezy` (firma HMAC-SHA256 verificada contra el secreto).
2. Si el email no existe como usuario: crea cuenta (`role="intelligence_pro"`, `email`, password aleatoria que nadie usa), genera token de un solo uso (`password_reset_token`, expira 7 días).
3. Envía correo de bienvenida con link para fijar contraseña — vía **Resend** (`RESEND_API_KEY`, aún no configurada). **Mientras tanto: si la API key no está, el link queda logueado en Render (`⚠️ RESEND_API_KEY no configurada — link de acceso para {email}: {url}`) — no falla en silencio, Juanma puede mandarlo a mano como respaldo.**
4. Cliente entra a `/intelligence/set-password/<token>`, fija contraseña, queda logueado automáticamente.
5. `/login` (el mismo de siempre) ahora redirige por rol: admin→`/bot`, socio→dashboard socio, **intelligence_pro→`/intelligence/pro`** (nunca al dashboard del bot — exactamente lo pedido), el resto→inversor.
6. `/intelligence/pro` — placeholder real (no vacío), muestra régimen/briefing en vivo vía `/api/intelligence` + nota "muy pronto" para MarketQuake/zonas de entrada.

**Cambios técnicos:** `models.py` — User ganó `email`, `intelligence_pro_active`, `intelligence_pro_expires`, `ls_subscription_id`, `password_reset_token`, `password_reset_expires` (migración seguraALTER TABLE ADD COLUMN IF NOT EXISTS, mismo patrón que `scheduled_at`). Nuevas rutas y templates en `app.py`/`templates/intelligence_pro.html`/`templates/intelligence_set_password.html`.

**Verificado end-to-end contra producción real** (no solo local): webhook firmado → cuenta creada → link de set-password → contraseña fijada → login → redirige a `/intelligence/pro` sin tocar el dashboard del bot. Admin/socio/inversor confirmados sin regresión. Queda una cuenta de prueba en la DB (`prueba.produccion.11jul@example.com`) — inofensiva, pendiente que Juanma la desactive desde el panel cuando quiera (no tengo cómo borrarla yo, no tengo su password de admin ni acceso psql directo).

**Pendiente inmediato:** configurar `RESEND_API_KEY` (cuenta gratis en resend.com, la debe crear Juanma) para que el correo de bienvenida salga automático — hoy funciona igual mediante el respaldo en logs, solo que requiere que Juanma revise el log y lo mande a mano.

## Imagen de portada del producto en Lemon Squeezy — pendiente

Juanma la va a generar él mismo en ChatGPT/DALL-E (no la construimos vía HTML+captura como se intentó primero). Prompt exacto entregado 11-jul, guardado para referencia:

> Create a premium product cover image, 1600×1200 pixels (4:3 ratio), for a financial market-intelligence subscription product called "Pegasus Intelligence PRO." Style: dark, institutional, high-end fintech terminal aesthetic — think Bloomberg Terminal meets luxury branding, NOT generic stock-photo trading imagery. Background near-black (#080600) with a subtle warm gold radial glow top-left. Typography: bold monospace/geometric font, "PEGASUS" in gold gradient (#D4AF37→#F0D060) wide letter-spacing, "INTELLIGENCE" below in cream/gold even wider spacing. A small solid gold "PRO" badge below the wordmark. Centerpiece: a thin gold seismograph/waveform line horizontally across the middle — flat/calm on both sides, one dramatic sharp spike in the center (soft glow), representing the flagship early-warning feature. Thin gold corner brackets near the four corners (camera-viewfinder style). Tagline above wordmark: "Institutional Early Warning System." Near bottom: price tag "$24.99" bold gold + "/ MES" smaller muted. Mood: serious, expensive, exclusive — tool for professional traders, not a consumer app.

Pendiente: que Juanma la genere y la suba al producto en Lemon Squeezy (Store → Products → Pegasus Intelligence PRO → Media).

## ✅ UI de Pegasus MarketQuake — CONSTRUIDA Y VERIFICADA EN PRODUCCIÓN (12-jul madrugada)

Juanma señaló el prototipo original (`pegasus_intelligence/pegasus_earthquake_early_warning.html`, hecho por Claude en otra sesión) como punto de partida, con libertad total de usarlo, modificarlo, o descartarlo. Decisión: **se conservó el lenguaje visual** (sismógrafo animado, medidores tipo Richter, 4 pestañas, historial) pero **se reconstruyó toda la lógica desde cero con datos reales** — el prototipo tenía 4 niveles con texto y números escritos a mano en JavaScript (fake), y sus 9 sensores apuntaban a rotación sectorial (XLF→XLK) que vive en Valuation, no en Intelligence.

**5 sensores reales usados** (`compute_marketquake()` en `intelligence_engine.py`): VIX spike, volumen anómalo por activo, COT/dealer shift (cambio de signo semana a semana), HY Credit Spread, Gamma Exposure (short gamma en SPY/QQQ — bonus que el prototipo original ni tenía). Nivel 0-3 según cuántos disparan simultáneamente (2=Precaución, 3=Alerta, 4+=Crítico). Spearman/OBV/BOP sectorial y Put/Call quedaron fuera — el primero exige traer código de Valuation (no vale la pena ahora), el segundo sigue sin fuente gratis viva.

`/intelligence/pro` ahora tiene la UI completa: sismógrafo con color/amplitud según el nivel real, 3 medidores (Magnitud, Confirmaciones, "Sensores Reales 5/5 — sin datos simulados"), y 4 pestañas (Alerta con narrativa+confirmaciones, Sensores con detalle de cada uno, Escala con la leyenda, Historial acumulando cambios de nivel reales vía `marketquake_history`). Sin botones de "simular nivel" — eso era solo para la demo del prototipo.

**Verificado en producción real** (no solo local): logueado con la cuenta de prueba, `/intelligence/pro` mostró nivel ALERTA real (3/5 sensores: volumen anómalo en Oro 16.7x, dealer shift en Petróleo, NQ en short gamma) — coincide exacto con lo que devuelve `/api/intelligence`. Las 4 pestañas confirmadas funcionando.

## Pendiente de decidir con Juanma

1. **¿Claude real en el lanzamiento inicial o fase 2?** — recomendación: fase 2.
2. Put/Call Ratio — buscar fuente alternativa viva, o lanzar MarketQuake sin este sensor (5/5 reales ya es sólido).
3. Traer Spearman/OBV/BOP sectorial desde Valuation para sumar más sensores (opcional, no urgente).
3. Configurar Resend para correo automático (ver arriba).
4. Construir la UI completa de MarketQuake — la data ya está conectada, falta la interfaz visual dentro de `/intelligence/pro`.
5. Imagen de portada del producto en Lemon Squeezy (ver arriba, prompt ya entregado).
