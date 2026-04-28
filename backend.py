# -*- coding: utf-8 -*-
"""
PEGASUS TRADING TOOLS — Market Intelligence Backend
Versión A: Local, para validación antes de deploy

Corre con: python backend.py
Expone:    http://localhost:5050/api/data   (JSON completo)
           http://localhost:5050/api/asset/<id>  (activo individual)
           http://localhost:5050/           (status)

Actualiza data cada 15 minutos automáticamente.
"""

import os
import json
import time
import threading
import datetime
import logging
from flask import Flask, jsonify, send_from_directory, request
import yfinance as yf
import pandas as pd
import requests
import anthropic

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN — Pon tu API key de Anthropic aquí
# ─────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "TU_API_KEY_AQUI")
NEWS_API_KEY       = os.environ.get("NEWS_API_KEY", "")       # opcional, gratis en newsapi.org
SUBSCRIBER_KEY     = os.environ.get("SUBSCRIBER_KEY", "")    # si está vacío, acceso libre (modo dev)
REFRESH_MINUTES    = 15

# ─────────────────────────────────────────────────────────────
# ACTIVOS
# ─────────────────────────────────────────────────────────────
ASSETS = {
    "gold":  {"name": "ORO",       "ticker": "GC=F",      "label": "XAU/USD",   "news_query": "gold price market"},
    "oil":   {"name": "PETRÓLEO",  "ticker": "CL=F",      "label": "WTI CL=F",  "news_query": "crude oil WTI price"},
    "nq":    {"name": "NASDAQ",    "ticker": "NQ=F",       "label": "NQ=F",      "news_query": "nasdaq futures tech market"},
    "spy":   {"name": "S&P 500",   "ticker": "ES=F",       "label": "ES=F",      "news_query": "S&P 500 sp500 market"},
    "dow":   {"name": "DOW JONES", "ticker": "YM=F",       "label": "YM=F",      "news_query": "dow jones industrial"},
    "dxy":   {"name": "DÓLAR",     "ticker": "DX-Y.NYB",   "label": "DXY",       "news_query": "US dollar DXY index federal reserve"},
}

MACRO_TICKERS = {
    "VIX":   "^VIX",
    "DXY":   "DX-Y.NYB",
    "US10Y": "^TNX",
    "US02Y": "^IRX",
    "GOLD":  "GC=F",
    "OIL":   "CL=F",
}

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("PegasusIntel")

# ─────────────────────────────────────────────────────────────
# ESTADO GLOBAL — cache compartido
# ─────────────────────────────────────────────────────────────
STATE = {
    "last_update": None,
    "assets": {},
    "macro": {},
    "briefing": "",
    "status": "INICIANDO",
    "errors": []
}
STATE_LOCK = threading.Lock()

# ─────────────────────────────────────────────────────────────
# 1. PRECIOS Y TÉCNICOS — yfinance
# ─────────────────────────────────────────────────────────────
def fetch_price_data(ticker: str) -> dict:
    """Obtiene OHLCV + indicadores técnicos básicos."""
    try:
        tk = yf.Ticker(ticker)
        # 60 días para EMAs y RSI confiables
        hist = tk.history(period="60d", interval="1d", auto_adjust=True)
        if hist.empty:
            return {}

        close = hist["Close"]
        volume = hist["Volume"]
        last_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        chg_pct = ((last_price - prev_price) / prev_price) * 100

        # RSI (14)
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, 1e-9)
        rsi   = float(100 - (100 / (1 + rs.iloc[-1])))

        # EMAs
        ema50  = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])

        # ATR (14)
        high = hist["High"]; low = hist["Low"]
        tr   = pd.concat([high - low,
                          (high - close.shift()).abs(),
                          (low  - close.shift()).abs()], axis=1).max(axis=1)
        atr  = float(tr.rolling(14).mean().iloc[-1])

        # Volumen relativo
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_rel = float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else 1.0

        # Últimos 30 días de precios para sparkline
        prices_30 = [round(float(p), 2) for p in close.tail(30).tolist()]

        return {
            "price":     round(last_price, 2),
            "prev":      round(prev_price, 2),
            "chg_pct":   round(chg_pct, 2),
            "rsi":       round(rsi, 1),
            "ema50":     round(ema50, 2),
            "ema200":    round(ema200, 2),
            "atr":       round(atr, 2),
            "vol_rel":   round(vol_rel, 2),
            "prices_30": prices_30,
            "ema_signal": "ALCISTA" if ema50 > ema200 else "BAJISTA",
        }
    except Exception as e:
        log.warning(f"fetch_price_data {ticker}: {e}")
        return {}

