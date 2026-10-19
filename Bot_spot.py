import os
import time
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE TELEGRAM ---
# Se recomienda usar Variables de Entorno en Render para mayor seguridad
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "AAGW4GcUn9mN17jysrT9CGlE50jPaD3jMSk")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8721042176")

SYMBOLS = ["ADXUSDT", "XNOUSDT", "GNOUSDT", "BTTCUSDT"]

# Parámetros ajustados para mayor sensibilidad (Detecta movimientos desde ~1.5% - 2%)
PRICE_CHANGE_THRESHOLD = 1.5  # Porcentaje mínimo de cambio para alertar
CHECK_INTERVAL = 30           # Segundos entre cada revisión

# Diccionario para almacenar precios previos y comparar cambios
last_prices = {}

def send_telegram_message(text):
    """Envía una alerta al chat de Telegram."""
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
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def get_binance_ticker(symbol):
    """Obtiene el precio actual de Spot."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url, timeout=5).json()
        return float(res['price'])
    except Exception as e:
        print(f"Error obteniendo ticker Spot {symbol}: {e}")
        return None

def get_order_book_pressure(symbol, market_type="spot"):
    """
    Analiza el libro de órdenes (Spot o Futuros) 
    para calcular la presión de compra vs venta en los mejores 20 niveles.
    """
    if market_type == "futures":
        url = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=20"
    else:
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        
    try:
        res = requests.get(url, timeout=5).json()
        bids = sum(float(item[1]) for item in res.get('bids', [])) # Volumen de Compra
        asks = sum(float(item[1]) for item in res.get('asks', [])) # Volumen de Venta
        
        total = bids + asks
        if total == 0:
            return 0, 0, "Neutro"
        
        bid_percentage = (bids / total) * 100
        ask_percentage = (asks / total) * 100
        
        if bid_percentage > 58:
            pressure = "🟢 Alta Presión de Compra (Muro de Bids)"
        elif ask_percentage > 58:
            pressure = "🔴 Alta Presión de Venta (Muro de Asks)"
        else:
            pressure = "⚖️ Mercado Equilibrado"
            
        return bid_percentage, ask_percentage, pressure
    except Exception as e:
        print(f"Error obteniendo libro de órdenes ({market_type}) para {symbol}: {e}")
        return 50, 50, "Sin datos"

def main():
    print("Iniciando bot de criptomonedas...")
    # Mensaje inicial en Telegram al arrancar el código
    startup_text = (
        "🟢 *¡Bot de Monitoreo Reiniciado y Activo!* 24/7\n\n"
        f"🎯 *Tokens vigilados:* {', '.join([s.replace('USDT', '') for s in SYMBOLS])}\n"
        f"⚙️ *Sensibilidad:* Alertas por cambios > {PRICE_CHANGE_THRESHOLD}%\n"
        "📊 *Modo:* Analizando Spot y referencia en Futuros."
    )
    send_telegram_message(startup_text)

    # Inicializar precios base
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

            # Si el cambio supera el umbral ajustado, evaluamos y alertamos
            if abs(price_change) >= PRICE_CHANGE_THRESHOLD:
                # Analizar libro de Spot
                spot_bids, spot_asks, spot_pressure = get_order_book_pressure(symbol, "spot")
                # Analizar libro de Futuros como referencia de hacia dónde se mueve el precio
                fut_bids, fut_asks, fut_pressure = get_order_book_pressure(symbol, "futures")

                direction_emoji = "🚀" if price_change > 0 else "⚠️"
                alert_text = (
                    f"{direction_emoji * 2} *MOVIMIENTO DETECTADO EN {symbol}* {direction_emoji * 2}\n\n"
                    f"📈 *Variación:* `{price_change:+.2f}%`\n"
                    f"💲 *Precio Actual:* `{current_price}`\n\n"
                    f"📊 *Libro Spot:* Compra {spot_bids:.1f}% | Venta {spot_asks:.1f}%\n"
                    f"🔮 *Referencia Futuros:* {fut_pressure}\n"
                    f"⚙️ *Estado:* {spot_pressure}"
                )
                send_telegram_message(alert_text)
                
                # Actualizamos el precio base tras la alerta
                last_prices[symbol] = current_price
            
            time.sleep(2) # Pausa breve entre peticiones para evitar bloqueos de IP en Render

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
