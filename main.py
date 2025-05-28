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
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload)
        print("Telegram mesajı gönderildi:", r.json())
    except Exception as e:
        print("Telegram hatası:", e)

# === Değişiklik takip için global değişkenler ===
last_volume_changes = {}
last_rsi_values = {}
sent_news_ids = set()

# === Hacim ve RSI Kontrol Fonksiyonu ===
def check_market():
    coins = load_coins()
    volume_alerts = []
    rsi_alerts = []

    for coin in coins:
        try:
            # Binance 5dk mum verisi
            url = f"https://api.binance.com/api/v3/klines?symbol={coin}&interval=5m&limit=2"
            response = requests.get(url)
            data = response.json()
            if len(data) < 2:
                continue

            # Hacim değişimi
            prev_vol = float(data[0][7])
            curr_vol = float(data[1][7])
            if prev_vol == 0:
                continue
            volume_change = ((curr_vol - prev_vol) / prev_vol) * 100
            volume_change = round(volume_change, 2)

            last_change = last_volume_changes.get(coin, 0)
            if abs(volume_change - last_change) >= 50:
                volume_alerts.append(f"{coin}: %{volume_change} hacim değişimi")
                last_volume_changes[coin] = volume_change

            # RSI hesaplama için kapanış fiyatları alınır
            closes = [float(candle[4]) for candle in data]
            rsi = calculate_rsi(closes)
            last_rsi = last_rsi_values.get(coin, None)
            if last_rsi is None or abs(rsi - last_rsi) >= 5:
                rsi_alerts.append(f"{coin}: RSI %{round(rsi,2)}")
                last_rsi_values[coin] = rsi

        except Exception as e:
            print(f"Piyasa kontrol hatası ({coin}):", e)

    # Mesajları gönder
    messages = []
    if volume_alerts:
        messages.append("🔔 Hacim değişimleri:\n" + "\n".join(volume_alerts))
    if rsi_alerts:
        messages.append("📈 RSI değişimleri:\n" + "\n".join(rsi_alerts))

    if messages:
        send_telegram_message("\n\n".join(messages))
    else:
        print("Değişiklik yok, mesaj gönderilmedi.")

# === RSI Hesaplama Fonksiyonu ===
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    avg_gain = sum(gains)/period
    avg_loss = sum(losses)/period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# === Haberleri Kontrol Fonksiyonu ===
def check_news():
    global sent_news_ids
    try:
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_API_KEY}&filter=positive"
        response = requests.get(url)
        data = response.json()
        posts = data.get("results", [])[:5]

        new_posts = []
        for post in posts:
            post_id = post.get("id") or post.get("url")
            if post_id and post_id not in sent_news_ids:
                new_posts.append(post)
                sent_news_ids.add(post_id)

        if not new_posts:
            print("Yeni haber yok.")
            return

        news_message = "📰 Yeni Pozitif Haberler:\n"
        for post in new_posts:
            title = post["title"]
            link = post["url"]
            news_message += f"- {title}\n{link}\n"

        send_telegram_message(news_message)

    except Exception as e:
        print("Haber kontrol hatası:", e)

# === Arka planda sürekli çalışan işlev ===
def start_bot():
    while True:
        print("Piyasa ve haber kontrolü yapılıyor...")
        check_market()
        check_news()
        time.sleep(900)  # 15 dakika bekle

# === Flask Web Server (uptime için) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif!"

# === Program başlangıcı ===
if __name__ == "__main__":
    send_telegram_message("🔔 Bot başlatıldı. Her 15 dakikada hacim, RSI ve haber kontrolü yapılacak.")
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
