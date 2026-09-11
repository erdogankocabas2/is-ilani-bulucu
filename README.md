# 🎯 Job Radar AI - Otomatik İş İlanı Tarayıcı, Analiz ve Raporlama Sistemi

Bu proje; ilgi duyduğunuz alanlar ve pozisyonlar için farklı platformlardaki (LinkedIn, Kariyer.net, Remote portalleri, WeWorkRemotely, Jobicy, Greenhouse ve Lever ATS sistemleri vb.) iş ilanlarını otomatik olarak tarayan, **yüklediğiniz PDF CV** ile karşılaştırarak **Google Gemini AI** ile analiz edip puanlayan, **SQLite** ve **Google Sheets**'te saklayan ve belirli aralıklarla size **şık bir HTML e-posta bülteni** ile bildiren uçtan uca akıllı bir otomasyon sistemidir.

---

## ✨ Özellikler

1. 🌐 **Çoklu Kaynak Desteği:**
   - **LinkedIn & Kariyer.net:** Türkiye ve global odaklı ilanlar.
   - **Remote Portalleri:** RemoteOK, WeWorkRemotely, Jobicy (REST API & RSS Feeds).
   - **ATS Şirket Sayfaları:** Greenhouse & Lever (GitLab, Canonical, Automattic, Spotify, Reddit, Stripe vb.).

2. 📄 **Otomatik PDF CV Analizi:**
   - Klasördeki PDF formatındaki özgeçmişinizi (`Erdoğan_Kocabaş_FlowCV_Resume_2026-09-10.pdf`) otomatik okur.
   - Deneyimlerinizi, yeteneklerinizi ve eğitim bilgilerinizi analiz için hazırlar.

3. 🤖 **Gemini AI Uyum Puanlama & Özet:**
   - Her ilanı CV'nizle karşılaştırarak **0-100 arası Uyum Skoru (Match Score)** hesaplar.
   - Rolün size neden uygun olduğunu anlatan 2-3 cümlelik **hap özet**, aranan kritik yetenekler ve tavsiye notu üretir.

4. 🗄️ **Tekilleştirme & Veri Depolama:**
   - **SQLite (`data/jobs.db`):** Daha önce taranmış ve gönderilmiş ilanları tekilleştirerek aynı ilanı tekrar tekrar almanızı engeller.
   - **Google Sheets & CSV:** Tüm ilanları canlı bir Google E-Tablosuna ve yerel `data/jobs_export.csv` dosyasına otomatik senkronize eder.

5. 📬 **Modern HTML E-Posta Bülteni:**
   - Skor rozetleri (Yeşil %80+, Mavi %65-79, Sarı %50-64), etiketler, özetler ve doğrudan başvuru butonları içeren şık bülten.

6. ⚡ **Ücretsiz & Sunucusuz Otomasyon (GitHub Actions):**
   - Bilgisayarınız kapalıyken bile GitHub Actions üzerinden günde 2 kez otomatik çalışır ve veritabanı durumunu repoya işler.

---

## 🚀 Hızlı Başlangıç & Kurulum

### 1. Depoyu Klonlayın ve Sanal Ortamı Hazırlayın
```bash
git clone <repo-url>
cd is-ilani-bulucu

python3 -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Ayarlayın (`.env`)
`.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```
Ardından `.env` dosyasını düzenleyin:
- `GEMINI_API_KEY`: [Google AI Studio](https://aistudio.google.com)'dan alacağınız ücretsiz API anahtarı.
- `SMTP_USER` & `SMTP_PASSWORD`: E-posta göndermek için Gmail adresiniz ve **Google Uygulama Şifresi (App Password)**.
- `RECIPIENT_EMAIL`: İlan bültenlerinin geleceği e-posta adresiniz.

> **💡 Gmail Uygulama Şifresi Nasıl Alınır?**
> 1. Google Hesabınızda **2 Adımlı Doğrulama**'yı açın.
> 2. `Hesap Güvenliği` -> `2 Adımlı Doğrulama` altından en alttaki **Uygulama Şifreleri (App Passwords)** bölümüne gidin.
> 3. İsim olarak "Job Radar" yazıp oluşturulan 16 haneli şifreyi `SMTP_PASSWORD` alanına yapıştırın.

---

## 🛠️ Kullanım ve CLI Komutları

### 1. Tam Otomasyonu Çalıştırma (Tarama -> AI Puanlama -> Sheets -> E-Posta)
```bash
python main.py --run-once
```

### 2. Sadece Scraper'ları Test Etme
```bash
python main.py --test-scrapers
```

### 3. Gemini AI ve CV Eşleştirmesini Test Etme
```bash
python main.py --test-ai
```

### 4. Test E-postası Gönderme (Şablon ve SMTP Kontrolü)
```bash
python main.py --test-email
```

### 5. Google Sheets / CSV Senkronizasyonu
```bash
python main.py --sync-sheets
```

---

## ⚙️ Kriterleri Özelleştirme (`config/config.yaml`)

`config/config.yaml` dosyasından dilediğiniz zaman arama kriterlerini değiştirebilirsiniz:
```yaml
search_criteria:
  job_titles:
    - "Product Manager"
    - "AI Engineer"
    - "Full Stack Developer"
    - "Business Development"
  
  keywords:
    - "Python"
    - "LLM"
    - "FastAPI"
    - "Growth"
  
  negative_keywords:
    - "WordPress"
    - "Stajyer"

profile:
  cv_pdf_path: "Erdoğan_Kocabaş_FlowCV_Resume_2026-09-10.pdf"
  min_match_score: 65 # Sadece %65 ve üzeri uyumlu ilanlar e-posta ile iletilir
```

---

## ⏰ GitHub Actions ile 7/24 Otomatik Çalıştırma

Projenizi bir GitHub özel (private) reposuna yükledikten sonra:
1. GitHub reponuzda **Settings -> Secrets and variables -> Actions** bölümüne gidin.
2. Aşağıdaki Secret'ları ekleyin:
   - `GEMINI_API_KEY`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `SENDER_EMAIL`
   - `RECIPIENT_EMAIL`
3. `.github/workflows/job_digest.yml` iş akışı her sabah ve akşam otomatik olarak çalışıp size bülteni gönderecektir.

---

## 🧪 Testleri Çalıştırma

```bash
PYTHONPATH=. pytest tests/
```