# ─────────────────────────────────────────────────────────────
# 2. MACRO — tickers directos de yfinance
# ─────────────────────────────────────────────────────────────
def fetch_macro() -> dict:
    """Obtiene VIX, DXY, US10Y, US02Y en tiempo real."""
    result = {}
    for name, ticker in MACRO_TICKERS.items():
        try:
            tk   = yf.Ticker(ticker)
            hist = tk.history(period="5d", interval="1d")
            if hist.empty:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            chg  = round(((last - prev) / prev) * 100, 2) if prev else 0
            result[name] = {"value": round(last, 2), "chg_pct": chg}
        except Exception as e:
            log.warning(f"fetch_macro {name}: {e}")
    return result

# ─────────────────────────────────────────────────────────────
# 3. NOTICIAS — NewsAPI o GDELT (fallback gratis)
# ─────────────────────────────────────────────────────────────
def fetch_headlines(query: str, max_results: int = 3) -> list:
    """Obtiene headlines reales. NewsAPI si hay key, GDELT si no."""
    headlines = []

    # Intento 1: NewsAPI
    if NEWS_API_KEY:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query, "language": "en",
                "sortBy": "publishedAt", "pageSize": max_results,
                "apiKey": NEWS_API_KEY
            }
            r = requests.get(url, params=params, timeout=8)
            if r.status_code == 200:
                articles = r.json().get("articles", [])
                for a in articles[:max_results]:
                    headlines.append({
                        "title":  a.get("title", "")[:120],
                        "source": a.get("source", {}).get("name", ""),
                        "url":    a.get("url", "")
                    })
                return headlines
        except Exception as e:
            log.warning(f"NewsAPI error: {e}")

    # Fallback: GDELT (gratis, sin key)
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query, "mode": "artlist",
            "maxrecords": max_results, "format": "json",
            "timespan": "1d"
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            articles = r.json().get("articles", [])
            for a in articles[:max_results]:
                headlines.append({
                    "title":  a.get("title", "")[:120],
                    "source": a.get("domain", ""),
                    "url":    a.get("url", "")
                })
    except Exception as e:
        log.warning(f"GDELT error: {e}")

    return headlines

