from web.app import app
import threading
import os
import sys

# إضافة المجلد الرئيسي إلى مسار البحث
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# استيراد البوت
from bot.bot import start_bot

# تشغيل البوت في خيط منفصل
def run_bot():
    try:
        start_bot()
    except Exception as e:
        print(f"خطأ في تشغيل البوت: {str(e)}")

# بدء تشغيل البوت في خيط منفصل
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    app.run()
