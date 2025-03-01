import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env إذا كان موجودًا
load_dotenv()

# تكوين البوت
BOT_TOKEN = os.getenv('BOT_TOKEN', '7865143004:AAHx7HMah28CkHkBNmS8uEML-GAzJ6qF8V0')

# تكوين تطبيق الويب
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', 5000))
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# مسار التحميل
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads'))

# إنشاء مجلد التحميل إذا لم يكن موجودًا
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

# الحد الأقصى لحجم الملف (بالبايت) - 50 ميجابايت افتراضيًا
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))

# مدة انتهاء صلاحية الملفات المؤقتة (بالثواني) - 24 ساعة افتراضيًا
FILE_EXPIRY = int(os.getenv('FILE_EXPIRY', 24 * 60 * 60))
