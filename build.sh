#!/usr/bin/env bash
# تثبيت FFmpeg على Render

# تحديث قائمة الحزم
apt-get update -qq

# تثبيت FFmpeg
apt-get install -y ffmpeg

# إنشاء مجلد التنزيلات
mkdir -p /tmp/youtube-downloader
chmod 777 /tmp/youtube-downloader

# طباعة إصدار FFmpeg للتأكد من التثبيت
ffmpeg -version

echo "Build script completed successfully!"
