import os
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
    _start_bot()
