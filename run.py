#!/usr/bin/env python3
import os
import sys
import argparse
import threading
import logging
from multiprocessing import Process

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_bot():
    """تشغيل بوت التلغرام."""
    try:
        from bot.telegram_bot import main as bot_main
        logger.info("جاري تشغيل بوت التلغرام...")
        bot_main()
    except Exception as e:
        logger.error(f"خطأ في تشغيل بوت التلغرام: {str(e)}")
        sys.exit(1)

def run_web():
    """تشغيل واجهة الويب."""
    try:
        from web.app import app
        from config import WEB_HOST, WEB_PORT, DEBUG
        logger.info(f"جاري تشغيل واجهة الويب على {WEB_HOST}:{WEB_PORT}...")
        app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG)
    except Exception as e:
        logger.error(f"خطأ في تشغيل واجهة الويب: {str(e)}")
        sys.exit(1)

def main():
    """الدالة الرئيسية."""
    parser = argparse.ArgumentParser(description='تشغيل بوت تحميل فيديوهات يوتيوب وواجهة الويب')
    parser.add_argument('--bot-only', action='store_true', help='تشغيل البوت فقط')
    parser.add_argument('--web-only', action='store_true', help='تشغيل واجهة الويب فقط')
    args = parser.parse_args()
    
    if args.bot_only:
        # تشغيل البوت فقط
        run_bot()
    elif args.web_only:
        # تشغيل واجهة الويب فقط
        run_web()
    else:
        # تشغيل كلاهما
        logger.info("جاري تشغيل بوت التلغرام وواجهة الويب...")
        
        # إنشاء عمليات منفصلة
        bot_process = Process(target=run_bot)
        web_process = Process(target=run_web)
        
        try:
            # بدء العمليات
            bot_process.start()
            web_process.start()
            
            # الانتظار حتى تنتهي العمليات
            bot_process.join()
            web_process.join()
        except KeyboardInterrupt:
            logger.info("تم إيقاف التشغيل بواسطة المستخدم")
            
            # إيقاف العمليات
            bot_process.terminate()
            web_process.terminate()
            
            # الانتظار حتى تنتهي العمليات
            bot_process.join()
            web_process.join()
            
            sys.exit(0)

if __name__ == '__main__':
    main()
