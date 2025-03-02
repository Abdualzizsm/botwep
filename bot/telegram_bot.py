import os
import sys
import logging
import threading
from typing import Dict, Optional, Any

from telegram import Update
from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

# إضافة المجلد الرئيسي إلى مسار النظام
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import BOT_TOKEN, DOWNLOAD_PATH, FILE_EXPIRY, MAX_FILE_SIZE, BASE_URL
from common.downloader import YouTubeDownloader
from bot.utils import (
    user_data_cache, format_video_info, create_format_keyboard,
    clean_user_data
)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء محمل YouTube
downloader = YouTubeDownloader(DOWNLOAD_PATH)

# قاموس لتخزين مهام التحميل النشطة
active_downloads = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة أمر البدء /start.
    """
    user = update.effective_user
    welcome_message = (
        f"👋 مرحبًا {user.first_name}!\n\n"
        f"أنا بوت تحميل فيديوهات يوتيوب. 🎬\n\n"
        f"يمكنك إرسال رابط فيديو يوتيوب وسأقوم بتحميله لك بالجودة التي تختارها.\n\n"
        f"يمكنك أيضًا استخدام واجهة الويب: {BASE_URL}\n\n"
        f"أرسل /help للحصول على مزيد من المعلومات."
    )
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة أمر المساعدة /help.
    """
    help_text = (
        "🔍 *كيفية استخدام البوت:*\n\n"
        "1️⃣ أرسل رابط فيديو يوتيوب\n"
        "2️⃣ اختر جودة التحميل المفضلة لديك\n"
        "3️⃣ انتظر حتى يتم تحميل الفيديو وإرساله إليك\n\n"
        "📌 *أوامر إضافية:*\n"
        "/start - بدء استخدام البوت\n"
        "/help - عرض هذه المساعدة\n"
        "/cancel - إلغاء العملية الحالية\n\n"
        "🔗 *واجهة الويب:*\n"
        f"يمكنك أيضًا استخدام واجهة الويب: {BASE_URL}\n\n"
        "⚠️ *ملاحظات:*\n"
        "- الحد الأقصى لحجم الملف هو 50 ميجابايت\n"
        "- قد يستغرق تحميل الفيديوهات الطويلة وقتًا أطول\n"
        "- إذا واجهت أي مشكلة، يرجى إعادة المحاولة لاحقًا"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة أمر الإلغاء /cancel.
    """
    user_id = update.effective_user.id
    
    # تنظيف بيانات المستخدم
    clean_user_data(user_id)
    
    # إلغاء التحميل النشط إذا وجد
    if user_id in active_downloads:
        del active_downloads[user_id]
    
    await update.message.reply_text("✅ تم إلغاء العملية الحالية.")

async def process_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة رابط يوتيوب المرسل من المستخدم.
    """
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # التحقق من أن الرسالة هي رابط يوتيوب
    if not downloader.is_valid_youtube_url(message_text):
        await update.message.reply_text(
            "❌ الرابط غير صالح. الرجاء إرسال رابط يوتيوب صالح."
        )
        return
    
    # إرسال رسالة "جاري المعالجة"
    processing_message = await update.message.reply_text(
        "⏳ جاري معالجة الرابط...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("إلغاء", callback_data="cancel")]
        ])
    )
    
    try:
        # استخراج معلومات الفيديو
        video_info = downloader.get_video_info(message_text)
        
        if not video_info:
            await processing_message.edit_text(
                "❌ لم يتم العثور على معلومات الفيديو. الرجاء التحقق من الرابط وإعادة المحاولة."
            )
            return
        
        # تخزين معلومات الفيديو في بيانات المستخدم
        user_data_cache[user_id] = {
            'url': message_text,
            'video_info': video_info,
            'page': 0
        }
        
        # إنشاء نص الرسالة
        message_text = format_video_info(video_info)
        
        # إنشاء لوحة المفاتيح
        keyboard = create_format_keyboard(video_info)
        
        # تحديث الرسالة
        await processing_message.edit_text(
            text=message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في معالجة رابط يوتيوب: {str(e)}")
        await processing_message.edit_text(
            f"❌ حدث خطأ أثناء معالجة الرابط: {str(e)}"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة الضغط على الأزرار في لوحة المفاتيح المضمنة.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # استخراج البيانات من الزر
    data = query.data
    
    # التحقق من وجود بيانات المستخدم
    if user_id not in user_data_cache:
        await query.edit_message_text(text="❌ انتهت الجلسة. الرجاء إرسال الرابط مرة أخرى.")
        return
    
    # استخراج بيانات المستخدم
    user_data = user_data_cache[user_id]
    
    # التحقق من نوع الزر
    if data.startswith('format_'):
        # استخراج معرف التنسيق
        format_id = data.replace('format_', '')
        
        # التحقق من وجود معلومات الفيديو
        if 'video_info' not in user_data:
            await query.edit_message_text(text="❌ لم يتم العثور على معلومات الفيديو. الرجاء إرسال الرابط مرة أخرى.")
            return
        
        # استخراج معلومات الفيديو
        video_info = user_data['video_info']
        url = user_data['url']
        
        # تحديث الرسالة
        progress_message = await query.edit_message_text(
            text="⏳ جاري التحضير للتحميل...",
            reply_markup=None
        )
        
        # إضافة المستخدم إلى قائمة التحميلات النشطة
        active_downloads[user_id] = {
            'url': url,
            'format_id': format_id,
            'format_type': 'video',
            'chat_id': chat_id,
            'message_id': progress_message.message_id
        }
        
        # بدء التحميل في خيط منفصل
        threading.Thread(
            target=lambda: asyncio.run(download_and_send(
                context, user_id, url, format_id, 'video', 
                chat_id, progress_message.message_id
            ))
        ).start()
        
    elif data == 'audio':
        # التحقق من وجود معلومات الفيديو
        if 'video_info' not in user_data:
            await query.edit_message_text(text="❌ لم يتم العثور على معلومات الفيديو. الرجاء إرسال الرابط مرة أخرى.")
            return
        
        # استخراج معلومات الفيديو
        url = user_data['url']
        
        # تحديث الرسالة
        progress_message = await query.edit_message_text(
            text="⏳ جاري التحضير للتحميل...",
            reply_markup=None
        )
        
        # إضافة المستخدم إلى قائمة التحميلات النشطة
        active_downloads[user_id] = {
            'url': url,
            'format_id': 'best',
            'format_type': 'audio',
            'chat_id': chat_id,
            'message_id': progress_message.message_id
        }
        
        # بدء التحميل في خيط منفصل
        threading.Thread(
            target=lambda: asyncio.run(download_and_send(
                context, user_id, url, 'best', 'audio', 
                chat_id, progress_message.message_id
            ))
        ).start()
        
    elif data == 'cancel':
        # إلغاء العملية الحالية
        if user_id in active_downloads:
            # حذف المستخدم من قائمة التحميلات النشطة
            del active_downloads[user_id]
            
            # تحديث الرسالة
            await query.edit_message_text(text="✅ تم إلغاء العملية. أرسل رابط فيديو آخر للتحميل.")
        else:
            # تنظيف بيانات المستخدم
            clean_user_data(user_id)
            
            # تحديث الرسالة
            await query.edit_message_text(text="✅ تم إلغاء العملية. أرسل رابط فيديو آخر للتحميل.")
    
    else:
        # زر غير معروف
        await query.edit_message_text(text="❌ خيار غير صالح. الرجاء إرسال الرابط مرة أخرى.")

async def download_and_send(context: ContextTypes.DEFAULT_TYPE, user_id: int, url: str, format_id: str, 
                     format_type: str, chat_id: int, message_id: int):
    """
    تحميل الفيديو وإرساله للمستخدم.
    """
    try:
        # إرسال رسالة بأن التحميل قد بدأ
        progress_message = f"⏳ *جاري التحميل...*\n\n" \
                          f"*الرابط:* {url}\n" \
                          f"*النوع:* {format_type}\n"
        
        # تحديث رسالة التقدم
        await update_progress_message(context, chat_id, message_id, "جاري التحميل", 0, 100, 0)
        
        # تحميل الفيديو أو الصوت
        if format_type == 'video':
            file_path = downloader.download_video(url, format_id, 
                                                 progress_callback=lambda progress, file_size, eta: 
                                                 update_progress_message(context, chat_id, message_id, 
                                                                               "جاري التحميل", 
                                                                               progress, file_size, eta))
        else:
            file_path = downloader.download_audio(url, 
                                                 progress_callback=lambda progress, file_size, eta: 
                                                 update_progress_message(context, chat_id, message_id, 
                                                                               "جاري التحميل", 
                                                                               progress, file_size, eta))
        
        # التحقق من أن الملف قد تم تحميله بنجاح
        if not file_path or not os.path.exists(file_path):
            await update_progress_message(context, chat_id, message_id, "فشل التحميل", 0, 0, 0)
            return
        
        # تحديث رسالة التقدم
        await update_progress_message(context, chat_id, message_id, "اكتمل التحميل", 100, 100, 0)
        
        # إرسال الملف
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # حجم الملف بالميجابايت
        
        # التحقق من حجم الملف
        if file_size > MAX_FILE_SIZE:
            # إذا كان الملف كبيرًا جدًا، أرسل رسالة خطأ
            error_message = f"⚠️ *حجم الملف كبير جدًا للإرسال عبر تلغرام*\n\n" \
                           f"حجم الملف: {file_size:.2f} ميجابايت\n" \
                           f"الحد الأقصى: {MAX_FILE_SIZE} ميجابايت\n\n" \
                           f"يمكنك تحميل الملف من خلال الرابط التالي:\n" \
                           f"{BASE_URL}/download?file={os.path.basename(file_path)}"
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=error_message,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # إرسال الملف
        if format_type == 'video':
            await context.bot.send_video(
                chat_id=chat_id,
                video=open(file_path, 'rb'),
                filename=os.path.basename(file_path),
                caption="🎬 تم التحميل بواسطة بوت تحميل يوتيوب",
                parse_mode=ParseMode.MARKDOWN,
                supports_streaming=True
            )
        else:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=open(file_path, 'rb'),
                filename=os.path.basename(file_path),
                caption="🎵 تم التحميل بواسطة بوت تحميل يوتيوب",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # حذف رسالة التقدم
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        # حذف الملف بعد الإرسال
        try:
            os.remove(file_path)
        except:
            pass
        
    except Exception as e:
        logger.error(f"خطأ أثناء تحميل وإرسال الملف: {str(e)}")
        try:
            await update_progress_message(context, chat_id, message_id, f"فشل التحميل: {str(e)}", 0, 0, 0)
        except:
            pass

    finally:
        # تنظيف بيانات المستخدم
        clean_user_data(user_id)
        
        # إزالة التحميل من القائمة النشطة
        if user_id in active_downloads:
            del active_downloads[user_id]

async def update_progress_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, 
                           status: str, downloaded: int, total: int, eta: int) -> None:
    """
    تحديث رسالة التقدم أثناء التحميل.
    """
    try:
        # حساب النسبة المئوية
        percentage = 0
        if total > 0:
            percentage = int((downloaded / total) * 100)
        
        # إنشاء شريط التقدم
        progress_bar = ""
        if percentage > 0:
            filled_length = int(20 * percentage // 100)
            progress_bar = "▓" * filled_length + "░" * (20 - filled_length)
        else:
            progress_bar = "░" * 20
        
        # تنسيق النص
        if status == "جاري التحميل" and total > 0:
            # تحويل الحجم إلى ميجابايت
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            
            # تنسيق الوقت المتبقي
            eta_str = ""
            if eta > 0:
                minutes, seconds = divmod(eta, 60)
                eta_str = f"{minutes}:{seconds:02d}"
            
            text = (
                f"⏳ *جاري التحميل...*\n\n"
                f"*التقدم:* {percentage}% ({downloaded_mb:.1f}/{total_mb:.1f} ميجابايت)\n"
                f"{progress_bar}\n"
                f"*الوقت المتبقي:* {eta_str}"
            )
        elif status == "اكتمل التحميل":
            text = f"✅ *تم التحميل بنجاح!*\n\nجاري إرسال الملف..."
        elif status == "فشل التحميل":
            text = f"❌ *فشل التحميل*\n\n{downloaded}"
        else:
            text = f"ℹ️ *حالة التحميل:* {status}"
        
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"خطأ في تحديث رسالة التقدم: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالجة الأخطاء.
    """
    logger.error(f"حدث خطأ: {context.error}")
    
    try:
        # إرسال رسالة خطأ للمستخدم
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ حدث خطأ: {context.error}"
            )
    except Exception as e:
        logger.error(f"خطأ أثناء معالجة الخطأ: {str(e)}")

async def cleanup_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    مهمة دورية لتنظيف الملفات القديمة.
    """
    downloader.cleanup_old_files(FILE_EXPIRY)
    logger.info(f"تم تنظيف الملفات القديمة (أكثر من {FILE_EXPIRY} ساعة)")

async def main():
    """
    الدالة الرئيسية لتشغيل البوت.
    """
    try:
        # إعداد البوت
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة معالجات الأوامر
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancel", cancel))
        
        # إضافة معالج الرسائل
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_youtube_url))
        
        # إضافة معالج الأزرار
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # إضافة معالج الأخطاء
        application.add_error_handler(error_handler)
        
        # إضافة مهمة دورية لتنظيف الملفات القديمة
        application.job_queue.run_repeating(cleanup_task, interval=3600, first=0)
        
        # بدء تشغيل البوت
        logger.info("تم بدء تشغيل البوت!")
        
        # استخدام طريقة run_polling مع تعيين drop_pending_updates=True لتجنب تعارضات getUpdates
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        # الانتظار حتى يتم إيقاف البوت
        await application.updater.idle()
        
    except Exception as e:
        logger.error(f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
