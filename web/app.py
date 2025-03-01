import os
import sys
import json
import uuid
import logging
from typing import Dict, Optional, Any, List
from flask import Flask, render_template, request, jsonify, send_file, abort, url_for

# إضافة المجلد الرئيسي إلى مسار النظام
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DOWNLOAD_PATH, FILE_EXPIRY, MAX_FILE_SIZE
from common.downloader import YouTubeDownloader

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask
app = Flask(__name__)

# إنشاء محمل YouTube
downloader = YouTubeDownloader(DOWNLOAD_PATH)

# قاموس لتخزين معلومات التحميل
download_sessions = {}

@app.route('/')
def index():
    """صفحة البداية."""
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_info():
    """استخراج معلومات الفيديو من الرابط."""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'الرجاء إدخال رابط يوتيوب'}), 400
    
    # التحقق من صحة رابط يوتيوب
    if not downloader.is_valid_youtube_url(url):
        return jsonify({'error': 'الرابط الذي أدخلته غير صالح. الرجاء إدخال رابط يوتيوب صحيح.'}), 400
    
    try:
        # استخراج معلومات الفيديو
        video_info = downloader.extract_video_info(url)
        
        if not video_info:
            return jsonify({'error': 'لم يتم العثور على معلومات الفيديو. الرجاء التحقق من الرابط والمحاولة مرة أخرى.'}), 400
        
        # إنشاء معرف جلسة فريد
        session_id = str(uuid.uuid4())
        
        # تخزين معلومات الفيديو في الجلسة
        download_sessions[session_id] = {
            'url': url,
            'video_info': video_info
        }
        
        # تحويل معلومات الفيديو إلى قاموس
        video_data = {
            'id': video_info.video_id,
            'title': video_info.title,
            'thumbnail': video_info.thumbnail,
            'duration': video_info.duration,
            'author': video_info.author,
            'views': video_info.views,
            'formats': video_info.formats,
            'session_id': session_id
        }
        
        return jsonify({'success': True, 'video': video_data})
        
    except Exception as e:
        logger.error(f"خطأ في استخراج معلومات الفيديو: {str(e)}")
        return jsonify({'error': f'حدث خطأ أثناء معالجة الرابط: {str(e)}'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    """تحميل الفيديو بالتنسيق المحدد."""
    data = request.json
    session_id = data.get('session_id')
    format_id = data.get('format_id')
    format_type = data.get('format_type')  # 'video' أو 'audio'
    
    if not session_id or not format_id or not format_type:
        return jsonify({'error': 'بيانات غير كاملة'}), 400
    
    # التحقق من وجود الجلسة
    if session_id not in download_sessions:
        return jsonify({'error': 'انتهت صلاحية الجلسة. الرجاء إعادة استخراج معلومات الفيديو.'}), 400
    
    try:
        # الحصول على معلومات الجلسة
        session_data = download_sessions[session_id]
        url = session_data['url']
        
        # إنشاء معرف تحميل فريد
        download_id = str(uuid.uuid4())
        
        # تخزين معلومات التحميل
        download_sessions[session_id]['download_id'] = download_id
        download_sessions[session_id]['format_id'] = format_id
        download_sessions[session_id]['format_type'] = format_type
        download_sessions[session_id]['status'] = 'preparing'
        download_sessions[session_id]['progress'] = 0
        
        # بدء التحميل في خلفية العملية (في تطبيق حقيقي، يجب استخدام Celery أو خيوط)
        # هنا نستخدم طريقة مبسطة للتوضيح
        
        # تحميل الفيديو أو الصوت
        if format_type == 'video':
            file_path = downloader.download_video(url, format_id)
        else:  # audio
            file_path = downloader.download_audio(url, format_id)
        
        # التحقق من نجاح التحميل
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'فشل التحميل. الرجاء المحاولة مرة أخرى.'}), 500
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            # حذف الملف
            os.remove(file_path)
            return jsonify({
                'error': f'حجم الملف ({file_size/(1024*1024):.1f} ميجابايت) أكبر من الحد المسموح به ({MAX_FILE_SIZE/(1024*1024):.1f} ميجابايت).'
            }), 400
        
        # تحديث حالة التحميل
        download_sessions[session_id]['status'] = 'completed'
        download_sessions[session_id]['progress'] = 100
        download_sessions[session_id]['file_path'] = file_path
        
        # إنشاء رابط للتحميل
        download_url = url_for('get_file', download_id=download_id, _external=True)
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'download_url': download_url
        })
        
    except Exception as e:
        logger.error(f"خطأ في تحميل الفيديو: {str(e)}")
        return jsonify({'error': f'حدث خطأ أثناء التحميل: {str(e)}'}), 500

@app.route('/api/status/<download_id>', methods=['GET'])
def get_status(download_id):
    """الحصول على حالة التحميل."""
    # البحث عن معرف التحميل في جميع الجلسات
    for session_id, session_data in download_sessions.items():
        if session_data.get('download_id') == download_id:
            return jsonify({
                'status': session_data.get('status', 'unknown'),
                'progress': session_data.get('progress', 0)
            })
    
    return jsonify({'error': 'لم يتم العثور على التحميل'}), 404

@app.route('/download/<download_id>', methods=['GET'])
def get_file(download_id):
    """تحميل الملف المحمل."""
    # البحث عن معرف التحميل في جميع الجلسات
    for session_id, session_data in download_sessions.items():
        if session_data.get('download_id') == download_id:
            file_path = session_data.get('file_path')
            
            if not file_path or not os.path.exists(file_path):
                abort(404)
            
            # تحديد اسم الملف
            filename = os.path.basename(file_path)
            
            # إرسال الملف
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
    
    abort(404)

@app.route('/api/cleanup', methods=['POST'])
def cleanup_session():
    """تنظيف جلسة التحميل."""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'معرف الجلسة مطلوب'}), 400
    
    if session_id in download_sessions:
        # حذف الملف إذا كان موجودًا
        file_path = download_sessions[session_id].get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"خطأ في حذف الملف: {str(e)}")
        
        # حذف الجلسة
        del download_sessions[session_id]
    
    return jsonify({'success': True})

@app.errorhandler(404)
def page_not_found(e):
    """معالجة خطأ 404."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """معالجة خطأ 500."""
    return render_template('500.html'), 500

def cleanup_old_files():
    """تنظيف الملفات القديمة."""
    downloader.cleanup_old_files(FILE_EXPIRY)

if __name__ == '__main__':
    # تنظيف الملفات القديمة عند بدء التشغيل
    cleanup_old_files()
    
    # تشغيل التطبيق
    app.run(debug=True)
