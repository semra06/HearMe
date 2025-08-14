import os
import numpy as np
import pyaudio
# TensorFlow uyarılarını kapat
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Uyarıları kapat
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*")
warnings.filterwarnings("ignore", message=".*return_all_scores.*")
warnings.filterwarnings("ignore", message=".*not initialized from the model checkpoint.*")
warnings.filterwarnings("ignore", message=".*You should probably TRAIN this model.*")
warnings.filterwarnings("ignore", message=".*BertForSequenceClassification.*")
warnings.filterwarnings("ignore", message=".*newly initialized.*")
warnings.filterwarnings("ignore", message=".*down-stream task.*")
warnings.filterwarnings("ignore", message=".*predictions and inference.*")

# Tüm uyarıları kapat
warnings.simplefilter("ignore")

import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import requests
import json
import torch
import time

# ===== KONFİGÜRASYON AYARLARI =====

# Gmail E-posta Ayarları
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 465
EMAIL_SENDER = "smrknnc@gmail.com"
EMAIL_PASSWORD = "vhdq hsfn jgxm obsi"  # Gmail Uygulama Şifresi
EMAIL_RECIPIENTS = [
    "smrknnc@gmail.com",
]

# WhatsApp Business API Ayarları
WHATSAPP_API_TOKEN = "EAFXxRnXU3TEBPMXjwePws8sKxMZBh8vDPpoyIAsjufaaBZB6eGXnmwZAmzZBxC8sfAK9x0XLmQIC0354SgN8aD8zwuXc8p3xUjC8MAJLYZBmMwLpakNwPNHkpNDDS930YojSPqC1oUNQJba3xzLRcnctcdvDL5V8saNNAlt1wDwjGH93Q00JDkh3WVGYMxtqSxUwdwvwopdZB9kDw4YXJOQvzhls1wwKb9ET2yZBPkItWcZD"  # Meta for Developers → WhatsApp → System Users → Generate Token
WHATSAPP_PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"  # Meta for Developers → WhatsApp → Phone Numbers → Phone Number ID
WHATSAPP_RECIPIENT_NUMBERS = [
    "+905432155670",  # Ana acil durum numarası
]

# LLM ve ASR Ayarları
ENABLE_LLM = True  # LLM tabanlı acil durum algılama
ENABLE_ASR = True  # Otomatik Ses Tanıma
ENABLE_ON_DEVICE = True  # On-device (KVKK/GDPR uyumlu) analiz
EMERGENCY_KEYWORDS = [
    "yardım", "acil", "imdat", "nefes", "yangın", "hırsız","deprem", "kaza", "bayıl", "öldürüyorlar", "kan",
    "kırık", "yanık", "zehirlen", "boğul", "çıkış", "kaç", "saldırı", "bıçak", "silah", "acil yardım","acil durum",
    "ölmek istemiyorum", "ölüm", "ölüyorum", "ölüyor", "ölüyorlar", "ölüyorlarım", "ölüyorlarımız", "ölüyorlarınız",
    "ambulans", "itfaiye", "polis", "doktor", "hemşire", "acil yardım", "acil durum", "acil yardım", "acil durum",
    "yardım et", "yardım edin", "nefes alamıyorum"
]

# Bildirim Ayarları
ENABLE_SMS = False  # SMS devre dışı
ENABLE_EMAIL = True # Email aktif
ENABLE_WHATSAPP = True  # WhatsApp aktif
ENABLE_CONSOLE_OUTPUT = True

# Yardım Türleri
YARDIM_TURLERI = {
    "ambulans": "🚑 Ambulans",
    "itfaiye": "🚒 İtfaiye", 
    "polis": "🚔 Polis",
    "acil_yardim": "🚨 Acil Yardım",
    "doktor": "👨‍⚕️ Doktor",
    "hemşire": "👩‍⚕️ Hemşire"
}

# ===== FONKSİYONLAR =====

def test_tarih_saat():
    """Tarih-saat fonksiyonunu test etmek için"""
    simdi = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    return simdi


