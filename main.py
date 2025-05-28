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
    except FileNotFoundError:
        return ["BTCUSDT", "ETHUSDT"]  # Yedek liste

# === Telegram Mesaj Gönderici ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    max_length = 4000  # Telegram mesaj sınırına yakın güvenli limit

    try:
        for i in range(0, len(message), max_length):
            part = message[i:i+max_length]
            payload = {
                "chat_id": CHAT_ID,
                "text": part
            }
            r = requests.post(url, data=payload)
            print("Telegram mesajı gönderildi:", r.json())
    except Exception as e:
        print("Telegram hatası:", e)

# === Hacim Kontrol Fonksiyonu ===
def check_volume_change():
    coins = load_coins()
    alerts = []  # %50 ve üzeri değişen coinler burada toplanacak

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

            if change >= 500:  # %500 ve üzeri artış için
                alerts.append(f"{coin}: %{change}")
        except Exception as e:
            print(f"Hacim kontrol hatası ({coin}): {e}")

    if alerts:
        msg = "[ALARM] Aşağıdaki coinlerde %500'den fazla hacim artışı var:\n" + "\n".join(alerts)
    else:
        msg = "Hacimde %500'den fazla artış yok."

    send_telegram_message(msg)


# === Arka Planda Sürekli Çalışan İşlem ===
def start_volume_bot():
    while True:
        print("Hacim kontrolü yapılıyor...")
        check_volume_change()
        time.sleep(300)  # 5 dakika bekle

# === Flask Web Server (UptimeRobot için) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif!"

# === Botu ve Web Server'ı Başlat ===
if __name__ == "__main__":
    # Başlatıldığında test mesajı gönder
    send_telegram_message("🔔 Bot başlatıldı. Hacim kontrolü 1 saatte bir yapılacak.")

    # Botu arka planda başlat
    threading.Thread(target=start_volume_bot).start()

    # Web sunucusunu başlat
    app.run(host="0.0.0.0", port=8080)
