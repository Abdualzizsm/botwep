// المتغيرات العامة
let sessionId = null;
let downloadId = null;
let statusCheckInterval = null;

// عناصر DOM
const youtubeForm = document.getElementById('youtube-form');
const youtubeUrl = document.getElementById('youtube-url');
const loadingElement = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const videoInfo = document.getElementById('video-info');
const videoThumbnail = document.getElementById('video-thumbnail');
const videoTitle = document.getElementById('video-title');
const videoAuthor = document.getElementById('video-author');
const videoDuration = document.getElementById('video-duration');
const videoViews = document.getElementById('video-views');
const videoFormatsList = document.getElementById('video-formats-list');
const audioFormatsList = document.getElementById('audio-formats-list');
const downloadProgress = document.getElementById('download-progress');
const progressBar = document.getElementById('progress-bar');
const downloadStatus = document.getElementById('download-status');
const downloadComplete = document.getElementById('download-complete');
const downloadLink = document.getElementById('download-link');
const newDownload = document.getElementById('new-download');

// تنسيق الحجم من بايت إلى صيغة مقروءة
function formatSize(sizeBytes) {
    if (sizeBytes === 0) return "0B";
    
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    
    while (sizeBytes >= 1024 && i < sizes.length - 1) {
        sizeBytes /= 1024;
        i++;
    }
    
    return `${sizeBytes.toFixed(2)} ${sizes[i]}`;
}

// تنسيق المدة من ثوانٍ إلى صيغة مقروءة
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

// تنسيق عدد المشاهدات
function formatViews(views) {
    return new Intl.NumberFormat('ar-SA').format(views);
}

// إظهار رسالة خطأ
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('d-none');
    loadingElement.classList.add('d-none');
}

// إخفاء رسالة الخطأ
function hideError() {
    errorMessage.classList.add('d-none');
    errorMessage.textContent = '';
}

// إظهار عنصر التحميل
function showLoading() {
    loadingElement.classList.remove('d-none');
    hideError();
    videoInfo.classList.add('d-none');
    downloadProgress.classList.add('d-none');
    downloadComplete.classList.add('d-none');
}

// إخفاء عنصر التحميل
function hideLoading() {
    loadingElement.classList.add('d-none');
}

// إظهار معلومات الفيديو
function showVideoInfo(videoData) {
    // تعيين الصورة المصغرة
    videoThumbnail.src = videoData.thumbnail;
    
    // تعيين العنوان
    videoTitle.textContent = videoData.title;
    
    // تعيين اسم القناة
    videoAuthor.textContent = `بواسطة: ${videoData.author}`;
    
    // تعيين المدة
    videoDuration.textContent = `⏱ ${formatDuration(videoData.duration)}`;
    
    // تعيين عدد المشاهدات
    videoViews.textContent = `👁 ${formatViews(videoData.views)} مشاهدة`;
    
    // تحديث قوائم التنسيقات
    updateFormatLists(videoData.formats);
    
    // إظهار معلومات الفيديو
    videoInfo.classList.remove('d-none');
    hideLoading();
}

// تحديث قوائم التنسيقات
function updateFormatLists(formats) {
    // تفريغ القوائم
    videoFormatsList.innerHTML = '';
    audioFormatsList.innerHTML = '';
    
    // فصل تنسيقات الفيديو والصوت
    const videoFormats = formats.filter(format => format.type === 'video');
    const audioFormats = formats.filter(format => format.type === 'audio');
    
    // إضافة تنسيقات الفيديو
    videoFormats.forEach(format => {
        const sizeStr = format.filesize > 0 ? formatSize(format.filesize) : 'غير معروف';
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <span>
                <i class="bi bi-film"></i> ${format.resolution}
            </span>
            <span class="badge bg-primary rounded-pill">${sizeStr}</span>
        `;
        
        // إضافة حدث النقر
        item.addEventListener('click', () => {
            startDownload(format.format_id, 'video');
        });
        
        videoFormatsList.appendChild(item);
    });
    
    // إضافة تنسيقات الصوت
    audioFormats.forEach(format => {
        const sizeStr = format.filesize > 0 ? formatSize(format.filesize) : 'غير معروف';
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <span>
                <i class="bi bi-music-note-beamed"></i> ${format.resolution}
            </span>
            <span class="badge bg-success rounded-pill">${sizeStr}</span>
        `;
        
        // إضافة حدث النقر
        item.addEventListener('click', () => {
            startDownload(format.format_id, 'audio');
        });
        
        audioFormatsList.appendChild(item);
    });
}

