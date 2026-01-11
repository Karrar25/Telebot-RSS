import feedparser
import asyncio
import logging
import os
import json
from datetime import datetime

# محاولة استيراد المكتبات
try:
    from telegram import Bot
    from telegram.constants import ParseMode
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ==========================================
# إعدادات البوت - جاهزة للعمل
# ==========================================
TELEGRAM_TOKEN = "8105384548:AAHVJ6QrQwJSiws3PxXswVYXk43wYwMHHw8"
CHANNEL_ID = "@IRQnews_bot" 
OPENAI_API_KEY = "ضع_مفتاح_openai_هنا" 
CHECK_INTERVAL = 300 # فحص كل 5 دقائق

# إعداد OpenAI
client = None
if HAS_OPENAI and OPENAI_API_KEY != "ضع_مفتاح_openai_هنا":
    client = OpenAI(api_key=OPENAI_API_KEY)

# قائمة المصادر المحددة
RSS_FEEDS = [
    "https://www.aljazeera.net/aljazeerarss/all.xml",
    "https://www.alarabiya.net/.mrss/ar/last-24-hours.xml",
    "https://www.skynewsarabia.com/rss.xml",
    "https://www.bbc.com/arabic/index.xml",
    "https://www.france24.com/ar/rss",
    "https://www.almayadeen.net/rss",
    "https://almanar.com.lb/rss.php",
    "https://www.alhurra.com/rss",
    "https://www.syria.tv/rss",
    "https://www.reutersagency.com/feed/",
    "https://www.bloomberg.com/politics/feeds/site.xml"
]

IMPORTANT_KEYWORDS = [
    "عاجل", "انفجار", "قصف", "غارة", "اشتباكات", "هجوم", "اغتيال", "مقتل", "سقوط", 
    "احتلال", "عملية عسكرية", "انسحاب", "تصعيد", "هدنة", "مفاوضات", "انقلاب", 
    "زلزال", "كارثة", "اعتقال", "حالة طوارئ", "بيان عاجل", "مجلس الأمن", "تطورات"
]

SENT_NEWS_FILE = "sent_news.json"
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_sent_news(sent_list):
    with open(SENT_NEWS_FILE, "w") as f:
        json.dump(sent_list[-200:], f)

def clean_html(html):
    if HAS_BS4:
        try:
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text()
        except: return html
    return html

def is_important(title, summary):
    text = (title + " " + summary).lower()
    for keyword in IMPORTANT_KEYWORDS:
        if keyword in text:
            return True
    return False

async def rewrite_news(title, summary):
    if client is None:
        return f"🚨 *{title}*\n\n{summary}"
    prompt = f"أعد صياغة هذا الخبر بأسلوب إخباري عاجل وقوي:\n{title}\n{summary}"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return f"🚨 *{title}*\n\n{summary}"

async def fetch_and_post():
    if not HAS_TELEGRAM: return
    bot = Bot(token=TELEGRAM_TOKEN)
    sent_news = load_sent_news()
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                news_id = entry.get("id", entry.get("link"))
                if news_id not in sent_news:
                    title = entry.get("title", "")
                    summary = clean_html(entry.get("summary", entry.get("description", "")))
                    
                    if is_important(title, summary):
                        rewritten_content = await rewrite_news(title, summary)
                        try:
                            await bot.send_message(chat_id=CHANNEL_ID, text=rewritten_content, parse_mode=ParseMode.MARKDOWN)
                            sent_news.append(news_id)
                            save_sent_news(sent_news)
                            logger.info(f"تم النشر: {title}")
                            await asyncio.sleep(3)
                        except:
                            await bot.send_message(chat_id=CHANNEL_ID, text=rewritten_content)
                            sent_news.append(news_id)
                            save_sent_news(sent_news)
                    else:
                        sent_news.append(news_id)
                        save_sent_news(sent_news)
        except Exception as e:
            logger.error(f"خطأ في {url}: {e}")

async def main():
    print("--- البوت بدأ العمل ---")
    # إذا كان يعمل على GitHub Actions، سيعمل مرة واحدة
    if os.getenv("GITHUB_ACTIONS"):
        await fetch_and_post()
    else:
        # إذا كان يعمل على الهاتف أو الحاسوب، سيبقى يعمل في حلقة مستمرة
        while True:
            await fetch_and_post()
            print(f"تم الفحص. الانتظار {CHECK_INTERVAL} ثانية...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
