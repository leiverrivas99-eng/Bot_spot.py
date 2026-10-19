import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- SERVIDOR WEB MÍNIMO PARA ENGAÑAR A RENDER (CUMPLE CON EL PUERTO) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot activo 24/7")

    def log_message(self, format, *args):
        return  # Silenciar logs del servidor web para no saturar

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "AAGW4GcUn9mN17jysrT9CGlE50jPaD3jMSk")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8721042176")

SYMBOLS = ["ADXUSDT", "XNOUSDT", "GNOUSDT", "BTTCUSDT"]
PRICE_CHANGE_THRESHOLD = 1.5  # Sensibilidad del 1.5%
CHECK_INTERVAL = 30           # Intervalo de revisión en segundos

last_prices = {}

def send_telegram_message(text):
    if "TU_TOKEN" in TELEGRAM_TOKEN:
        print("Error: Configura tu Token y Chat ID de Telegram.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def get_binance_ticker(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url, timeout=5).json()
        return float(res['price'])
    except Exception as e:
        print(f"Error obteniendo ticker {symbol}: {e}")
        return None

def get_order_book_pressure(symbol, market_type="spot"):
    if market_type == "futures":
        url = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=20"
    else:
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        
    try:
        res = requests.get(url, timeout=5).json()
        bids = sum(float(item[1]) for item in res.get('bids', []))
        asks = sum(float(item[1]) for item in res.get('asks', []))
        
        total = bids + asks
        if total == 0:
            return 0, 0, "Neutro"
        
        bid_pct = (bids / total) * 100
        ask_pct = (asks / total) * 100
        
        if bid_pct > 58:
            pressure = "🟢 Alta Presión de Compra"
        elif ask_pct > 58:
            pressure = "🔴 Alta Presión de Venta"
        else:
            pressure = "⚖️ Mercado Equilibrado"
            
        return bid_pct, ask_pct, pressure
    except Exception as e:
        return 50, 50, "Sin datos"

def monitor_bot():
    print("Iniciando bot de criptomonedas...")
    startup_text = (
        "🟢 *¡Bot de Monitoreo Reiniciado y Activo!* 24/7\n\n"
        f"🎯 *Tokens vigilados:* {', '.join([s.replace('USDT', '') for s in SYMBOLS])}\n"
        f"⚙️ *Sensibilidad:* Alertas por cambios > {PRICE_CHANGE_THRESHOLD}%\n"
        "📊 *Modo:* Analizando Spot y referencia en Futuros."
    )
    send_telegram_message(startup_text)

    for symbol in SYMBOLS:
        price = get_binance_ticker(symbol)
        if price:
            last_prices[symbol] = price
        time.sleep(1)

    while True:
        for symbol in SYMBOLS:
            current_price = get_binance_ticker(symbol)
            if not current_price:
                continue
            
            old_price = last_prices.get(symbol, current_price)
            price_change = ((current_price - old_price) / old_price) * 100

            if abs(price_change) >= PRICE_CHANGE_THRESHOLD:
                spot_bids, spot_asks, spot_pressure = get_order_book_pressure(symbol, "spot")
                fut_bids, fut_asks, fut_pressure = get_order_book_pressure(symbol, "futures")

                direction = "🚀" if price_change > 0 else "⚠️"
                alert_text = (
                    f"{direction * 2} *MOVIMIENTO DETECTADO EN {symbol}* {direction * 2}\n\n"
                    f"📈 *Variación:* `{price_change:+.2f}%`\n"
                    f"💲 *Precio Actual:* `{current_price}`\n\n"
                    f"📊 *Libro Spot:* Compra {spot_bids:.1f}% | Venta {spot_asks:.1f}%\n"
                    f"🔮 *Referencia Futuros:* {fut_pressure}\n"
                    f"⚙️ *Estado Spot:* {spot_pressure}"
                )
                send_telegram_message(alert_text)
                last_prices[symbol] = current_price
            
            time.sleep(2)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Iniciar servidor web en hilo secundario para que Render detecte el puerto
    threading.Thread(target=start_dummy_server, daemon=True).start()
    # Ejecutar el bot principal
    monitor_bot()