# ─────────────────────────────────────────────────────────────
# 4. SCORING ENGINE — lógica de mercado
# ─────────────────────────────────────────────────────────────
def compute_score(price_data: dict, macro: dict, asset_id: str) -> dict:
    """
    Score de -100 a +100 basado en variables técnicas y macro.
    Ponderación:
      Técnico (RSI + EMA + volumen):  40%
      Macro (correlaciones):          35%
      Momentum precio:                25%
    """
    score = 0
    details = {}

    pd_ = price_data
    if not pd_:
        return {"score": 0, "label": "SIN DATA", "details": {}}

    rsi      = pd_.get("rsi", 50)
    ema_sig  = pd_.get("ema_signal", "LATERAL")
    vol_rel  = pd_.get("vol_rel", 1.0)
    chg_pct  = pd_.get("chg_pct", 0)

    # --- TÉCNICO (40 pts máx) ---
    # RSI: sobrecompra/sobreventa
    if rsi < 30:
        rsi_s = +18   # sobreventa = potencial rebote alcista
    elif rsi < 45:
        rsi_s = +8
    elif rsi < 55:
        rsi_s = 0
    elif rsi < 70:
        rsi_s = -8
    else:
        rsi_s = -15   # sobrecompra

    ema_s = +12 if ema_sig == "ALCISTA" else -12
    vol_s = +8  if vol_rel > 1.3 else (-5 if vol_rel < 0.7 else 0)
    tecnico = rsi_s + ema_s + vol_s
    details["RSI"] = {"value": rsi, "contribution": rsi_s}
    details["EMA"] = {"value": ema_sig, "contribution": ema_s}
    details["Volumen"] = {"value": round(vol_rel, 2), "contribution": vol_s}

    # --- MACRO (35 pts máx) ---
    vix_val = macro.get("VIX", {}).get("value", 20)
    dxy_chg = macro.get("DXY", {}).get("chg_pct", 0)
    us10y   = macro.get("US10Y", {}).get("value", 4.5)
    macro_s = 0

    if asset_id == "gold":
        # Oro: beneficiado por DXY débil y VIX alto
        macro_s += -dxy_chg * 4        # DXY baja → oro sube
        macro_s += max(0, (vix_val-18)) * 1.5

    elif asset_id == "oil":
        # Petróleo: correlación moderada con riesgo
        macro_s += -dxy_chg * 2
        macro_s += -max(0, (vix_val-20)) * 1

    elif asset_id in ("nq", "spy"):
        # Equity tech: perjudicado por yields altos y VIX
        macro_s += -(us10y - 4.0) * 8
        macro_s += -(vix_val - 16) * 1.2

    elif asset_id == "dow":
        # Dow: menos sensible a yields, más a economía real
        macro_s += -(us10y - 4.0) * 4
        macro_s += -(vix_val - 16) * 0.8

    elif asset_id == "dxy":
        # DXY: yields altos lo fortalecen, expectativas de recortes lo debilitan
        macro_s += (us10y - 4.0) * 6

    macro_s = max(-35, min(35, round(macro_s)))
    details["Macro"] = {"vix": vix_val, "dxy_chg": dxy_chg, "us10y": us10y, "contribution": macro_s}

    # --- MOMENTUM PRECIO (25 pts máx) ---
    mom_s = max(-25, min(25, round(chg_pct * 4)))
    details["Momentum"] = {"chg_pct": chg_pct, "contribution": mom_s}

    total = max(-100, min(100, tecnico + macro_s + mom_s))

    # Label
    if total >= 60:   label = "ALCISTA FUERTE"
    elif total >= 25: label = "ALCISTA"
    elif total > -25: label = "NEUTRAL"
    elif total > -60: label = "BAJISTA"
    else:             label = "BAJISTA FUERTE"

    return {"score": total, "label": label, "details": details}

