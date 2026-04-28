# PEGASUS TRADING TOOLS — Market Intelligence Backend
## Guía de instalación rápida (Windows)

---

## Requisitos
- Python 3.10 o superior
- Conexión a internet
- API Key de Anthropic (para análisis narrativo completo)

---

## Instalación en 3 pasos

### Paso 1 — Copiar archivos
Copia la carpeta `pegasus_intelligence` a tu máquina, por ejemplo:
```
C:\Juanma\proyectos\pegasus_intelligence\
```

### Paso 2 — Configurar API Key
Abre `start.bat` con el Bloc de notas y descomenta esta línea:
```bat
set ANTHROPIC_API_KEY=sk-ant-tu-key-aqui
```
Reemplaza con tu API key real de Anthropic.

Opcional — NewsAPI (100 noticias/día gratis en newsapi.org):
```bat
set NEWS_API_KEY=tu-key-aqui
```

### Paso 3 — Arrancar
Doble clic en `start.bat`

El servidor arranca en: **http://localhost:5050**

---

## Endpoints disponibles

| URL | Descripción |
|-----|-------------|
| `http://localhost:5050/` | Status del servidor |
| `http://localhost:5050/api/data` | Todos los activos + macro + briefing |
| `http://localhost:5050/api/asset/gold` | Oro completo |
| `http://localhost:5050/api/asset/oil` | Petróleo |
| `http://localhost:5050/api/asset/nq` | Nasdaq |
| `http://localhost:5050/api/asset/spy` | S&P 500 |
| `http://localhost:5050/api/asset/dow` | Dow Jones |
| `http://localhost:5050/api/asset/dxy` | Dólar DXY |
| `http://localhost:5050/api/macro` | Solo macro (VIX, DXY, yields) |

---

## ¿Cuándo se actualiza la data?
- Automáticamente cada **15 minutos**
- Primera carga tarda ~60-90 segundos (procesa 6 activos + Claude)
- El servidor sigue respondiendo con la última data mientras actualiza

---

## Sin API Key de Anthropic
El sistema funciona igual con análisis de fallback:
- Precios reales ✓
- Score técnico real ✓  
- Zonas de entrada calculadas por ATR ✓
- Sin análisis narrativo en español (fallback automático)

---

## Notas de costo
- yfinance: GRATIS
- GDELT (noticias): GRATIS  
- Claude API: ~$8-12/mes con 15min refresh, 6 activos
- NewsAPI Pro: $0 primero 30 días (opcional)

---

## Próximo paso — Deploy
Una vez validado localmente, el backend se despliega en Railway.app
con un clic para que cualquier suscriptor acceda 24/7.
