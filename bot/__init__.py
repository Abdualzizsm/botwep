import os
import asyncio
from bot.telegram_bot import main as _start_bot

def start_bot():
    """
    بدء تشغيل البوت مع التحقق من متغير البيئة BOT_ENABLED
    """
    # التحقق من متغير البيئة BOT_ENABLED
    if os.environ.get('BOT_ENABLED', 'true').lower() != 'true':
        print("البوت معطل عن طريق متغير البيئة BOT_ENABLED")
        return
    
    # تشغيل البوت فقط إذا كان مُمكّنًا
    try:
        # استخدام asyncio لتشغيل الدالة غير المتزامنة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_start_bot())
    except Exception as e:
        print(f"خطأ في تشغيل البوت: {str(e)}")
