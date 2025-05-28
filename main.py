import requests
import time
import threading
from flask import Flask

app = Flask(__name__)

# Telegram bilgileri
TELEGRAM_TOKEN = "7426521746:AAF6Q0jLjICWEGgW_bS4AXfmdMlgZ8rL9f4"
CHAT_ID = "6521428327"

# === Coin Listesi (coins.txt dosyasından okunur) ===
def load_coins():
    try:
        with open("coins.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except:
        return ["BTCUSDT", "ETHUSDT"]  # Yedek liste

# === Telegram Mesaj Gönderici ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, data=payload)
        print("Telegram mesajı gönderildi:", r.json())
    except Exception as e:
        print("Telegram hatası:", e)

# === Hacim Kontrol Fonksiyonu ===
def check_volume_change():
    coins = load_coins()
    alarms = []
    for coin in coins:
        url = f"https://api.binance.com/api/v3/klines?symbol={coin}&interval=5m&limit=2"
        try:
            response = requests.get(url)
            data = response.json()
            if len(data) < 2:
                continue
            prev_vol = float(data[0][7])
            curr_vol = float(data[1][7])
            if prev_vol == 0:
                continue
            change = ((curr_vol - prev_vol) / prev_vol) * 100
            change = round(change, 2)

            if abs(change) >= 500:
                alarms.append(f"[ALARM] {coin} hacim değişimi: %{change}")
        except Exception as e:
            print(f"Hacim kontrol hatası ({coin}):", e)

    if alarms:
        for msg in alarms:
            send_telegram_message(msg)
    else:
        send_telegram_message("⏱️ Hacim değişimi %500'yi aşmadı. Değişiklik yok.")

# === RSI Kontrol Fonksiyonu ===
def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_rsi():
    coins = load_coins()
    for coin in coins:
        url = f"https://api.binance.com/api/v3/klines?symbol={coin}&interval=1h&limit=100"
        try:
            response = requests.get(url)
            data = response.json()
            closes = [float(kline[4]) for kline in data]
            df = pd.DataFrame(closes, columns=["close"])
            rsi_series = get_rsi(df["close"])
            latest_rsi = rsi_series.iloc[-1]

            if latest_rsi >= 70:
                send_telegram_message(f"🔴 RSI AŞIRI ALIM: {coin} RSI = {round(latest_rsi, 2)}")
            elif latest_rsi <= 30:
                send_telegram_message(f"🟢 RSI AŞIRI SATIM: {coin} RSI = {round(latest_rsi, 2)}")
        except Exception as e:
            print(f"RSI kontrol hatası ({coin}):", e)

# === Arka Planda Sürekli Çalışan İşlem ===
def start_bot():
    while True:
        print("Kontroller yapılıyor...")
        check_volume_change()
        check_rsi()
        time.sleep(300)  # 5 dakika bekle

# === Flask Web Server (UptimeRobot için) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif!"

# === Botu ve Web Server'ı Başlat ===
if __name__ == "__main__":
    send_telegram_message("🤖 Bot başlatıldı. Her 5 dakikada hacim ve RSI kontrolü yapılacak.")
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=8080)

    # Web sunucusunu başlat
    app.run(host="0.0.0.0", port=8080)