# ===== WHATSAPP BUSINESS API KURULUM REHBERİ =====
"""
📱 WhatsApp Business API Kurulumu:

1. Meta for Developers'a gidin: https://developers.facebook.com/
2. WhatsApp Business hesabı oluşturun
3. WhatsApp Business API'yi etkinleştirin
4. Access Token alın
5. Phone Number ID alın

Adım Adım:
1. https://developers.facebook.com/ → "Get Started"
2. WhatsApp → "Get Started"
3. Business Account oluşturun
4. WhatsApp Business API → "Set Up"
5. Phone Number ID ve Access Token alın

Örnek:
WHATSAPP_API_TOKEN = "EAA..."
WHATSAPP_PHONE_NUMBER_ID = "123456789"
"""

# ===== LLM TABANLI ACİL DURUM ALGILAMA =====

def categorize_emergency(text):
    """Acil durum türünü kategorize eder"""
    text_lower = text.lower()
    
    categories = {
        "sağlık": ["nefes", "bayıl","deprem" "kalp", "kan","deprem", "kırık", "yanık", "zehirlen", "boğul"],
        "güvenlik": ["hırsız", "saldırı", "bıçak", "silah", "kaç", "çıkış"],
        "yangın": ["yangın", "ateş", "duman", "yanık"],
        "kaza": ["kaza", "düştüm", "çarptı", "trafik"],
        "genel": ["yardım", "acil", "imdat"]
    }
    
    detected_categories = []
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected_categories.append(category)
                break
    
    if detected_categories:
        return detected_categories[0], detected_categories
    else:
        return "genel", ["genel"]

def acil_durum_bildirim_gonder_llm(konum, emergency_text, emergency_category):
    """LLM tabanlı acil durum bildirimi gönderir"""
    simdi = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"🕐 Şu anki tarih-saat: {simdi}")
    print(f" Yardım Kategorisi: {emergency_category}")
    print(f"📍 Konum: {konum}")
    
    # E-posta gönder (LLM tabanlı)
    if ENABLE_EMAIL:
        success, message = acil_bildirim_gonder_llm_email(konum, emergency_text, emergency_category)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    
    # WhatsApp gönder (KVKK uyumlu)
    if ENABLE_WHATSAPP:
        success, message = send_gdpr_compliant_whatsapp(konum, emergency_text, emergency_category)
        if success and message:
            print(f"✅ {message}")


def acil_bildirim_gonder_llm_email(konum, emergency_text, emergency_category):
    """LLM tabanlı e-posta bildirimi gönderir"""
    simdi = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    mesaj = f"""🚨 ACİL DURUM BİLDİRİMİ

📋 Acil Durum Detayları:
• Kategori: {emergency_category.upper()}
• Tarih-Saat: {simdi}
• Konum: {konum}


"""

    msg = MIMEText(mesaj)
    msg["Subject"] = f"🚨 HearMe Acil Durum - {emergency_category.upper()}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True, "E-posta bildirimi başarıyla gönderildi."
    except Exception as e:
        return False, f" E-posta gönderilemedi: {e}"


# ===== KVKK/GDPR UYUMLU ON-DEVICE LLM =====

def initialize_on_device_llm():
    """On-device LLM modelini yükler (KVKK/GDPR uyumlu)"""
    try:
        # Whisper modeli (on-device ASR) - Daha basit yaklaşım
        try:
            import whisper
            # Daha küçük model kullan
            whisper_model = whisper.load_model("tiny")
            
        except Exception as e:
            print(f"❌ Whisper yüklenemedi: {e}")
            print("💡 Whisper yüklemek için: pip install openai-whisper")
            whisper_model = None
        
        # BERT modelini kaldırdık - Sadece Whisper kullan
        classifier = None
        
        # Eğer Whisper yüklenemezse basit yaklaşım kullan
        if not whisper_model:
            print("⚠️ Whisper yüklenemedi, sistem çalışamaz")
            return None, None
        
        return whisper_model, classifier
        
    except Exception as e:
        print(f"❌ On-device LLM yüklenemedi: {e}")
        return None, None

