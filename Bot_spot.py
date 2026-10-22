import time
import requests

TELEGRAM_TOKEN = "8721042176:AAGW4GcUn9mN17jysrT9CGlE50jPaD3jMSk"
CHAT_ID = "1828560047"

SYMBOL = "SUIUSDT"
MIN_BLOCK_SUI = 100000   # Mínimo de SUI acumulado en el bloque
RANGE_PCT = 1.0         # Rango del 1% hacia abajo
TAKE_PROFIT_PCT = 0.8   # Take Profit del 0.8%
CHECK_INTERVAL = 60     # Segundos entre cada escaneo (1 minuto)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, json=payload, timeout=8)
        if response.status_code == 200:
            print("¡Alerta de bloque enviada a Telegram con éxito!")
        else:
            print(f"Error al enviar: {response.text}")
    except Exception as e:
        print(f"Error de conexión: {e}")

print("🚀 Bot de bloques SUI (Bybit) iniciado en bucle continuo...")
send_telegram_message("🟢 *Bot de SUI activo:* Monitoreando bloques de liquidez en Bybit.")

while True:
    try:
        url = f"https://api.bybit.com/v5/market/orderbook?category=spot&symbol={SYMBOL}&limit=50"
        res = requests.get(url, timeout=5).json()
        
        if res.get("retCode") == 0:
            bids = res.get("result", {}).get("b", [])
            
            if bids:
                best_price = float(bids[0][0])
                limit_price = best_price * (1 - (RANGE_PCT / 100))
                
                total_block_qty = 0
                prices_in_block = []
                
                for item in bids:
                    price = float(item[0])
                    qty = float(item[1])
                    
                    if price >= limit_price:
                        total_block_qty += qty
                        prices_in_block.append(price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Precio: {best_price} | Bloque 1%: {total_block_qty:,.0f} SUI")
                
                if total_block_qty >= MIN_BLOCK_SUI:
                    target_sell = best_price * (1 + (TAKE_PROFIT_PCT / 100))
                    
                    mensaje = (
                        f"🧱 *¡BLOQUE DE LIQUIDEZ FUERTE EN SUI!* 🧱\n\n"
                        f"📊 *Volumen acumulado (-1%):* {total_block_qty:,.0f} SUI\n"
                        f"📍 *Zona de Precio:* {limit_price:.4f} - {best_price:.4f}\n"
                        f"📈 *Venta Objetivo (+0.8%):* {target_sell:.4f}\n"
                        f"----------------------------------------"
                    )
                    send_telegram_message(mensaje)
                    
                    # Pausa de 5 minutos si ya mandó alerta para evitar spam repetido del mismo bloque
                    time.sleep(300)
                else:
                    print("Bloque por debajo del mínimo. Esperando siguiente ciclo...")
            else:
                print("El libro de órdenes vino vacío.")
        else:
            print(f"Error en la API: {res.get('retMsg')}")

    except Exception as e:
        print(f"Error general en el ciclo: {e}")
    
    time.sleep(CHECK_INTERVAL)