// بدء التحميل
function startDownload(formatId, formatType) {
    // إظهار شريط التقدم
    downloadProgress.classList.remove('d-none');
    videoInfo.classList.add('d-none');
    
    // تعيين قيمة شريط التقدم إلى 0
    updateProgressBar(0);
    
    // تحديث حالة التحميل
    downloadStatus.textContent = 'جاري تجهيز الملف...';
    
    // إرسال طلب التحميل
    fetch('/api/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: sessionId,
            format_id: formatId,
            format_type: formatType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // إظهار رسالة الخطأ
            downloadProgress.classList.add('d-none');
            showError(data.error);
            return;
        }
        
        // تخزين معرف التحميل
        downloadId = data.download_id;
        
        // تعيين رابط التحميل
        downloadLink.href = data.download_url;
        
        // بدء التحقق من حالة التحميل
        startStatusCheck();
    })
    .catch(error => {
        console.error('خطأ في بدء التحميل:', error);
        downloadProgress.classList.add('d-none');
        showError('حدث خطأ أثناء بدء التحميل. الرجاء المحاولة مرة أخرى.');
    });
}

// بدء التحقق من حالة التحميل
function startStatusCheck() {
    // إيقاف أي فاصل زمني سابق
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // إنشاء فاصل زمني جديد
    statusCheckInterval = setInterval(() => {
        checkDownloadStatus();
    }, 1000);
}

// التحقق من حالة التحميل
function checkDownloadStatus() {
    fetch(`/api/status/${downloadId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                clearInterval(statusCheckInterval);
                downloadProgress.classList.add('d-none');
                showError(data.error);
                return;
            }
            
            // تحديث شريط التقدم
            updateProgressBar(data.progress);
            
            // تحديث حالة التحميل
            if (data.status === 'preparing') {
                downloadStatus.textContent = 'جاري تجهيز الملف...';
            } else if (data.status === 'downloading') {
                downloadStatus.textContent = `جاري التحميل... ${data.progress}%`;
            } else if (data.status === 'completed') {
                clearInterval(statusCheckInterval);
                downloadProgress.classList.add('d-none');
                downloadComplete.classList.remove('d-none');
            }
        })
        .catch(error => {
            console.error('خطأ في التحقق من حالة التحميل:', error);
        });
}

// تحديث شريط التقدم
function updateProgressBar(progress) {
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    progressBar.textContent = `${progress}%`;
}

// تنظيف الجلسة
function cleanupSession() {
    if (sessionId) {
        fetch('/api/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        })
        .catch(error => {
            console.error('خطأ في تنظيف الجلسة:', error);
        });
    }
}

// إعادة تعيين النموذج
function resetForm() {
    youtubeForm.reset();
    hideError();
    videoInfo.classList.add('d-none');
    downloadProgress.classList.add('d-none');
    downloadComplete.classList.add('d-none');
    
    // تنظيف الجلسة
    cleanupSession();
    
    // إعادة تعيين المتغيرات
    sessionId = null;
    downloadId = null;
    
    // إيقاف التحقق من حالة التحميل
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

// معالجة تقديم النموذج
youtubeForm.addEventListener('submit', function(event) {
    event.preventDefault();
    
    const url = youtubeUrl.value.trim();
    
    if (!url) {
        showError('الرجاء إدخال رابط يوتيوب');
        return;
    }
    
    // إعادة تعيين النموذج
    resetForm();
    
    // إظهار عنصر التحميل
    showLoading();
    
    // إرسال طلب استخراج المعلومات
    fetch('/api/extract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // تخزين معرف الجلسة
        sessionId = data.video.session_id;
        
        // إظهار معلومات الفيديو
        showVideoInfo(data.video);
    })
    .catch(error => {
        console.error('خطأ في استخراج معلومات الفيديو:', error);
        showError('حدث خطأ أثناء استخراج معلومات الفيديو. الرجاء المحاولة مرة أخرى.');
    });
});

// معالجة نقر زر "تحميل فيديو جديد"
newDownload.addEventListener('click', resetForm);

// تنظيف الجلسة عند إغلاق الصفحة
window.addEventListener('beforeunload', cleanupSession);