def speech_to_text_on_device(whisper_model):
    """On-device ses tanıma (Canlı mikrofon, geçici dosya yok)"""
    if not whisper_model:
        print("❌ Whisper modeli yüklenemedi")
        return None
        
    try:
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 10  # 10 saniye dinleme

        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                        input=True, frames_per_buffer=CHUNK)

        print(f"🎤 Dinleniyor... ")
        frames = []

        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.int16))

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Tek bir numpy array'e çevir ve normalize et
        audio_np = np.concatenate(frames).astype(np.float32) / 32768.0

        # Whisper ile canlı ses analizi
        result = whisper_model.transcribe(audio_np, language="tr")
        text = result["text"].strip()

        if not text:
            print("⚠️ Whisper hiçbir şey duyamadı")
        return text

    except Exception as e:
        print(f"❌ Ses tanıma hatası: {e}")
        return None


def detect_emergency_on_device(text, classifier):
    """On-device acil durum algılama (GDPR uyumlu)"""
    try:
        # Veri hiçbir yere gönderilmez, sadece yerel analiz
        text_lower = text.lower()
        
        # Anahtar kelime kontrolü (yerel) - Cümle içinde arama
        emergency_score = 0
        detected_keywords = []
        
        # Her anahtar kelimeyi cümle içinde ara
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                emergency_score += 1
                detected_keywords.append(keyword)
                
        # Acil durum tespiti - Daha hassas
        if emergency_score > 0:  # En az bir anahtar kelime bulunduysa
            emergency_probability = emergency_score / len(EMERGENCY_KEYWORDS)
            return True, f"On-device acil durum tespit edildi! Skor: {emergency_probability:.2f}, Anahtar kelimeler: {detected_keywords}"
        
        print("❌ Acil durum tespit edilmedi")
        return False, "On-device acil durum tespit edilmedi"
        
    except Exception as e:
        print(f"❌ Analiz hatası: {e}")
        return False, f" Anliz başarısız: {e}"

def advanced_emergency_detection_gdpr(whisper_model=None, classifier=None):
    """KVKK/GDPR uyumlu gelişmiş acil durum algılama (Sadece Whisper)"""
    
    # Eğer modeller verilmemişse yükle
    if whisper_model is None and classifier is None:
        whisper_model, classifier = initialize_on_device_llm()
    
    # Whisper modeli gerekli
    if not whisper_model:
        print("❌ Modeli yüklenemedi, sistem çalışamaz")
        return False, None
    
    # On-device ses tanıma (Whisper ile)
    text = speech_to_text_on_device(whisper_model)
    
    if text:
        # On-device acil durum analizi
        is_emergency, reason = detect_emergency_on_device(text, classifier)
        
        if is_emergency:
            print(f"🚨 ACİL DURUM TESPİT EDİLDİ!")
            return True, text
        else:
            return False, text
    
    return False, None

def send_gdpr_compliant_whatsapp(konum, message, emergency_category):
    """KVKK uyumlu WhatsApp gönderir"""
    try:
        if WHATSAPP_API_TOKEN == "YOUR_WHATSAPP_API_TOKEN":
            return False, "WhatsApp API token yapılandırılmamış."
        
        basarili_whatsapp = 0
        toplam_whatsapp = len(WHATSAPP_RECIPIENT_NUMBERS)
        
        for numara in WHATSAPP_RECIPIENT_NUMBERS:
            try:
                url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
                    "Content-Type": "application/json"
                }
                data = {
                    "messaging_product": "whatsapp",
                    "to": numara,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }

                response = requests.post(url, headers=headers, json=data)
                response_json = response.json()

                if response.status_code == 200 and response_json.get("messages"):
                    basarili_whatsapp += 1
                    print(f"✅ {numara} numarasına WhatsApp mesajı gönderildi")
                else:
                    print(f"❌ {numara} numarasına WhatsApp mesajı gönderilemedi")

            except Exception as e:
                print(f"⚠️ {numara} numarasına WhatsApp mesajı gönderilemedi: {e}")
        
        if basarili_whatsapp > 0:
            return True, f"{basarili_whatsapp}/{toplam_whatsapp} WhatsApp mesajı gönderildi"
        else:
            return False, ""
            
    except Exception as e:
        return False, ""




