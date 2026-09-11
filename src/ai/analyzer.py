import json
import os
import re
from typing import Any, Dict, List, Optional
from src.utils.config_loader import config
from src.utils.logger import logger
from src.ai.resume_parser import resume_parser

class JobAnalyzer:
    def __init__(self):
        self.api_key = config.get("ai.api_key") or os.getenv("GEMINI_API_KEY")
        self.model_name = config.get("ai.model_name", "gemini-3.7-flash")
        self.client = None
        self._init_client()

    def _init_client(self):
        """Google GenAI Client'ı başlatır."""
        if not self.api_key:
            logger.warning("⚠️ GEMINI_API_KEY bulunamadı. Kural tabanlı yedek puanlama kullanılacak.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"✨ Gemini AI Analiz Motoru aktif ([cyan]{self.model_name}[/cyan])")
        except Exception as e:
            logger.error(f"Gemini Client başlatılamadı: {e}")
            self.client = None

    def analyze_job(self, job: Dict[str, Any], candidate_cv_text: Optional[str] = None) -> Dict[str, Any]:
        """Bir iş ilanını adayın CV profili ile karşılaştırıp analiz eder."""
        if not candidate_cv_text:
            candidate_cv_text = resume_parser.get_profile_summary()

        if self.client:
            try:
                return self._analyze_with_gemini(job, candidate_cv_text)
            except Exception as e:
                logger.warning(f"Gemini API hatası, kural tabanlı analize geçiliyor: {e}")

        return self._fallback_rule_analysis(job)

    def _analyze_with_gemini(self, job: Dict[str, Any], candidate_cv: str) -> Dict[str, Any]:
        """Gemini modeli ile yapılandırılmış analiz ve uyum puanı üretir."""
        from google.genai import types

        prompt = f"""
Aşağıda bir adayın özgeçmişi (CV) ve Türkiye'de taranan bir iş ilanının detayları yer almaktadır.
Göreviniz adayın profili ile iş ilanının gereksinimlerini profesyonel bir İK ve Kariyer Danışmanı gözüyle karşılaştırmaktır.

=== ADAY ÖZGEÇMİŞİ (CV) ===
{candidate_cv[:4000]}

=== İŞ İLANI DETAYLARI ===
Başlık: {job.get('title')}
Şirket: {job.get('company')}
Lokasyon: {job.get('location')}
Çalışma Türü: {job.get('work_type')}
Açıklama:
{job.get('description', '')[:4000]}

=== KRİTİK DEĞERLENDİRME KURALLARI ===
1. Aday Boğaziçi Üniversitesi Endüstri Mühendisliği son sınıf / yeni mezun seviyesindedir. Aday özellikle **Yeni Mezun (New Grad), Giriş Seviyesi (Entry-Level), Management Trainee (MT), Stajyer (Uzun Dönem/Part-Time) veya Junior** rolleri hedeflemektedir.
2. EĞER pozisyon 3 yıldan fazla tecrübe arayan Senior, Lead, Executive seviyesinde bir pozisyonsa; adaya uygun değildir. Uyum Skorunu (score) 35'in altında tutun ve recommendation olarak "Uygun Değil" yazın.
3. EĞER pozisyon Yeni Mezun, MT, Junior, Giriş Seviyesi, Growth Specialist, Ürün Uzmanı (Product), İş Analisti veya Müşteri Deneyimi (CX) alanında bir pozisyonsa ve adayın geçmişiyle (Getirfinans AI/CX, SabancıDx Ürün, P&G Marka/Büyüme, Buluttan İş Geliştirme) örtüşüyorsa; Uyum Skorunu 75-95 aralığında verin.

=== YÖNERGELER ===
Lütfen yanıtı SADECE aşağıdaki JSON formatında ver:
{{
  "score": (0 ile 100 arasında tam sayı uyumluluk puanı),
  "summary": "İlanın rolünü, seviyesini ve adayın profiline neden uygun/uygun olmadığını anlatan 2-3 cümlelik Türkçe net özet.",
  "key_skills": ["İlanda aranan ve adayın bildiği veya dikkat çeken 3-6 anahtar yetenek"],
  "match_reasons": ["Adayın bu pozisyona uygun olduğunu gösteren 2-3 somut neden"],
  "missing_skills": ["İlanda istenip adayın CV'sinde eksik kalabilecek yetenekler (varsa)"],
  "recommendation": "Kuvvetle Tavsiye Edilir" | "Tavsiye Edilir" | "Düşünülebilir" | "Uygun Değil"
}}
"""
        models_to_try = [self.model_name, "gemini-flash-latest", "gemini-2.5-flash-lite"]
        last_error = None

        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    )
                )

                text = response.text.strip()
                data = json.loads(text)
                return {
                    "ai_score": int(data.get("score", 50)),
                    "ai_summary": data.get("summary", ""),
                    "key_skills": data.get("key_skills", []),
                    "pros_cons": {
                        "match_reasons": data.get("match_reasons", []),
                        "missing_skills": data.get("missing_skills", []),
                        "recommendation": data.get("recommendation", "Tavsiye Edilir")
                    }
                }
            except Exception as e:
                last_error = e
                logger.debug(f"Model {model} denenirken hata: {e}")

        raise last_error

    def _fallback_rule_analysis(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """API anahtarı olmadığında veya hata durumunda çalışan kural tabanlı analiz."""
        title = job.get("title", "").lower()
        desc = job.get("description", "").lower()
        full_text = f"{title} {desc}"

        score = 50
        matched_skills = []

        keywords = config.get("search_criteria.keywords", ["Python", "Product", "Data", "AI", "Engineering"])
        for kw in keywords:
            if kw.lower() in full_text:
                score += 8
                matched_skills.append(kw)

        # Target job titles bonus
        target_titles = config.get("search_criteria.job_titles", [])
        for tt in target_titles:
            if tt.lower() in title:
                score += 15
                break

        # Negative keywords penalty
        neg_keywords = config.get("search_criteria.negative_keywords", [])
        for nkw in neg_keywords:
            if nkw.lower() in full_text:
                score -= 25

        score = max(0, min(100, score))

        return {
            "ai_score": score,
            "ai_summary": f"{job.get('company', '')} bünyesinde {job.get('title', '')} pozisyonu. Profil anahtar kelimelerinizle eşleşti.",
            "key_skills": matched_skills[:5],
            "pros_cons": {
                "match_reasons": ["Kural tabanlı anahtar kelime eşleşmesi"],
                "missing_skills": [],
                "recommendation": "Tavsiye Edilir" if score >= 65 else "Düşünülebilir"
            }
        }

analyzer = JobAnalyzer()
