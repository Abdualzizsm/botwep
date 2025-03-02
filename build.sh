#!/usr/bin/env bash
# تثبيت FFmpeg على Render

# تعيين متغير RENDER لتمكين إعدادات Render
export RENDER=true

# تحديث قائمة الحزم
apt-get update -qq

# تثبيت FFmpeg
apt-get install -y ffmpeg

# إنشاء مجلد التحميل
mkdir -p /tmp/youtube-downloader
chmod 777 /tmp/youtube-downloader

# طباعة إصدار FFmpeg للتأكد من التثبيت
echo "FFmpeg version:"
ffmpeg -version

# تعطيل البوت في النشر الأول حتى يتم إعادة التشغيل
export BOT_ENABLED=false
echo "BOT_ENABLED=false" > .env
echo "تم تعطيل البوت. يرجى تفعيله يدويًا من لوحة تحكم Render."

# إعداد اسم الخدمة لعنوان URL
export RENDER_SERVICE_NAME=$(echo $RENDER_SERVICE_NAME)
echo "RENDER_SERVICE_NAME=$RENDER_SERVICE_NAME" >> .env
echo "تم تعيين اسم الخدمة: $RENDER_SERVICE_NAME"

echo "Build script completed successfully!"
