# Pegasus Intelligence / Pegasus MarketQuake — Documento Maestro

Estado real al 12-jul-2026 tarde. Este documento refleja decisiones tomadas, no el plan original — leer esto antes que `session_09jun2026_pegasus_intel.md` (memoria histórica, superada en precio/niveles).

**Nota de repos — importante para no perder tiempo la próxima vez:** este archivo vive en el repo `pegasus_intelligence` (el prototipo standalone, `backend.py`/`dashboard.html`, congelado desde el 12-jul madrugada), pero casi todo lo que describe abajo sobre `/intelligence/pro` en producción vive en un repo **distinto**: `C:\Juanma\proyectos\NQH2026\CLOUD` (remoto `github.com/JuanmaTrader/pegasus-trading.git`), que corre junto al bot de trading. Ahí están `app.py`, `intelligence_engine.py`, `templates/intelligence_pro.html`. Este documento se sigue manteniendo aquí por continuidad histórica, pero para tocar código real hay que ir a ese otro repo.

## ✅ Actualización 12-jul-2026 tarde — `/intelligence/pro` ya es un producto completo, no un placeholder

La sesión del 12-jul madrugada dejó `/intelligence/pro` con Dashboard ejecutivo (tarjetas resumen + clic para expandir, exactamente el patrón "Bloomberg Terminal" que Juanma pidió) y 6 pestañas ya funcionando en producción: **Dashboard, MarketQuake, Gamma (cadena de opciones completa), Macro, Noticias (calendario + paradoja), Cascade Tracker** (impacto mecánico real tipo NVDA→Nasdaq + correlación sectorial + buscador de cualquier ticker). Nada de esto estaba reflejado en la versión anterior de este documento — quedó desactualizado apenas se construyó.

Esta tarde (12-jul) se agregó, sobre esa misma base, sin tocar lo que ya funcionaba:

- **Activos** (pestaña nueva) — destapa por fin las zonas de entrada/stop/TP1/TP2/R:R e IV Rank reales de los 6 activos (`_build_entry`, `compute_iv_rank`) que ya se calculaban en el motor desde hacía semanas pero nunca se mostraban en la página PRO — solo aparecían borrosas en la versión gratis como anzuelo. Era el hueco más grande que quedaba del diferenciador de pago.
- **Screener** (pestaña nueva) — el mismo motor de score/convergencia/entrada/IV Rank, pero para cualquier ticker de Yahoo Finance (no solo los 6 fijos). Nueva función `analyze_ticker()` en `intelligence_engine.py` + ruta `/api/intelligence/screener/<ticker>`.
- **Radar AI** (pestaña nueva) — reporte diario tipo Bloomberg (resumen ejecutivo, régimen/macro, gamma/dealers, MarketQuake, cascade, catalizadores, conclusión operativa) compuesto 100% por reglas sobre datos ya calculados en `STATE` — **sin Claude real**, tal como se había recomendado (fase 2, cuando haya suscriptores que lo justifiquen). Incluye una "convicción compuesta" transparente (0-100, con sus dos componentes — alineación de activos y estabilidad de MarketQuake — visibles, no una caja negra). Nueva función `compute_radar_ai()`.
- **Call Wall / Put Wall / Max Pain** — se agregaron al módulo Gamma existente. Requirió trackear open interest de calls y puts por separado por strike (antes se combinaban en `strike_gex`) y una función nueva `_compute_max_pain()` con la metodología estándar (el strike que minimiza el pago total a tenedores de opciones al vencimiento).

**Verificado antes de subir** (sin acceso a levantar el Flask completo por la DB): `intelligence_engine.py` no depende de Flask/DB, así que se probaron `analyze_ticker()`, `compute_gamma_exposure()` y `update_all()` completo de forma standalone contra APIs reales (Yahoo, CFTC, FRED) — todo devolvió datos reales coherentes (ej. SPY: Call Wall $760, Put Wall $540, Max Pain $745). El template se renderizó con Jinja2 en aislamiento (stubbing `current_user`/`request`) sin errores, y el bloque `<script>` se extrajo y pasó `node --check` sin errores de sintaxis.

**Descartado por hoy — Liquidez** (icebergs, DOM, order book, footprint, CVD): no existe fuente gratis y viva de datos Level 2 en ningún lado confiable. Se dejó fuera del menú en vez de simular con mockup — mostrar un módulo de "Liquidez" sin dato real detrás rompería la misma confianza que se ganó con Valuation (regla ya establecida más abajo: nunca mockups falsos). Si aparece una fuente gratis viable más adelante, se retoma.

