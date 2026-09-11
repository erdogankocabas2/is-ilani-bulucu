import os
from pathlib import Path
from typing import Optional
import pypdf
from src.utils.logger import logger

class ResumeParser:
    def __init__(self, pdf_path: Optional[str] = None):
        self.pdf_path = self._find_resume_path(pdf_path)
        self.raw_text: str = ""
        self._load_resume()

    def _find_resume_path(self, specific_path: Optional[str]) -> Optional[Path]:
        """Verilen yolu veya çalışma dizinindeki CV PDF dosyasını tespit eder."""
        if specific_path and Path(specific_path).exists():
            return Path(specific_path)

        # Otomatik arama
        workspace = Path(".")
        candidates = list(workspace.glob("*.pdf"))
        for c in candidates:
            name_lower = c.name.lower()
            if "resume" in name_lower or "cv" in name_lower or "erdogan" in name_lower or "kocabas" in name_lower:
                return c

        if candidates:
            return candidates[0]
        return None

    def _load_resume(self):
        """PDF dosyasından metni ayrıştırır."""
        if not self.pdf_path or not self.pdf_path.exists():
            logger.warning(f"CV PDF dosyası bulunamadı: {self.pdf_path}")
            return

        try:
            reader = pypdf.PdfReader(str(self.pdf_path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            self.raw_text = "\n".join(pages_text).strip()
            logger.info(f"✅ CV başarıyla yüklendi: [bold green]{self.pdf_path.name}[/bold green] ({len(self.raw_text)} karakter)")
        except Exception as e:
            logger.error(f"CV PDF okunurken hata: {e}")
            self.raw_text = ""

    def get_profile_summary(self) -> str:
        """AI analizinde kullanılmak üzere CV özetini döndürür."""
        if self.raw_text:
            return self.raw_text
        return (
            "Aday Profili: Boğaziçi Üniversitesi Endüstri Mühendisliği mezunu/öğrencisi. "
            "Product Management, AI Assistants/Agent deployment, Customer Experience (CX), "
            "Business Development, Growth, Data Analytics, Python ve Girişimcilik alanlarında deneyimli."
        )

# Varsayılan tekil parser örneği
resume_parser = ResumeParser()
