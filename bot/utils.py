import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاموس لتخزين معلومات المستخدمين
user_data_cache = {}

def format_size(size_bytes: int) -> str:
    """
    تنسيق حجم الملف من بايت إلى صيغة مقروءة.
    
    Args:
        size_bytes: حجم الملف بالبايت
        
    Returns:
        حجم الملف بصيغة مقروءة
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """
    تنسيق المدة من ثوانٍ إلى صيغة مقروءة.
    
    Args:
        seconds: المدة بالثواني
        
    Returns:
        المدة بصيغة مقروءة (ساعات:دقائق:ثوانٍ)
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def create_format_keyboard(video_info: Any, page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """
    إنشاء لوحة مفاتيح مضمنة لاختيار تنسيق الفيديو.
    
    Args:
        video_info: معلومات الفيديو
        page: رقم الصفحة الحالية
        items_per_page: عدد العناصر في كل صفحة
        
    Returns:
        لوحة مفاتيح مضمنة
    """
    # فصل تنسيقات الفيديو والصوت
    video_formats = [fmt for fmt in video_info.formats if fmt['type'] == 'video']
    audio_formats = [fmt for fmt in video_info.formats if fmt['type'] == 'audio']
    
    # إنشاء أزرار لتنسيقات الفيديو
    keyboard = []
    
    # إضافة عنوان للفيديو
    keyboard.append([InlineKeyboardButton("📹 تنسيقات الفيديو", callback_data="header_video")])
    
    # حساب نطاق التنسيقات للصفحة الحالية
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(video_formats))
    
    # إضافة أزرار تنسيقات الفيديو
    for i in range(start_idx, end_idx):
        fmt = video_formats[i]
        size_str = format_size(fmt['filesize']) if fmt['filesize'] > 0 else "غير معروف"
        button_text = f"🎬 {fmt['resolution']} ({size_str})"
        callback_data = f"format_{fmt['format_id']}_video"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # إضافة عنوان للصوت
    keyboard.append([InlineKeyboardButton("🎵 تنسيقات الصوت", callback_data="header_audio")])
    
    # إضافة أزرار تنسيقات الصوت
    for fmt in audio_formats[:2]:  # عرض أفضل تنسيقين للصوت فقط
        size_str = format_size(fmt['filesize']) if fmt['filesize'] > 0 else "غير معروف"
        button_text = f"🎵 {fmt['resolution']} ({size_str})"
        callback_data = f"format_{fmt['format_id']}_audio"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # إضافة أزرار التنقل بين الصفحات إذا كان هناك المزيد من التنسيقات
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{page-1}"))
    
    if end_idx < len(video_formats):
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # إضافة زر العودة
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def create_progress_keyboard() -> InlineKeyboardMarkup:
    """
    إنشاء لوحة مفاتيح مضمنة لإلغاء التحميل.
    
    Returns:
        لوحة مفاتيح مضمنة
    """
    keyboard = [[InlineKeyboardButton("❌ إلغاء التحميل", callback_data="cancel_download")]]
    return InlineKeyboardMarkup(keyboard)

def format_video_info(video_info: Any) -> str:
    """
    تنسيق معلومات الفيديو لعرضها للمستخدم.
    
    Args:
        video_info: معلومات الفيديو
        
    Returns:
        نص منسق يحتوي على معلومات الفيديو
    """
    duration_str = format_duration(video_info.duration)
    views_str = f"{video_info.views:,}" if video_info.views else "غير معروف"
    
    return (
        f"*🎬 {video_info.title}*\n\n"
        f"👤 *القناة:* {video_info.author}\n"
        f"⏱ *المدة:* {duration_str}\n"
        f"👁 *المشاهدات:* {views_str}\n\n"
        f"الرجاء اختيار تنسيق التحميل:"
    )

def update_progress_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, 
                           status: str, downloaded: int, total: int, eta: int) -> None:
    """
    تحديث رسالة التقدم أثناء التحميل.
    
    Args:
        context: سياق المحادثة
        chat_id: معرف المحادثة
        message_id: معرف الرسالة
        status: حالة التحميل
        downloaded: حجم البيانات المحملة
        total: إجمالي حجم البيانات
        eta: الوقت المتبقي
    """
    if status == 'downloading':
        if total > 0:
            percent = (downloaded / total) * 100
            progress_bar = generate_progress_bar(percent)
            downloaded_str = format_size(downloaded)
            total_str = format_size(total)
            eta_str = f"{eta} ثانية" if eta > 0 else "غير معروف"
            
            text = (
                f"⬇️ *جاري التحميل...*\n\n"
                f"{progress_bar}\n"
                f"*التقدم:* {percent:.1f}% ({downloaded_str} من {total_str})\n"
                f"*الوقت المتبقي:* {eta_str}"
            )
        else:
            downloaded_str = format_size(downloaded)
            text = f"⬇️ *جاري التحميل...*\n\n*تم تحميل:* {downloaded_str}"
    
    elif status == 'finished':
        text = "✅ *اكتمل التحميل!*\n\nجاري معالجة الملف..."
    
    else:
        text = f"ℹ️ *حالة التحميل:* {status}"
    
    try:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=create_progress_keyboard()
        )
    except Exception as e:
        logger.error(f"خطأ في تحديث رسالة التقدم: {str(e)}")

def generate_progress_bar(percent: float, length: int = 10) -> str:
    """
    إنشاء شريط تقدم نصي.
    
    Args:
        percent: النسبة المئوية للتقدم
        length: طول شريط التقدم
        
    Returns:
        شريط تقدم نصي
    """
    filled_length = int(length * percent / 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}]"

def clean_user_data(user_id: int) -> None:
    """
    تنظيف بيانات المستخدم من الذاكرة المؤقتة.
    
    Args:
        user_id: معرف المستخدم
    """
    if user_id in user_data_cache:
        del user_data_cache[user_id]
