import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- SERVIDOR WEB MÍNIMO PARA EL PLAN GRATUITO DE RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot SUI Activo 24/7")

    def log_message(self, format, *args):
        return  # Silencia los logs HTTP

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- CONFIGURACIÓN DEL BOT ---
# Asegúrate de colocar tus credenciales de Telegram si no usas variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "AAGW4GcUn9m17jysrT9CG1E50jPaD3jMSK")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8721042176")

SYMBOL = "SUIUSDT"
MIN_WALL_SUI = 170000   # Muro mínimo de 170k tokens SUI
TAKE_PROFIT_PCT = 0.8   # Objetivo del 0.8%
CHECK_INTERVAL = 10     # Revisa cada 10 segundos

last_alert_time = 0     # Cooldown entre alertas (3 minutos mínimo)

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or "TU_TOKEN" in TELEGRAM_TOKEN:
        print("Error: Credenciales de Telegram no configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=8)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def get_order_books():
    """Obtiene libro de Spot y libro de Perpetuos para SUIUSDT."""
    spot_url = f"https://api.binance.com/api/v3/depth?symbol={SYMBOL}&limit=50"
    fut_url = f"https://fapi.binance.com/fapi/v1/depth?symbol={SYMBOL}&limit=50"
    
    try:
        spot_res = requests.get(spot_url, timeout=5).json()
        fut_res = requests.get(fut_url, timeout=5).json()
        return spot_res, fut_res
    except Exception as e:
        print(f"Error consultando APIs de Binance: {e}")
        return None, None

def monitor_sui():
    global last_alert_time
    print("Iniciando monitoreo especializado en SUI...")
    
    startup_text = (
        "🟢 *BOT SUI 100% ACTIVO*\n\n"
        "🎯 *Token:* SUI / USDT\n"
        f"📊 *Filtro de Muro:* >= 170,000 SUI (en Bids/Compras Spot)\n"
        f"🎯 *Take Profit Objetivo:* +{TAKE_PROFIT_PCT}%\n"
        "🛡️ *Filtro Futuros:* Revisa que no haya presión bajista masiva en Perpetuos."
    )
    send_telegram_message(startup_text)

    while True:
        spot_book, fut_book = get_order_books()
        
        if spot_book and fut_book and "bids" in spot_book and "asks" in fut_book:
            # 1. Analizar Muros de Compra en Spot (en cantidad de SUI, no $)
            spot_bids = spot_book.get("bids", [])
            max_bid_volume = 0
            best_bid_price = float(spot_bids[0][0]) if spot_bids else 0

            # Sumamos o buscamos bloques de compra mayores a 170k SUI cerca del precio actual
            for price, qty in spot_bids[:15]:  # Top 15 niveles de profundidad
                volume_sui = float(qty)
                if volume_sui > max_bid_volume:
                    max_bid_volume = volume_sui

            # 2. Analizar Presión de Venta en Futuros (Asks / Muros Bajistas)
            fut_asks = fut_book.get("asks", [])
            fut_sell_volume = sum(float(qty) for price, qty in fut_asks[:15])
            fut_buy_volume = sum(float(qty) for price, qty in fut_book.get("bids", [])[:15])

            # Condición: Presión vendedora en futuros no debe dominar exageradamente
            no_bearish_pressure = fut_buy_volume >= (fut_sell_volume * 0.45)

            # 3. Disparo de Alerta si hay muro de >= 170k SUI y no hay pared bajista en futuros
            current_time = time.time()
            if max_bid_volume >= MIN_WALL_SUI and no_bearish_pressure:
                # Evitar spam de alertas (mínimo 3 minutos entre notificaciones)
                if current_time - last_alert_time > 180:
                    tp_price = best_bid_price * (1 + (TAKE_PROFIT_PCT / 100))
                    
                    alert_msg = (
                        f"🚨 *MURO DETECTADO EN SUI (SPOT)* 🚨\n\n"
                        f"💰 *Muro Comprador:* `{max_bid_volume:,.0f} SUI`\n"
                        f"💲 *Precio Actual/Entrada:* `{best_bid_price:.4f} USDT`\n"
                        f"🎯 *Take Profit (+{TAKE_PROFIT_PCT}%):* `{tp_price:.4f} USDT`\n\n"
                        f"🔮 *Estado Perpetuos:* Sin bloqueos bajistas dominantes.\n"
                        f"⚡ *Acción:* Evaluación de Compra Rápida."
                    )
                    send_telegram_message(alert_msg)
                    last_alert_time = current_time

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Servidor invisible para Render (Puerto Web)
    threading.Thread(target=start_dummy_server, daemon=True).start()
    # Iniciar escáner de SUI
    monitor_sui()
