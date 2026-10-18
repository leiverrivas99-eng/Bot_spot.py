import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- SERVIDOR PARA MANTENER RENDER ACTIVO 24/7 ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Spot Baja Capitalizacion Activo 24/7")

def run_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print("🌐 Servidor interno iniciado en puerto 10000...")
    httpd.serve_forever()

Thread(target=run_server, daemon=True).start()

# --- CONFIGURACIÓN DE TELEGRAM ---
TOKEN = "8721042176:AAGW4GcUn9mN17jysrT9CGlE50jPaD3jMSk"
CHAT_ID = "1828560047"

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")
        return False

# --- TOKENS DE BAJA CAPITALIZACIÓN (SOLO SPOT) ---
SIMBOLOS_SPOT = [
    "ADXUSDT", 
    "XNOUSDT", 
    "GNOUSDT", 
    "BTTCUSDT"
]

alertas_enviadas = {}

print("🚀 Bot Spot Baja Capitalización iniciando...")

# --- MENSAJE DE CONFIRMACIÓN DE ACTIVACIÓN ---
mensaje_prueba = (
    "🟢 *BOT SPOT DE BAJA CAPITALIZACIÓN ACTIVADO*\n\n"
    "🎯 *Tokens vigilados:* `ADX, XNO, GNO, BTTC`\n"
    "⚙️ *Estrategia:* Análisis dinámico de volumen en Spot, detección de muros orgánicos y cálculo de Imbalance (Presión de Compra/Venta)."
)
enviar_telegram(mensaje_prueba)

# --- BUCLE PRINCIPAL DE MONITOREO ---
while True:
    try:
        for simbolo in SIMBOLOS_SPOT:
            # Consultar libro de órdenes en Spot (profundidad de 20 niveles)
            url = f"https://api.binance.com/api/v3/depth?symbol={simbolo}&limit=20"
            r = requests.get(url, timeout=5)
            
            if r.status_code != 200:
                continue
                
            data = r.json()
            bids = data.get("bids", []) # Órdenes de compra
            asks = data.get("asks", []) # Órdenes de venta
            
            if not bids or not asks:
                continue

            # Calcular volumen total en USDT para el Top 20 del libro
            total_bids_usdt = sum(float(p) * float(q) for p, q in bids)
            total_asks_usdt = sum(float(p) * float(q) for p, q in asks)
            
            # Calcular el promedio de dinero por nivel para adaptar el filtro al token
            volumen_promedio_nivel = total_bids_usdt / len(bids) if len(bids) > 0 else 0
            # Umbral dinámico: Buscamos órdenes que superen significativamente el promedio del libro
            umbral_dinamico = max(volumen_promedio_nivel * 1.5, 1000) # Mínimo $1,000 USDT de respaldo real

            # Buscar muros de compra individuales que superen el umbral adaptativo
            for precio_str, cantidad_str in bids[:10]:
                precio = float(precio_str)
                cantidad = float(cantidad_str)
                valor_muro_usdt = precio * cantidad

                if valor_muro_usdt >= umbral_dinamico:
                    clave_alerta = f"{simbolo}_{precio_str}"
                    tiempo_actual = time.time()
                    
                    # Evitar repetir la misma alerta antes de 30 minutos
                    if clave_alerta not in alertas_enviadas or (tiempo_actual - alertas_enviadas[clave_alerta]) > 1800:
                        alertas_enviadas[clave_alerta] = tiempo_actual
                        
                        # Análisis de Imbalance / Presión del mercado
                        if total_bids_usdt > total_asks_usdt:
                            imbalance = "🟢 FUERTE PRESIÓN DE COMPRA (Imbalance Alcista)"
                        else:
                            imbalance = "🔴 PRESIÓN DE VENTA DOMINANTE"

                        msg = (
                            f"💎 *OPORTUNIDAD SPOT (BAJA CAP): {simbolo}*\n\n"
                            f"🧱 *Muro de Soporte Detectado:* `{precio:,.6f}`\n"
                            f"💰 *Capital en el Muro:* `${valor_muro_usdt:,.2f} USDT`\n\n"
                            f"⚖️ *Balance del Libro:* \n"
                            f"🔹 Compras (Bids): `${total_bids_usdt:,.0f}`\n"
                            f"🔸 Ventas (Asks): `${total_asks_usdt:,.0f}`\n\n"
                            f"📊 *Estado:* {imbalance}\n\n"
                            f"💡 _Token exclusivo Spot: Sin manipulación de futuros._"
                        )
                        print(f"🔔 Alerta enviada para {simbolo}")
                        enviar_telegram(msg)
                        
        time.sleep(40) # Pausa entre cada ronda de revisión

    except Exception as e:
        print(f"⚠️ Error en el ciclo Spot: {e}")
        time.sleep(10)
