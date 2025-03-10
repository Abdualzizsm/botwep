from web.app import app
import threading
import os
import sys
import logging

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إضافة المجلد الرئيسي إلى مسار البحث
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# استيراد دالة تشغيل البوت
from bot import start_bot

# تشغيل البوت في خيط منفصل فقط إذا لم يكن هناك نسخة أخرى تعمل
def run_bot():
    """
    تشغيل بوت تلغرام في خيط منفصل
    """
    try:
        # تشغيل البوت من خلال الدالة المعرفة في bot/__init__.py
        start_bot()
    except Exception as e:
        logger.error(f"خطأ في تشغيل بوت التلغرام: {str(e)}")

# بدء تشغيل البوت في خيط منفصل
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()
logger.info("تم بدء خيط البوت")

if __name__ == "__main__":
    app.run()
