# 🚀 Deploy ke Railway — Panduan Lengkap

## 📁 Struktur Folder yang Harus Diupload ke GitHub

```
YOLO-Detection-System/
├── models/                  ← KOSONG di GitHub (upload manual via Railway Volume)
├── assets/                  ← Logo dan gambar statis
├── app.py                   ← ✅ Sudah dimodifikasi untuk Railway
├── index.html               ← Tampilan web (3.1 sudah diaktifkan)
├── Procfile                 ← Perintah start server untuk Railway
├── runtime.txt              ← Versi Python yang dipakai
├── nixpacks.toml            ← Konfigurasi build Railway (backup)
├── requirements.txt         ← ✅ Sudah ditambahkan gunicorn & opencv-headless
├── .gitignore               ← Model .pt dikecualikan dari GitHub
└── README_RAILWAY.md        ← Panduan ini
```

---

## 🛠️ Langkah-langkah Deploy

### TAHAP 1 — Persiapkan GitHub Repository

1. Buka https://github.com → klik **New repository**
2. Nama repo: `yolo-detection-system` → klik **Create**
3. Upload semua file **kecuali folder `models/`** ke repo tersebut
   - Cukup drag & drop file di browser GitHub
   - File `.pt` JANGAN diupload (terlalu besar & ada di .gitignore)

### TAHAP 2 — Deploy di Railway

1. Buka https://railway.com → **Login** (bisa pakai akun GitHub)
2. Klik **New Project** → pilih **Deploy from GitHub repo**
3. Pilih repo `yolo-detection-system`
4. Railway otomatis mendeteksi Python & membuild

### TAHAP 3 — Upload Model .pt ke Railway Volume

Karena file `.pt` tidak bisa diupload ke GitHub (terlalu besar), gunakan Railway Volume:

1. Di dashboard Railway → klik service Anda
2. Klik tab **Volumes** → klik **Add Volume**
3. Mount path: `/app/models`
4. Setelah Volume terbuat, klik **Connect** → buka Railway Shell
5. Upload file via Railway CLI:
   ```bash
   # Install Railway CLI di komputer lokal
   npm install -g @railway/cli

   # Login
   railway login

   # Upload file .pt
   railway volume upload best1_1.pt /app/models/best1_1.pt
   railway volume upload best1_2.pt /app/models/best1_2.pt
   railway volume upload best2_1.pt /app/models/best2_1.pt
   railway volume upload best2_2.pt /app/models/best2_2.pt
   railway volume upload best3_1.pt /app/models/best3_1.pt
   railway volume upload best3_2.pt /app/models/best3_2.pt
   ```

### TAHAP 4 — Generate Domain Publik

1. Di Railway → klik service → tab **Settings**
2. Klik **Generate Domain** → dapat URL seperti:
   `https://yolo-detection-system-production.up.railway.app`

---

## ⚙️ Environment Variables (Opsional)

Railway sudah otomatis mengatur `PORT`. Tidak perlu konfigurasi tambahan.

---

## 🔍 Troubleshooting

| Masalah | Solusi |
|---|---|
| Build gagal | Pastikan `requirements.txt` ada di root folder |
| Model tidak ditemukan | Cek Volume sudah di-mount ke `/app/models` |
| Timeout saat inferensi | Normal untuk video panjang — Railway timeout default 300 detik |
| `gunicorn not found` | Pastikan `gunicorn` ada di `requirements.txt` |

---

## 💰 Biaya Railway

- **Free tier**: $5 kredit/bulan (cukup untuk demo & pengujian)
- **Hobby plan**: $5/bulan (lebih stabil, tidak sleep otomatis)
- Inferensi AI berat → rekomendasikan Hobby plan

© 2026 Politeknik Keselamatan Transportasi Jalan