# ─────────────────────────────────────────────────────────────
# 5. CLAUDE API — análisis narrativo
# ─────────────────────────────────────────────────────────────
def analyze_with_claude(asset_name: str, price_data: dict,
                         macro: dict, score_data: dict,
                         headlines: list) -> dict:
    """
    Llama a Claude para generar:
    - Razón de la señal (2-3 frases en español simple)
    - Briefing del activo
    - Proyección 3 escenarios
    - Sentiment score de las noticias
    - Zonas de entrada sugeridas
    """
    if ANTHROPIC_API_KEY == "TU_API_KEY_AQUI":
        return _fallback_analysis(asset_name, price_data, score_data)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        hl_text = "\n".join([f"- {h['title']} ({h['source']})" for h in headlines]) or "Sin headlines disponibles"
        pd_     = price_data
        mac     = macro

        prompt = f"""Eres el motor de análisis de Pegasus Trading Tools — Market Intelligence.
Analiza el activo {asset_name} con los siguientes datos reales:

PRECIO Y TÉCNICOS:
- Precio actual: {pd_.get('price')}
- Cambio hoy: {pd_.get('chg_pct')}%
- RSI (14): {pd_.get('rsi')}
- EMA Señal: {pd_.get('ema_signal')}
- ATR: {pd_.get('atr')}
- Volumen relativo: {pd_.get('vol_rel')}x promedio

CONTEXTO MACRO:
- VIX: {mac.get('VIX',{}).get('value')}
- DXY: {mac.get('DXY',{}).get('value')} ({mac.get('DXY',{}).get('chg_pct')}% hoy)
- US10Y: {mac.get('US10Y',{}).get('value')}%

SCORE DEL MODELO: {score_data['score']} → {score_data['label']}

HEADLINES RECIENTES:
{hl_text}

Responde ÚNICAMENTE con este JSON (sin markdown, sin texto extra):
{{
  "reason": "2-3 frases en español simple explicando POR QUÉ el modelo da esta señal. Sin jerga técnica. Como si se lo explicaras a alguien inteligente que no es trader.",
  "sentiment_bull": 65,
  "sentiment_bear": 35,
  "headlines_scored": [
    {{"title": "titular aquí", "source": "fuente", "direction": "up"}}
  ],
  "entry": {{
    "tipo": "LONG",
    "zona": "$3,310–$3,318",
    "stop": "$3,292",
    "tp1": "$3,355",
    "tp2": "$3,398",
    "risk_pct": "1.8%"
  }},
  "projection": {{
    "optimista": {{"valor": "3,520", "factor": "descripción breve del escenario optimista"}},
    "base":      {{"valor": "3,380", "factor": "descripción breve del escenario base"}},
    "pesimista": {{"valor": "3,210", "factor": "descripción breve del escenario pesimista"}}
  }}
}}

Para direction en headlines usa: "up" si es alcista para el activo, "dn" si es bajista, "neu" si es neutral.
Para tipo en entry usa: "LONG", "SHORT", o "ESPERAR" si no hay setup claro.
Los valores de projection deben ser números razonables basados en ATR y contexto."""

        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = msg.content[0].text.strip()
        # Limpiar posibles backticks
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        log.error(f"Claude API error ({asset_name}): {e}")
        return _fallback_analysis(asset_name, price_data, score_data)

