import os
import sys
import logging
import threading
from typing import Dict, Optional, Any

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackQueryHandler, CallbackContext
)

# إضافة المجلد الرئيسي إلى مسار النظام
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import BOT_TOKEN, DOWNLOAD_PATH, FILE_EXPIRY, MAX_FILE_SIZE
from common.downloader import YouTubeDownloader
from bot.utils import (
    user_data_cache, format_video_info, create_format_keyboard,
    update_progress_message, clean_user_data
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

def start(update: Update, context: CallbackContext) -> None:
    """
    معالجة أمر البدء /start.
    """
    user = update.effective_user
    message = (
        f"👋 مرحبًا {user.first_name}!\n\n"
        f"أنا بوت تحميل فيديوهات يوتيوب. 🎬\n\n"
        f"ما عليك سوى إرسال رابط فيديو يوتيوب إلي وسأساعدك في تحميله بالتنسيق والجودة التي تفضلها.\n\n"
        f"يمكنك أيضًا زيارة موقعنا على الويب للتحميل: http://localhost:5000"
    )
    
    update.message.reply_text(message)

def help_command(update: Update, context: CallbackContext) -> None:
    """
    معالجة أمر المساعدة /help.
    """
    message = (
        "🔍 *كيفية استخدام البوت:*\n\n"
        "1️⃣ أرسل رابط فيديو يوتيوب\n"
        "2️⃣ اختر تنسيق التحميل (فيديو أو صوت)\n"
        "3️⃣ اختر الجودة المطلوبة\n"
        "4️⃣ انتظر حتى يتم التحميل\n\n"
        "📌 *الأوامر المتاحة:*\n"
        "/start - بدء استخدام البوت\n"
        "/help - عرض هذه المساعدة\n"
        "/cancel - إلغاء العملية الحالية\n\n"
        "🔗 *الروابط المدعومة:*\n"
        "- روابط يوتيوب العادية\n"
        "- روابط يوتيوب المختصرة\n"
        "- روابط يوتيوب شورتس\n"
        "- روابط يوتيوب ميوزك\n\n"
        "⚠️ *ملاحظات:*\n"
        f"- الحد الأقصى لحجم الملف: {MAX_FILE_SIZE/(1024*1024):.1f} ميجابايت\n"
        f"- يتم حذف الملفات تلقائيًا بعد {FILE_EXPIRY/3600:.1f} ساعة"
    )
    
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

def cancel(update: Update, context: CallbackContext) -> None:
    """
    معالجة أمر الإلغاء /cancel.
    """
    user_id = update.effective_user.id
    
    # تنظيف بيانات المستخدم
    clean_user_data(user_id)
    
    # إلغاء التحميل النشط إذا كان موجودًا
    if user_id in active_downloads:
        # لا يمكن إلغاء التحميل بسهولة مع yt-dlp، لكن يمكننا إزالته من القائمة النشطة
        del active_downloads[user_id]
    
    update.message.reply_text("✅ تم إلغاء العملية الحالية.")

def process_youtube_url(update: Update, context: CallbackContext) -> None:
    """
    معالجة رابط يوتيوب المرسل من المستخدم.
    """
    url = update.message.text
    user_id = update.effective_user.id
    
    # التحقق من صحة رابط يوتيوب
    if not downloader.is_valid_youtube_url(url):
        update.message.reply_text(
            "❌ الرابط الذي أدخلته غير صالح. الرجاء إدخال رابط يوتيوب صحيح."
        )
        return
    
    # إرسال رسالة انتظار
    wait_message = update.message.reply_text(
        "⏳ جاري استخراج معلومات الفيديو، يرجى الانتظار..."
    )
    
    try:
        # استخراج معلومات الفيديو
        video_info = downloader.extract_video_info(url)
        
        if not video_info:
            wait_message.edit_text(
                "❌ لم يتم العثور على معلومات الفيديو. الرجاء التحقق من الرابط والمحاولة مرة أخرى."
            )
            return
        
        # تخزين معلومات الفيديو في ذاكرة المستخدم المؤقتة
        user_data_cache[user_id] = {
            'url': url,
            'video_info': video_info,
            'page': 0
        }
        
        # إرسال معلومات الفيديو مع لوحة مفاتيح الاختيار
        formatted_info = format_video_info(video_info)
        keyboard = create_format_keyboard(video_info)
        
        # حذف رسالة الانتظار وإرسال معلومات الفيديو
        wait_message.delete()
        
        # إرسال صورة مصغرة مع معلومات الفيديو
        if video_info.thumbnail:
            update.message.reply_photo(
                photo=video_info.thumbnail,
                caption=formatted_info,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text(
                formatted_info,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"خطأ في معالجة رابط يوتيوب: {str(e)}")
        wait_message.edit_text(
            f"❌ حدث خطأ أثناء معالجة الرابط: {str(e)}"
        )

def button_callback(update: Update, context: CallbackContext) -> None:
    """
    معالجة الضغط على الأزرار في لوحة المفاتيح المضمنة.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # التحقق من وجود بيانات المستخدم
    if user_id not in user_data_cache:
        query.answer("⚠️ انتهت صلاحية الجلسة. الرجاء إرسال الرابط مرة أخرى.")
        query.edit_message_reply_markup(reply_markup=None)
        return
    
    # الحصول على بيانات المستخدم
    user_data = user_data_cache[user_id]
    callback_data = query.data
    
    # معالجة الإلغاء
    if callback_data == "cancel":
        clean_user_data(user_id)
        query.answer("تم الإلغاء")
        query.edit_message_reply_markup(reply_markup=None)
        query.edit_message_text(
            text=query.message.text if query.message.text else query.message.caption,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # معالجة إلغاء التحميل
    if callback_data == "cancel_download":
        if user_id in active_downloads:
            del active_downloads[user_id]
            query.answer("تم إلغاء التحميل")
            query.edit_message_text("❌ تم إلغاء التحميل.")
            return
        else:
            query.answer("لا يوجد تحميل نشط للإلغاء")
            return
    
    # معالجة تغيير الصفحة
    if callback_data.startswith("page_"):
        page = int(callback_data.split("_")[1])
        user_data['page'] = page
        query.answer(f"الصفحة {page + 1}")
        keyboard = create_format_keyboard(user_data['video_info'], page)
        query.edit_message_reply_markup(reply_markup=keyboard)
        return
    
    # معالجة رؤوس الأقسام (لا تفعل شيئًا)
    if callback_data.startswith("header_"):
        query.answer()
        return
    
    # معالجة اختيار التنسيق
    if callback_data.startswith("format_"):
        parts = callback_data.split("_")
        format_id = parts[1]
        format_type = parts[2]  # video أو audio
        
        # إرسال رسالة التحميل
        query.answer("جاري بدء التحميل...")
        progress_message = query.edit_message_text(
            "⬇️ *جاري التحميل...*\n\nجاري تجهيز الملف...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_progress_keyboard()
        )
        
        # بدء التحميل في خيط منفصل
        download_thread = threading.Thread(
            target=download_and_send,
            args=(context, user_id, user_data['url'], format_id, format_type, 
                  progress_message.chat_id, progress_message.message_id)
        )
        download_thread.start()
        
        # تخزين معلومات التحميل النشط
        active_downloads[user_id] = {
            'thread': download_thread,
            'chat_id': progress_message.chat_id,
            'message_id': progress_message.message_id
        }
        
        return

def download_and_send(context: CallbackContext, user_id: int, url: str, format_id: str, 
                     format_type: str, chat_id: int, message_id: int) -> None:
    """
    تحميل الفيديو وإرساله للمستخدم.
    """
    try:
        # دالة تحديث التقدم
        def progress_callback(status, downloaded, total, eta):
            update_progress_message(context, chat_id, message_id, status, downloaded, total, eta)
        
        # تحميل الفيديو أو الصوت
        if format_type == 'video':
            file_path = downloader.download_video(url, format_id, progress_callback)
        else:  # audio
            file_path = downloader.download_audio(url, format_id, progress_callback)
        
        # التحقق من نجاح التحميل
        if not file_path or not os.path.exists(file_path):
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="❌ فشل التحميل. الرجاء المحاولة مرة أخرى."
            )
            return
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ حجم الملف ({file_size/(1024*1024):.1f} ميجابايت) أكبر من الحد المسموح به ({MAX_FILE_SIZE/(1024*1024):.1f} ميجابايت)."
            )
            # حذف الملف
            os.remove(file_path)
            return
        
        # تحديث رسالة التقدم
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="✅ اكتمل التحميل! جاري إرسال الملف..."
        )
        
        # إرسال الملف
        file_name = os.path.basename(file_path)
        
        if format_type == 'video':
            with open(file_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    filename=file_name,
                    caption="🎬 تم التحميل بواسطة بوت تحميل يوتيوب"
                )
        else:  # audio
            with open(file_path, 'rb') as audio_file:
                context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    filename=file_name,
                    caption="🎵 تم التحميل بواسطة بوت تحميل يوتيوب"
                )
        
        # تحديث رسالة التقدم النهائية
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="✅ تم التحميل وإرسال الملف بنجاح!\n\nأرسل رابط فيديو آخر للتحميل."
        )
        
        # حذف الملف بعد الإرسال
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"خطأ في التحميل والإرسال: {str(e)}")
        try:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ حدث خطأ أثناء التحميل: {str(e)}"
            )
        except Exception:
            pass
    
    finally:
        # تنظيف بيانات المستخدم
        clean_user_data(user_id)
        
        # إزالة التحميل من القائمة النشطة
        if user_id in active_downloads:
            del active_downloads[user_id]

def error_handler(update: Update, context: CallbackContext) -> None:
    """
    معالجة الأخطاء.
    """
    logger.error(f"حدث خطأ: {context.error}")
    
    try:
        # إرسال رسالة خطأ للمستخدم
        if update and update.effective_chat:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ عذرًا، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى."
            )
    except Exception:
        pass

def cleanup_task() -> None:
    """
    مهمة دورية لتنظيف الملفات القديمة.
    """
    downloader.cleanup_old_files(FILE_EXPIRY)
    
def main() -> None:
    """
    الدالة الرئيسية لتشغيل البوت.
    """
    # إنشاء محدث
    updater = Updater(BOT_TOKEN)
    
    # الحصول على المرسل
    dispatcher = updater.dispatcher
    
    # إضافة معالجات الأوامر
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    
    # إضافة معالج الرسائل
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_youtube_url))
    
    # إضافة معالج الأزرار
    dispatcher.add_handler(CallbackQueryHandler(button_callback))
    
    # إضافة معالج الأخطاء
    dispatcher.add_error_handler(error_handler)
    
    # إضافة مهمة دورية لتنظيف الملفات القديمة
    updater.job_queue.run_repeating(lambda _: cleanup_task(), interval=3600, first=0)
    
    # بدء البوت
    updater.start_polling()
    logger.info("تم بدء تشغيل البوت!")
    
    # الانتظار حتى يتم إيقاف البوت
    updater.idle()

if __name__ == '__main__':
    main()
