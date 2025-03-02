import os
import logging
import subprocess
import re
import time
import shutil
from typing import Dict, List, Optional, Tuple, Union

# استيراد المكتبات
try:
    import yt_dlp as youtube_dl
    USE_YT_DLP = True
    logging.info("تم استخدام yt-dlp للتحميل")
except ImportError:
    import pytube
    USE_YT_DLP = False
    logging.info("تم استخدام pytube للتحميل")

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self, download_path: str):
        """
        تهيئة محمل يوتيوب
        
        Args:
            download_path: مسار مجلد التحميل
        """
        self.download_path = download_path
        
        # التحقق من وجود FFmpeg
        self.has_ffmpeg = self._check_ffmpeg()
        if self.has_ffmpeg:
            logger.info("تم العثور على FFmpeg بنجاح.")
        else:
            logger.warning("لم يتم العثور على FFmpeg. بعض الميزات قد لا تعمل بشكل صحيح.")
    
    def _check_ffmpeg(self) -> bool:
        """التحقق من وجود FFmpeg على النظام"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_video_info(self, url: str) -> Dict:
        """
        الحصول على معلومات الفيديو
        
        Args:
            url: رابط الفيديو
            
        Returns:
            قاموس يحتوي على معلومات الفيديو
        """
        logger.info(f"جاري استخراج معلومات الفيديو من: {url}")
        
        try:
            if USE_YT_DLP:
                return self._get_video_info_ytdlp(url)
            else:
                return self._get_video_info_pytube(url)
        except Exception as e:
            logger.error(f"خطأ في استخراج معلومات الفيديو: {str(e)}")
            raise
    
    def _get_video_info_ytdlp(self, url: str) -> Dict:
        """الحصول على معلومات الفيديو باستخدام yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'format': 'best',
            'ignoreerrors': True,
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    raise ValueError("لم يتم العثور على معلومات الفيديو")
                
                # تنسيق المعلومات
                formats = []
                
                # إضافة تنسيقات الفيديو
                video_formats = [f for f in info.get('formats', []) 
                                if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
                
                # ترتيب حسب الدقة (من الأعلى إلى الأدنى)
                video_formats.sort(key=lambda x: (
                    x.get('height', 0) or 0, 
                    x.get('width', 0) or 0,
                    x.get('tbr', 0) or 0
                ), reverse=True)
                
                # إضافة تنسيقات الفيديو المميزة
                for fmt in video_formats:
                    height = fmt.get('height', 0)
                    if height and height >= 360:  # تجاهل الدقة المنخفضة جدًا
                        formats.append({
                            'id': fmt['format_id'],
                            'type': 'video',
                            'quality': f"{height}p",
                            'extension': fmt.get('ext', 'mp4'),
                            'size': fmt.get('filesize') or fmt.get('filesize_approx'),
                            'tbr': fmt.get('tbr'),  # معدل البت الإجمالي
                        })
                
                # إضافة تنسيقات الصوت فقط
                audio_formats = [f for f in info.get('formats', []) 
                                if f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none']
                
                # ترتيب حسب معدل البت (من الأعلى إلى الأدنى)
                audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                
                # إضافة أفضل تنسيق صوتي
                if audio_formats:
                    best_audio = audio_formats[0]
                    formats.append({
                        'id': best_audio['format_id'],
                        'type': 'audio',
                        'quality': f"{int(best_audio.get('abr', 128))}kbps",
                        'extension': best_audio.get('ext', 'mp3'),
                        'size': best_audio.get('filesize') or best_audio.get('filesize_approx'),
                        'abr': best_audio.get('abr'),  # معدل بت الصوت
                    })
                
                return {
                    'title': info.get('title', 'فيديو بدون عنوان'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'channel': info.get('uploader', 'غير معروف'),
                    'formats': formats
                }
            except Exception as e:
                logger.error(f"خطأ في yt-dlp: {str(e)}")
                raise
    
    def _get_video_info_pytube(self, url: str) -> Dict:
        """الحصول على معلومات الفيديو باستخدام pytube"""
        try:
            yt = pytube.YouTube(url)
            
            # تنسيق المعلومات
            formats = []
            
            # إضافة تنسيقات الفيديو
            for stream in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
                if stream.resolution:
                    formats.append({
                        'id': str(stream.itag),
                        'type': 'video',
                        'quality': stream.resolution,
                        'extension': stream.subtype,
                        'size': stream.filesize,
                    })
            
            # إضافة تنسيق الصوت
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if audio_stream:
                formats.append({
                    'id': str(audio_stream.itag),
                    'type': 'audio',
                    'quality': audio_stream.abr,
                    'extension': 'mp3',  # سيتم تحويله إلى mp3
                    'size': audio_stream.filesize,
                })
            
            return {
                'title': yt.title,
                'thumbnail': yt.thumbnail_url,
                'duration': yt.length,
                'channel': yt.author,
                'formats': formats
            }
        except Exception as e:
            logger.error(f"خطأ في pytube: {str(e)}")
            raise
    
    def download_video(self, url: str, format_id: str) -> Optional[str]:
        """
        تحميل الفيديو
        
        Args:
            url: رابط الفيديو
            format_id: معرف التنسيق
            
        Returns:
            مسار الملف المحمل أو None في حالة الفشل
        """
        logger.info(f"بدء تحميل الفيديو من {url} بتنسيق {format_id}")
        
        try:
            if USE_YT_DLP:
                return self._download_video_ytdlp(url, format_id)
            else:
                return self._download_video_pytube(url, format_id)
        except Exception as e:
            logger.error(f"خطأ في تحميل الفيديو: {str(e)}")
            # طباعة تفاصيل الخطأ للتصحيح
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _download_video_ytdlp(self, url: str, format_id: str) -> Optional[str]:
        """تحميل الفيديو باستخدام yt-dlp"""
        # إنشاء اسم ملف فريد
        timestamp = int(time.time())
        output_template = os.path.join(self.download_path, f'video_{timestamp}_%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'nooverwrites': True,
            'progress_hooks': [self._progress_hook],
        }
        
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"بدء تحميل الفيديو باستخدام yt-dlp: {url}")
                info = ydl.extract_info(url, download=True)
                
                if info is None:
                    logger.error("فشل في استخراج معلومات الفيديو")
                    return None
                
                # الحصول على مسار الملف المحمل
                if 'requested_downloads' in info and info['requested_downloads']:
                    file_path = info['requested_downloads'][0].get('filepath')
                    if file_path and os.path.exists(file_path):
                        logger.info(f"تم تحميل الفيديو بنجاح: {file_path}")
                        return file_path
                
                # محاولة بديلة للعثور على الملف
                video_id = info.get('id', '')
                ext = info.get('ext', 'mp4')
                expected_file = os.path.join(self.download_path, f'video_{timestamp}_{video_id}.{ext}')
                
                if os.path.exists(expected_file):
                    logger.info(f"تم العثور على الملف المحمل: {expected_file}")
                    return expected_file
                
                logger.error("لم يتم العثور على الملف المحمل")
                return None
        except Exception as e:
            logger.error(f"خطأ في yt-dlp أثناء التحميل: {str(e)}")
            return None
    
    def _download_video_pytube(self, url: str, format_id: str) -> Optional[str]:
        """تحميل الفيديو باستخدام pytube"""
        try:
            yt = pytube.YouTube(url)
            stream = yt.streams.get_by_itag(int(format_id))
            
            if not stream:
                logger.error(f"لم يتم العثور على التنسيق المطلوب: {format_id}")
                return None
            
            # تحميل الفيديو
            logger.info(f"بدء تحميل الفيديو باستخدام pytube: {url}")
            file_path = stream.download(output_path=self.download_path)
            
            if os.path.exists(file_path):
                logger.info(f"تم تحميل الفيديو بنجاح: {file_path}")
                return file_path
            else:
                logger.error("لم يتم العثور على الملف المحمل")
                return None
        except Exception as e:
            logger.error(f"خطأ في pytube أثناء التحميل: {str(e)}")
            return None
    
    def download_audio(self, url: str, format_id: str) -> Optional[str]:
        """
        تحميل الصوت
        
        Args:
            url: رابط الفيديو
            format_id: معرف التنسيق
            
        Returns:
            مسار الملف المحمل أو None في حالة الفشل
        """
        logger.info(f"بدء تحميل الصوت من {url} بتنسيق {format_id}")
        
        try:
            if USE_YT_DLP:
                return self._download_audio_ytdlp(url, format_id)
            else:
                return self._download_audio_pytube(url, format_id)
        except Exception as e:
            logger.error(f"خطأ في تحميل الصوت: {str(e)}")
            return None
    
    def _download_audio_ytdlp(self, url: str, format_id: str) -> Optional[str]:
        """تحميل الصوت باستخدام yt-dlp"""
        # إنشاء اسم ملف فريد
        timestamp = int(time.time())
        output_template = os.path.join(self.download_path, f'audio_{timestamp}_%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'nooverwrites': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if self.has_ffmpeg else [],
            'progress_hooks': [self._progress_hook],
        }
        
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"بدء تحميل الصوت باستخدام yt-dlp: {url}")
                info = ydl.extract_info(url, download=True)
                
                if info is None:
                    logger.error("فشل في استخراج معلومات الفيديو")
                    return None
                
                # الحصول على مسار الملف المحمل
                if 'requested_downloads' in info and info['requested_downloads']:
                    file_path = info['requested_downloads'][0].get('filepath')
                    if file_path and os.path.exists(file_path):
                        logger.info(f"تم تحميل الصوت بنجاح: {file_path}")
                        return file_path
                
                # محاولة بديلة للعثور على الملف
                video_id = info.get('id', '')
                ext = 'mp3' if self.has_ffmpeg else info.get('ext', 'mp3')
                expected_file = os.path.join(self.download_path, f'audio_{timestamp}_{video_id}.{ext}')
                
                if os.path.exists(expected_file):
                    logger.info(f"تم العثور على الملف المحمل: {expected_file}")
                    return expected_file
                
                logger.error("لم يتم العثور على الملف المحمل")
                return None
        except Exception as e:
            logger.error(f"خطأ في yt-dlp أثناء تحميل الصوت: {str(e)}")
            return None
    
    def _download_audio_pytube(self, url: str, format_id: str) -> Optional[str]:
        """تحميل الصوت باستخدام pytube"""
        try:
            yt = pytube.YouTube(url)
            stream = yt.streams.get_by_itag(int(format_id))
            
            if not stream:
                logger.error(f"لم يتم العثور على التنسيق المطلوب: {format_id}")
                return None
            
            # تحميل الصوت
            logger.info(f"بدء تحميل الصوت باستخدام pytube: {url}")
            file_path = stream.download(output_path=self.download_path)
            
            # تحويل إلى MP3 إذا كان FFmpeg متاحًا
            if self.has_ffmpeg and os.path.exists(file_path):
                try:
                    mp3_path = os.path.splitext(file_path)[0] + '.mp3'
                    cmd = [
                        'ffmpeg', '-i', file_path, 
                        '-vn', '-ab', '192k', 
                        '-ar', '44100', '-y', mp3_path
                    ]
                    
                    subprocess.run(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        check=True
                    )
                    
                    # حذف الملف الأصلي
                    os.remove(file_path)
                    file_path = mp3_path
                except Exception as e:
                    logger.error(f"خطأ في تحويل الملف إلى MP3: {str(e)}")
            
            if os.path.exists(file_path):
                logger.info(f"تم تحميل الصوت بنجاح: {file_path}")
                return file_path
            else:
                logger.error("لم يتم العثور على الملف المحمل")
                return None
        except Exception as e:
            logger.error(f"خطأ في pytube أثناء تحميل الصوت: {str(e)}")
            return None
    
    def _progress_hook(self, d):
        """تتبع تقدم التحميل"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                logger.info(f"تقدم التحميل: {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                logger.info(f"تقدم التحميل (تقديري): {percent:.1f}%")
            else:
                logger.info(f"تم تحميل {d['downloaded_bytes'] / (1024*1024):.1f} ميجابايت")
        elif d['status'] == 'finished':
            logger.info(f"اكتمل التحميل. حجم الملف: {d['downloaded_bytes'] / (1024*1024):.1f} ميجابايت")
        elif d['status'] == 'error':
            logger.error(f"خطأ في التحميل: {d.get('error', 'خطأ غير معروف')}")