**Pendiente de decidir con Juanma (actualizado):**
1. Imagen de portada del producto en Lemon Squeezy (ver más abajo, prompt ya entregado, sigue pendiente que Juanma la genere).
2. Configurar `RESEND_API_KEY` para correo de bienvenida automático (sigue pendiente, ver más abajo).
3. Put/Call Ratio — sigue sin fuente gratis viva; con Activos/Screener/Radar AI ya construidos, el PRO tiene bastante profundidad sin este sensor.
4. Traer Spearman/OBV/BOP sectorial desde Valuation para sumar más sensores a MarketQuake (opcional, no urgente).
5. ~~Claude real (fase 2) — en pausa por costo~~ — **revisado 12-jul noche, ver sección de abajo: se reabre, pero acotado.**

## 🔄 EN CURSO 12-jul-2026 noche — Auditoría/rediseño visual de `/intelligence/pro`, módulo por módulo

Juanma pidió repotenciar gráficamente cada módulo del menú, uno a la vez, en el orden del menú (Dashboard → Activos → MarketQuake → Gamma → Macro → Noticias → Cascade → Radar AI → Screener), con este ciclo estricto por módulo: **auditoría → discusión → acuerdo → construcción** — nunca saltar a código antes de acordar el diseño. Ver [[feedback_design]] (memoria de Claude) para el proceso de colaboración completo.

**Dashboard — primer módulo, en prototipo, NO todavía en producción.** Se construyó un prototipo (Claude Artifact, fuera del repo, con datos reales tomados en vivo de `/api/intelligence`) para validar dirección de diseño antes de tocar `intelligence_pro.html`. Decisiones de diseño confirmadas por Juanma para el Dashboard:

- **Arco narrativo de 6 capítulos, no grid de tarjetas sueltas:** 01 Contexto (Régimen/Macro) → 02 Tensión (MarketQuake) → 03 La Causa (Gamma + Cascade juntos) → 04 Lo que viene (Calendario) → 05 La Decisión (Activos) → 06 El Veredicto (Radar AI). Screener queda fuera del arco, como herramienta siempre disponible aparte.
- **Eliminar la caja uniforme** — cada capítulo compone texto narrativo + su propio micro-gráfico libremente, sin forzar todo al mismo contenedor de tarjeta.
- **Jerarquía real** — los capítulos "clímax" (Tensión, La Causa, Decisión cuando hay setup, Veredicto) llevan números grandes con gradiente dorado/glow (mismo tratamiento que ya existe en el gauge de producción); los capítulos de contexto quedan visualmente más discretos a propósito.
- **Todo elemento visual debe representar un dato real, cero decoración** — el sismógrafo mini, la regla de gamma (call/put wall/max pain/spot), la línea de tiempo de eventos, y las barras de proximidad al umbral de señal por activo, todos mapean 1:1 a campos reales que el motor ya calcula. Nada se agrega "porque se ve bien".
- **Diseñar para todo el rango de estados, no para la foto de hoy** — verificado con dos botones de alternar estado en el prototipo: uno para Gamma (SHORT↔LONG) y otro para Activos (sin setup↔con setup activo), ambos probando que el mismo diseño aguanta cualquier lectura real del mercado sin verse roto.
- **Filtro de decisión para cualquier ajuste de diseño:** ¿esto ayuda a que alguien que paga $24.99 y prueba 7 días se quede, lo entienda sin ser trader, y el trader experimentado no lo sienta básico?

**Bug real encontrado y corregido en el prototipo:** cuando dos valores de la regla de gamma quedan cerca (ej. Max Pain y Spot), sus etiquetas se encimaban e ilegibles — se corrigió con una función de layout que detecta colisión y apila en una segunda fila. Ojo con este mismo patrón al portar a producción — cualquier visualización de puntos en una recta numérica necesita esta lógica de colisión, no asumir que los valores reales vendrán siempre espaciados.

### Decisión de arquitectura — motor de texto narrativo con IA real, acotado (reabre la decisión de "Claude real: fase 2")

Problema planteado por Juanma: el texto de cada capítulo (y de cada módulo detallado) no puede ser generado con plantillas fijas de Python — por más ramas condicionales que tengan, siguen siendo una lista finita de frases, y con el tiempo un suscriptor que lo usa a diario reconoce el patrón. Eso rompe la sensación de "vivo" que se busca. Solución acordada:

**Una llamada a Claude por sección, disparada solo por evento real (no por reloj de refresh), que devuelve 3 profundidades de texto en una sola respuesta estructurada (JSON):**
- `resumen_gratuito` — para Intelligence FREE, siempre respetando el muro de pago existente (nunca revela cifras/zonas exactas, nunca revela un nivel de MarketQuake por encima de Precaución — mismo límite que ya existe hoy).
- `resumen_dashboard` — el capítulo corto del nuevo Dashboard PRO.
- `explicacion_completa` — el párrafo técnico completo de la pestaña de detalle PRO.

