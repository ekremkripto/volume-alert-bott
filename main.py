import requests
import time
import threading
from flask import Flask
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Telegram bilgileri
TELEGRAM_TOKEN = "7426521746:AAF6Q0jLjICWEGgW_bS4AXfmdMlgZ8rL9f4"
CHAT_ID = "6521428327"
CRYPTO_API_KEY = "661200c9079b9706615c770477a45c662831df7a"



def load_coins():
    try:
        with open("coins.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except:
        return ["BTCUSDT", "ETHUSDT"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("Telegram mesajı:", response.json())
    except Exception as e:
        print("Telegram gönderim hatası:", e)

def check_volume_and_rsi():
    coins = load_coins()
    volume_alerts = []
    rsi_alerts = []

    for coin in coins:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={coin}&interval=15m&limit=15"
            response = requests.get(url)
            df = pd.DataFrame(response.json())
            if df.empty or len(df) < 15:
                continue

            df[4] = df[4].astype(float)  # Close fiyatı
            df[7] = df[7].astype(float)  # Hacim

            # RSI Hesabı
            delta = df[4].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            last_rsi = rsi.iloc[-1]

            if last_rsi > 70 or last_rsi < 30:
                rsi_alerts.append(f"{coin} RSI: {round(last_rsi,2)}")

            # Hacim kontrolü
            prev_vol = df[7].iloc[-2]
            curr_vol = df[7].iloc[-1]
            if prev_vol == 0:
                continue
            change = ((curr_vol - prev_vol) / prev_vol) * 100
            if abs(change) >= 50:
                volume_alerts.append(f"{coin} hacim değişimi: %{round(change, 2)}")

        except Exception as e:
            print(f"{coin} işlem hatası:", e)

    messages = []
    if volume_alerts:
        messages.append("📊 Hacim Uyarıları:\n" + "\n".join(volume_alerts))
    if rsi_alerts:
        messages.append("📈 RSI Uyarıları:\n" + "\n".join(rsi_alerts))
    if not messages:
        messages.append("🔍 Değişiklik yok. Tüm coinler normal.")
    
    send_telegram_message("\n\n".join(messages))

def check_news():
    try:
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_API_KEY}&filter=positive"
        response = requests.get(url)
        data = response.json()
        posts = data.get("results", [])[:3]  # Son 3 haberi al

        if not posts:
            return

        news_message = "📰 Yeni Pozitif Haberler:\n"
        for post in posts:
            title = post["title"]
            link = post["url"]
            news_message += f"- {title}\n{link}\n"

        send_telegram_message(news_message)

    except Exception as e:
        print("Haber kontrol hatası:", e)

def scheduled_task():
    while True:
        print("🔁 Kontrol başlatıldı:", datetime.now())
        check_volume_and_rsi()
        check_news()
        time.sleep(900)  # 15 dakika

@app.route("/")
def home():
    return "Bot aktif!"

if __name__ == "__main__":
    send_telegram_message("🚀 Bot başlatıldı! 15 dakikada bir RSI, hacim ve haber kontrolü yapılacak.")
    threading.Thread(target=scheduled_task).start()
    app.run(host="0.0.0.0", port=8080)