def _fallback_analysis(asset_name: str, pd_: dict, score_data: dict) -> dict:
    """Análisis de fallback cuando no hay API key o hay error."""
    score  = score_data["score"]
    label  = score_data["label"]
    chg    = pd_.get("chg_pct", 0)
    rsi    = pd_.get("rsi", 50)
    ema    = pd_.get("ema_signal", "LATERAL")
    price  = pd_.get("price", 0)
    atr    = pd_.get("atr", 0)

    reason = (f"El modelo asigna señal {label} con score {score}/100. "
              f"RSI en {rsi} y tendencia EMA {ema}. "
              f"Cambio del día: {chg:+.2f}%. Configura tu API key de Anthropic para análisis narrativo completo.")

    bull = max(10, min(90, 50 + score // 2))
    tipo = "LONG" if score > 25 else "SHORT" if score < -25 else "ESPERAR"
    sl_dist = round(atr * 1.5, 1) if atr else round(price * 0.01, 1)
    tp1_dist = round(atr * 2.5, 1) if atr else round(price * 0.015, 1)
    tp2_dist = round(atr * 4.0, 1) if atr else round(price * 0.025, 1)

    if tipo == "LONG":
        zona  = f"{price - atr:.2f}–{price:.2f}"
        stop  = f"{price - sl_dist:.2f}"
        tp1   = f"{price + tp1_dist:.2f}"
        tp2   = f"{price + tp2_dist:.2f}"
    elif tipo == "SHORT":
        zona  = f"{price:.2f}–{price + atr:.2f}"
        stop  = f"{price + sl_dist:.2f}"
        tp1   = f"{price - tp1_dist:.2f}"
        tp2   = f"{price - tp2_dist:.2f}"
    else:
        zona = stop = tp1 = tp2 = "—"

    return {
        "reason": reason,
        "sentiment_bull": bull,
        "sentiment_bear": 100 - bull,
        "headlines_scored": [],
        "entry": {"tipo": tipo, "zona": zona, "stop": stop,
                  "tp1": tp1, "tp2": tp2, "risk_pct": "1.5%"},
        "projection": {
            "optimista": {"valor": f"{price*(1+0.06):.0f}", "factor": "Escenario favorable — momentum continúa"},
            "base":      {"valor": f"{price*(1+0.02):.0f}", "factor": "Escenario base — tendencia actual"},
            "pesimista": {"valor": f"{price*(1-0.05):.0f}", "factor": "Escenario adverso — reversión"},
        }
    }

# ─────────────────────────────────────────────────────────────
# 6. BRIEFING DIARIO — Claude genera el resumen del día
# ─────────────────────────────────────────────────────────────
def generate_briefing(assets_data: dict, macro: dict) -> str:
    """Genera el briefing del día en español."""
    if ANTHROPIC_API_KEY == "TU_API_KEY_AQUI":
        vix = macro.get("VIX", {}).get("value", "—")
        dxy = macro.get("DXY", {}).get("value", "—")
        return (f"VIX en {vix} y DXY en {dxy}. "
                f"Configura tu API key de Anthropic para el briefing narrativo completo.")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        signals = {aid: f"{d.get('score_data',{}).get('label','—')} ({d.get('score_data',{}).get('score',0)})"
                   for aid, d in assets_data.items()}
        vix  = macro.get("VIX",  {}).get("value", "—")
        dxy  = macro.get("DXY",  {}).get("value", "—")
        dxy_chg = macro.get("DXY",  {}).get("chg_pct", 0)
        us10y = macro.get("US10Y",{}).get("value", "—")

        prompt = f"""Eres el analista jefe de Pegasus Trading Tools. Genera el briefing del día.

Contexto macro actual:
- VIX: {vix}
- DXY: {dxy} ({dxy_chg:+.2f}% hoy)
- US10Y: {us10y}%

Señales del modelo por activo:
{json.dumps(signals, ensure_ascii=False, indent=2)}

Escribe UN párrafo de máximo 2 frases en español. Directo, claro, sin jerga. 
Menciona qué activo lidera en cada dirección y por qué en términos simples.
No uses comillas. No uses markdown. Solo el párrafo."""

        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    except Exception as e:
        log.error(f"Briefing error: {e}")
        return "Análisis de mercado en proceso. Configura tu API key para el briefing completo."

# ─────────────────────────────────────────────────────────────
# 7. CICLO PRINCIPAL DE ACTUALIZACIÓN
# ─────────────────────────────────────────────────────────────
def update_all():
    """Refresca toda la data. Se llama cada REFRESH_MINUTES."""
    log.info("━━ Iniciando ciclo de actualización ━━")

    # Macro primero (la necesitamos para scoring)
    log.info("Obteniendo datos macro...")
    macro = fetch_macro()

    assets_data = {}

    for asset_id, asset_cfg in ASSETS.items():
        log.info(f"Procesando {asset_cfg['name']} ({asset_cfg['ticker']})...")

        # Precios
        price_data = fetch_price_data(asset_cfg["ticker"])
        if not price_data:
            log.warning(f"Sin datos de precio para {asset_id}")
            continue

        # Score
        score_data = compute_score(price_data, macro, asset_id)

        # Noticias
        headlines = fetch_headlines(asset_cfg["news_query"], max_results=3)

        # Claude análisis
        log.info(f"  → Analizando con Claude: {asset_cfg['name']}...")
        ai_analysis = analyze_with_claude(
            asset_cfg["name"], price_data, macro, score_data, headlines
        )

        # Dirección
        chg = price_data.get("chg_pct", 0)
        direction = "up" if chg > 0 else "dn"

        # Formateo de precio
        price = price_data["price"]
        if price > 1000:
            price_fmt = f"{price:,.0f}"
        elif price > 100:
            price_fmt = f"{price:,.2f}"
        else:
            price_fmt = f"{price:.4f}"

        assets_data[asset_id] = {
            "id":        asset_id,
            "name":      asset_cfg["name"],
            "ticker":    asset_cfg["label"],
            "price":     price_fmt,
            "price_raw": price,
            "chg":       f"{chg:+.2f}%",
            "dir":       direction,
            "score_data": score_data,
            "price_data": price_data,
            "ai":         ai_analysis,
            "headlines":  headlines,
        }

        time.sleep(0.5)  # Respetar rate limits

    # Briefing del día
    log.info("Generando briefing del día...")
    briefing = generate_briefing(assets_data, macro)

    # Actualizar estado global
    with STATE_LOCK:
        STATE["assets"]      = assets_data
        STATE["macro"]       = macro
        STATE["briefing"]    = briefing
        STATE["last_update"] = datetime.datetime.now().isoformat()
        STATE["status"]      = "ACTIVO"

    log.info(f"✓ Ciclo completo. {len(assets_data)} activos actualizados.")

def background_loop():
    """Loop en hilo separado."""
    while True:
        try:
            update_all()
        except Exception as e:
            log.error(f"Error en ciclo: {e}")
            with STATE_LOCK:
                STATE["status"] = "ERROR"
                STATE["errors"].append(str(e))
        time.sleep(REFRESH_MINUTES * 60)

# ─────────────────────────────────────────────────────────────
# 8. FLASK API
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

def cors_response(data):
    """JSON con headers CORS para el frontend."""
    resp = jsonify(data)
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/api/info")
def index():
    with STATE_LOCK:
        return cors_response({
            "service":     "Pegasus Trading Tools — Market Intelligence",
            "status":      STATE["status"],
            "last_update": STATE["last_update"],
            "assets":      list(STATE["assets"].keys()),
        })

@app.route("/api/data")
def api_data():
    """Devuelve todo: macro + todos los activos + briefing."""
    with STATE_LOCK:
        return cors_response({
            "status":      STATE["status"],
            "last_update": STATE["last_update"],
            "briefing":    STATE["briefing"],
            "macro":       STATE["macro"],
            "assets":      _serialize_assets(STATE["assets"]),
        })

@app.route("/api/asset/<asset_id>")
def api_asset(asset_id):
    """Devuelve data completa de un activo específico."""
    with STATE_LOCK:
        assets = STATE["assets"]
    if asset_id not in assets:
        return cors_response({"error": f"Activo '{asset_id}' no encontrado"}), 404
    return cors_response(_serialize_asset(assets[asset_id]))

@app.route("/api/macro")
def api_macro():
    with STATE_LOCK:
        return cors_response(STATE["macro"])

@app.route("/api/status")
def api_status():
    with STATE_LOCK:
        return cors_response({
            "status":      STATE["status"],
            "last_update": STATE["last_update"],
            "errors":      STATE["errors"][-5:],
        })

@app.route("/")
def landing():
    return send_from_directory(".", "index.html")

@app.route("/dashboard")
def dashboard_page():
    return send_from_directory(".", "dashboard.html")

@app.route("/logo.png")
def logo_png():
    return send_from_directory(".", "logo.png")

@app.route("/api/verify", methods=["POST"])
def verify_key():
    """Valida la clave de suscriptor enviada desde el frontend."""
    if not SUBSCRIBER_KEY:
        return cors_response({"ok": True, "dev": True})
    body = request.get_json(silent=True) or {}
    key  = body.get("key", "").strip()
    if key == SUBSCRIBER_KEY:
        return cors_response({"ok": True})
    return cors_response({"ok": False, "error": "Clave inválida"}), 401

def _serialize_asset(a: dict) -> dict:
    """Convierte el asset a formato limpio para el frontend."""
    ai  = a.get("ai", {})
    sd  = a.get("score_data", {})
    pd_ = a.get("price_data", {})
    entry = ai.get("entry", {})
    proj  = ai.get("projection", {})

    return {
        "id":      a["id"],
        "name":    a["name"],
        "ticker":  a["ticker"],
        "price":   a["price"],
        "chg":     a["chg"],
        "dir":     a["dir"],
        "signal":  sd.get("label", "—"),
        "score":   sd.get("score", 0),
        "reason":  ai.get("reason", ""),
        "sentiment": {
            "bull": ai.get("sentiment_bull", 50),
            "bear": ai.get("sentiment_bear", 50),
        },
        "headlines": ai.get("headlines_scored", []),
        "vars": [
            {"n": "RSI (14)",    "v": str(pd_.get("rsi", "—")),          "c": _rsi_color(pd_.get("rsi",50))},
            {"n": "EMA 50/200",  "v": pd_.get("ema_signal","—"),         "c": "up" if pd_.get("ema_signal")=="ALCISTA" else "dn"},
            {"n": "Volumen Rel.", "v": f"{pd_.get('vol_rel',1):.1f}x",   "c": "up" if pd_.get("vol_rel",1)>1.2 else "neu"},
            {"n": "ATR",         "v": str(pd_.get("atr","—")),           "c": "neu"},
            {"n": "Sentimiento", "v": f"{ai.get('sentiment_bull',50)}% Bull", "c": "up" if ai.get("sentiment_bull",50)>50 else "dn"},
            {"n": "Score Modelo","v": f"{sd.get('score',0):+d} / 100",   "c": _score_color(sd.get("score",0))},
        ],
        "entry": {
            "tipo": entry.get("tipo", "ESPERAR"),
            "zona": entry.get("zona", "—"),
            "stop": entry.get("stop", "—"),
            "tp1":  entry.get("tp1", "—"),
            "tp2":  entry.get("tp2", "—"),
            "risk": entry.get("risk_pct", "—"),
        },
        "projection": {
            "opt":  proj.get("optimista", {}),
            "base": proj.get("base", {}),
            "pes":  proj.get("pesimista", {}),
        },
        "prices_30": pd_.get("prices_30", []),
    }

def _serialize_assets(assets: dict) -> dict:
    return {aid: _serialize_asset(a) for aid, a in assets.items()}

def _rsi_color(rsi):
    if rsi < 35: return "up"
    if rsi > 65: return "dn"
    return "neu"

def _score_color(score):
    if score > 25:  return "up"
    if score < -25: return "dn"
    return "neu"

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("═" * 55)
    log.info("  PEGASUS TRADING TOOLS — Market Intelligence")
    log.info("  Backend v1.0 — Local Mode")
    log.info("═" * 55)

    if ANTHROPIC_API_KEY == "TU_API_KEY_AQUI":
        log.warning("⚠ Sin API key de Anthropic — usando análisis de fallback")
        log.warning("  Configura: set ANTHROPIC_API_KEY=sk-ant-...")

    # Primera actualización en hilo separado para no bloquear el servidor
    log.info("Iniciando primera carga de datos...")
    t = threading.Thread(target=update_all, daemon=True)
    t.start()

    # Hilo de refresh continuo (arranca después de la primera carga)
    def delayed_loop():
        t.join()
        background_loop()

    threading.Thread(target=delayed_loop, daemon=True).start()

    PORT = int(os.environ.get("PORT", 5050))
    log.info(f"Servidor iniciando en http://localhost:{PORT}")
    log.info("Endpoints:")
    log.info(f"  Dashboard: http://localhost:{PORT}/dashboard")
    log.info("  GET /api/data   → todo")
    log.info("  GET /api/asset/gold  → oro")
    log.info("  GET /api/asset/nq    → nasdaq")
    log.info("  GET /api/macro  → macro")
    log.info("─" * 55)

    app.run(host="0.0.0.0", port=PORT, debug=False)