Una sola llamada, un solo razonamiento sobre el mismo hecho real → tres audiencias servidas a la vez, garantizando que nunca digan cosas distintas sobre el mismo hecho (vienen de la misma pasada).

**Disparadores de evento por sección** (reusa el mismo patrón de diff que ya usan `_update_signal_history()` / `_update_marketquake_history()` — comparar contra el último estado guardado, no generar en cada ciclo de `update_all()`):
1. **Contexto** — cambia el resultado de `detect_regime()`.
2. **Tensión** — cambia `mq.level` o el set de sensores disparando.
3. **La Causa** — el régimen de gamma cambia de signo, o cambia el mayor motor de `compute_cascade()`.
4. **Lo que viene** — un evento del calendario entra a la ventana inminente (cruza el umbral de días).
5. **La Decisión** — un activo cambia de `ESPERAR` a `LONG`/`SHORT` o viceversa.
6. **El Veredicto (Radar AI)** — se dispara si CUALQUIERA de las 5 anteriores cambió; sintetiza sus `resumen_dashboard` ya generados. Solo 2 salidas (sin `resumen_gratuito` — Radar AI es 100% exclusivo PRO, no existe en Intelligence FREE).

**Costo estimado:** contando generoso 20-40 eventos reales de cambio al día entre las 6 secciones combinadas, con Haiku 4.5 (~$0.003/llamada) esto queda en **~$3-6/mes** — muy lejos de los $55-60/mes que hicieron posponer "Claude real" originalmente (ese cálculo asumía llamar por cada uno de 6 activos cada 15 min sin condición de cambio real). Esto es un scope mucho más angosto: solo la capa narrativa de Intelligence, disparada por evento, no un análisis continuo.

**Límite explícito acordado — Valuation queda FUERA de este motor de texto con IA.** Valuation sigue siendo descriptivo/gratis por diseño (la separación estricta que Juanma estableció desde el principio: "todo lo que se haga en Intelligence debe superar a Valuation"). Meterle el mismo texto generado por IA a Valuation borraría esa diferencia a propósito. Lo que sí se mantiene (ya existe hoy) es el flujo de **datos** de Valuation → Intelligence vía `valuation_engine.get_data()` (así ya funciona `compute_cascade()`) — eso no cambia, solo no se comparte la capa de texto/IA.

**Estado:** el motor de texto con IA (evento → Claude → 3 salidas, techo de $8/mes) sigue **acordado pero no implementado** — sin cuenta de facturación activa en console.anthropic.com todavía (tarjeta de Juanma rechazada, pendiente resolver con el banco). El Dashboard rediseñado, en cambio, **ya está en producción y verificado en vivo** — ver la actualización siguiente.

## ✅ Actualización 12-jul-2026 noche — Dashboard de 6 capítulos YA EN PRODUCCIÓN (no solo prototipo)

Se portó el prototipo (validado como Claude Artifact) a `templates/intelligence_pro.html` real, conectado a datos en vivo de `/api/intelligence` — usando el texto de plantillas existente (`detect_regime`, `compute_marketquake`, `compute_radar_ai`, etc.), no el texto de ejemplo escrito a mano del prototipo. El motor de IA acotado (arriba) sigue siendo un reemplazo futuro de ESTE texto de plantillas, cuando esté listo.

**Lo que cambió respecto a la versión anterior del Dashboard** (la de tarjetas `.dcard` en grid, descrita en la actualización del 12-jul tarde): esa versión quedó completamente reemplazada. Ahora es un arco narrativo de 6 capítulos sin caja uniforme, con columna vertebral (spine) conectando: 01 Contexto, 02 Tensión, 03 La Causa, 04 Lo que viene, 05 La Decisión, 06 El Veredicto — más Screener aparte al final. Cada capítulo combina texto + su propio micro-gráfico real (ver detalle de diseño en memoria de Claude, [[feedback_design]]).

**Verificado en vivo contra producción real** (con Claude in Chrome, sesión ya logueada): los 6 capítulos renderizan con datos reales — incluyendo un cambio real de estado observado en la misma sesión (gamma de NQ pasó de SHORT a LONG GAMMA entre una revisión y la siguiente, y el capítulo 3 cambió de rojo a verde automáticamente, con el texto y la regla numérica actualizándose solos). El clic en "ver detalle" navega correctamente a cada pestaña (confirmado disparando el evento de clic directamente, ya que las coordenadas de clic simulado fallaban por desfases de layout, no por un bug real). La posición de scroll del Dashboard se preserva al volver desde un módulo de detalle (confirmado: scroll a 604px → entrar a Macro → resetea a 0 → volver a Dashboard → vuelve a 604px exacto).

