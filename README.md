# HARIKASHI — قاعدة بيانات حقيقية

هذا الإصدار يجمع الموقع وواجهة FastAPI وقاعدة PostgreSQL في مشروع واحد مناسب للرفع على GitHub ثم نشره على Render.

## الملفات
- `index.html` واجهة HARIKASHI.
- `backend/app/main.py` الخادم وقاعدة البيانات وواجهة API.
- `backend/requirements.txt` المكتبات المطلوبة.
- `render.yaml` إعداد النشر على Render.

## النشر
ارفع كل الملفات والمجلدات إلى مستودع GitHub، ثم أنشئ Web Service على Render من نفس المستودع. إعداد `render.yaml` يعرّف Web Service وقاعدة PostgreSQL.

## ملاحظة
النسخة المجانية من Render مناسبة للاختبار. Render يذكر أن قواعد PostgreSQL المجانية تنتهي بعد 30 يومًا، لذلك قبل إطلاق التطبيق بشكل دائم يجب الانتقال إلى خطة تخزين مناسبة.
