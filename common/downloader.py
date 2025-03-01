import os
import time
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any
import yt_dlp
from pytube import YouTube

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VideoInfo:
    """فئة تمثل معلومات الفيديو المستخرجة من YouTube."""
    
    def __init__(self, video_id: str, title: str, thumbnail: str, duration: int, 
                 formats: List[Dict[str, Any]], author: str, views: int):
        self.video_id = video_id
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration
        self.formats = formats
        self.author = author
        self.views = views

class YouTubeDownloader:
    """فئة للتعامل مع تحميل فيديوهات YouTube."""
    
    def __init__(self, download_path: str):
        """
        تهيئة محمل YouTube.
        
        Args:
            download_path: المسار الذي سيتم حفظ الملفات فيه
        """
        self.download_path = download_path
        if not os.path.exists(download_path):
            os.makedirs(download_path)
    
    def extract_video_info(self, url: str) -> Optional[VideoInfo]:
        """
        استخراج معلومات الفيديو من رابط YouTube.
        
        Args:
            url: رابط فيديو YouTube
            
        Returns:
            كائن VideoInfo يحتوي على معلومات الفيديو أو None إذا فشلت العملية
        """
        try:
            # استخدام yt-dlp لاستخراج المعلومات
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'format': 'best',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # تنظيم تنسيقات الفيديو والصوت
                formats = []
                
                # إضافة تنسيقات الفيديو
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                        resolution = fmt.get('height', 0)
                        if resolution > 0:
                            formats.append({
                                'format_id': fmt['format_id'],
                                'ext': fmt.get('ext', 'mp4'),
                                'resolution': f"{resolution}p",
                                'filesize': fmt.get('filesize', 0),
                                'type': 'video'
                            })
                
                # إضافة تنسيقات الصوت
                audio_formats = [fmt for fmt in info.get('formats', []) 
                                if fmt.get('vcodec') == 'none' and fmt.get('acodec') != 'none']
                
                for fmt in audio_formats:
                    formats.append({
                        'format_id': fmt['format_id'],
                        'ext': 'mp3',  # سنحول إلى mp3
                        'resolution': f"{fmt.get('abr', 128)}kbps",
                        'filesize': fmt.get('filesize', 0),
                        'type': 'audio'
                    })
                
                # إزالة التكرارات وترتيب التنسيقات
                unique_formats = {}
                for fmt in formats:
                    key = f"{fmt['type']}_{fmt['resolution']}"
                    if key not in unique_formats or fmt['filesize'] > unique_formats[key]['filesize']:
                        unique_formats[key] = fmt
                
                sorted_formats = sorted(
                    unique_formats.values(),
                    key=lambda x: (
                        0 if x['type'] == 'video' else 1,
                        -int(x['resolution'].replace('p', '').replace('kbps', ''))
                    )
                )
                
                return VideoInfo(
                    video_id=info['id'],
                    title=info['title'],
                    thumbnail=info.get('thumbnail', ''),
                    duration=info.get('duration', 0),
                    formats=sorted_formats,
                    author=info.get('uploader', ''),
                    views=info.get('view_count', 0)
                )
                
        except Exception as e:
            logger.error(f"خطأ في استخراج معلومات الفيديو: {str(e)}")
            return None
    
    def download_video(self, url: str, format_id: str, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        تحميل فيديو من YouTube.
        
        Args:
            url: رابط فيديو YouTube
            format_id: معرف التنسيق المطلوب تحميله
            progress_callback: دالة استدعاء لتحديث التقدم
            
        Returns:
            مسار الملف المحمل أو None إذا فشلت العملية
        """
        try:
            # إنشاء اسم ملف فريد
            file_id = str(uuid.uuid4())
            temp_path = os.path.join(self.download_path, f"{file_id}_temp")
            
            # تكوين خيارات yt-dlp
            ydl_opts = {
                'format': format_id,
                'outtmpl': f"{temp_path}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
            }
            
            # إضافة دالة استدعاء التقدم إذا تم توفيرها
            if progress_callback:
                ydl_opts['progress_hooks'] = [
                    lambda d: progress_callback(d['status'], d.get('downloaded_bytes', 0), 
                                               d.get('total_bytes', 0), d.get('eta', 0))
                ]
            
            # تحميل الفيديو
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                # تحديد المسار النهائي
                _, ext = os.path.splitext(downloaded_file)
                final_path = os.path.join(self.download_path, f"{file_id}{ext}")
                
                # إعادة تسمية الملف
                if os.path.exists(downloaded_file):
                    os.rename(downloaded_file, final_path)
                    return final_path
                
                return None
                
        except Exception as e:
            logger.error(f"خطأ في تحميل الفيديو: {str(e)}")
            return None
    
    def download_audio(self, url: str, format_id: str, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        تحميل الصوت فقط من فيديو YouTube.
        
        Args:
            url: رابط فيديو YouTube
            format_id: معرف تنسيق الصوت
            progress_callback: دالة استدعاء لتحديث التقدم
            
        Returns:
            مسار ملف الصوت المحمل أو None إذا فشلت العملية
        """
        try:
            # إنشاء اسم ملف فريد
            file_id = str(uuid.uuid4())
            output_path = os.path.join(self.download_path, f"{file_id}.mp3")
            
            # تكوين خيارات yt-dlp
            ydl_opts = {
                'format': format_id,
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            # إضافة دالة استدعاء التقدم إذا تم توفيرها
            if progress_callback:
                ydl_opts['progress_hooks'] = [
                    lambda d: progress_callback(d['status'], d.get('downloaded_bytes', 0), 
                                               d.get('total_bytes', 0), d.get('eta', 0))
                ]
            
            # تحميل الصوت
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # التحقق من وجود الملف
                if os.path.exists(output_path):
                    return output_path
                
                # البحث عن الملف بامتداد مختلف
                for ext in ['.mp3', '.m4a', '.webm']:
                    potential_path = os.path.join(self.download_path, f"{file_id}{ext}")
                    if os.path.exists(potential_path):
                        return potential_path
                
                return None
                
        except Exception as e:
            logger.error(f"خطأ في تحميل الصوت: {str(e)}")
            return None
    
    def cleanup_old_files(self, expiry_seconds: int = 86400) -> None:
        """
        تنظيف الملفات القديمة من مجلد التحميل.
        
        Args:
            expiry_seconds: عدد الثواني بعد إنشاء الملف قبل اعتباره قديمًا
        """
        try:
            current_time = time.time()
            for filename in os.listdir(self.download_path):
                file_path = os.path.join(self.download_path, filename)
                
                # تخطي المجلدات
                if os.path.isdir(file_path):
                    continue
                    
                # التحقق من عمر الملف
                file_age = current_time - os.path.getctime(file_path)
                if file_age > expiry_seconds:
                    os.remove(file_path)
                    logger.info(f"تم حذف الملف القديم: {filename}")
                    
        except Exception as e:
            logger.error(f"خطأ في تنظيف الملفات القديمة: {str(e)}")
    
    def is_valid_youtube_url(self, url: str) -> bool:
        """
        التحقق مما إذا كان الرابط هو رابط YouTube صالح.
        
        Args:
            url: الرابط المراد التحقق منه
            
        Returns:
            True إذا كان الرابط صالحًا، False خلاف ذلك
        """
        try:
            # التحقق من وجود youtube.com أو youtu.be في الرابط
            if 'youtube.com' not in url and 'youtu.be' not in url:
                return False
                
            # محاولة استخراج معلومات الفيديو
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                ydl.extract_info(url, download=False, process=False)
                return True
                
        except Exception:
            return False
            
        return False