**Bug real encontrado y corregido en producción** (no solo en el prototipo): en el capítulo 4, cuando dos eventos del calendario caían muy cerca (2 y 3 días), la segunda fila de la línea de tiempo quedaba a solo 16px de la primera — insuficiente para separar una etiqueta de dos líneas, el texto se encimaba. Corregido subiendo el espaciado de la segunda fila y el alto del contenedor.

**Además, se corrigió un choque de color que venía de antes:** "convicción BAJA" en Radar AI ya no se pinta de rojo (chocaba con la regla verde=alcista/rojo=bajista) — ahora usa `--neu`, un tono dorado apagado reservado para "sin sesgo direccional".

**Siguiente en la lista de módulos a repotenciar** (mismo ciclo auditoría→discusión→acuerdo→construcción): Activos, luego MarketQuake, Gamma, Macro, Noticias, Cascade, Radar AI, Screener — en ese orden, según lo acordado con Juanma.

## ✅ Actualización 13-jul-2026 madrugada — Módulo Activos repotenciado y EN PRODUCCIÓN

Auditoría encontró: las 6 tarjetas se veían casi idénticas en un día neutral (sin jerarquía), sin indicador de qué tan cerca está cada activo de una señal real, un caso real confuso (Petróleo +4.1% pero score NEUTRAL, sin explicación visible), el desglose de factores en texto plano poco escaneable, e IV Rank en 87-95 para 4 de 6 activos simultáneos (**pendiente que Juanma confirme si el modelo de IV Rank necesita recalibración** — no se tocó, es pregunta de datos, no de diseño).

**Construido:**
- **Orden por relevancia** — ya no es un orden fijo (Dow/Dólar/Oro/Nasdaq/Petróleo/S&P): primero los que tienen un setup activo, luego por distancia al umbral ±25.
- **Medidor de proximidad visual** en cada tarjeta (-100 a +100, umbral marcado) en vez de solo el badge de texto.
- **Frase narrativa por activo** (`_compose_asset_narrative()` en `intelligence_engine.py`) que explica casos como el de Petróleo — corregido un bug real en la primera versión: elegía el factor de mayor magnitud sin filtrar signo, lo que podía señalar a Momentum (que casi siempre acompaña el movimiento) como si "pesara en contra"; ahora filtra específicamente por signo opuesto al `chg_pct`.
- **Resumen del día** (`_compose_activos_summary()`) arriba del módulo.
- **Desglose de factores como mini-barras**, no texto plano con números separados por espacios.
- **Jerarquía real**: tarjeta con setup activo se ve más grande/con glow; en ESPERAR queda más compacta.

**Decisión de arquitectura importante — pedida explícitamente por Juanma:** todas las frases nuevas (`narrative` por activo, `activos_summary` del día) están ancladas al futuro motor de IA acotado desde el día uno — son funciones Python que devuelven un string ya guardado en `STATE`/el dict de cada activo, el frontend solo lee ese campo. Cuando el motor de IA esté listo, se reemplaza el CONTENIDO de esas funciones (plantilla → llamada a Claude), sin tocar una sola línea de `intelligence_pro.html`. Mismo patrón ya aplicado a `analyze_ticker()` (Screener) — reutiliza `_compose_asset_narrative()`.

**Verificado en producción real** con datos en vivo (vía extracción de texto de la página, no solo screenshots — hay un glitch de captura de pantalla específico de la herramienta de automatización al hacer scroll, ver nota abajo): orden correcto (DÓLAR 11 → NASDAQ 7 → DOW -5 → S&P 2 → ORO -1 → PETRÓLEO -1), narrativa de Petróleo corregida mostrando "EMA (-12)" como factor opositor real, resumen del día presente.

**Nota técnica — glitch de la herramienta de captura de pantalla:** durante la verificación se encontró que las capturas de pantalla vía Claude in Chrome se desincronizan del DOM real después de hacer scroll con el mouse (se ve un hueco negro grande con el logo flotando a mitad de pantalla). Confirmado con `elementFromPoint()` que el DOM/layout real está correcto — es un artefacto de la herramienta de automatización, no un bug del sitio. Si se repite en una sesión futura, usar `get_page_text` o `javascript_tool` para verificar contenido en vez de confiar en el screenshot tras hacer scroll.

**Siguiente en la lista:** MarketQuake.

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

Ver la lista "actualizado" cerca del inicio de este documento (sección 12-jul tarde) — reemplaza esta. Construir la UI completa de MarketQuake ya se hizo (ver sección justo arriba de esta); Activos/Screener/Radar AI también, ver el inicio del documento.
