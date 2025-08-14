import os
# TensorFlow uyarılarını kapat
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Uyarıları kapat
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*not initialized from the model checkpoint.*")
warnings.filterwarnings("ignore", message=".*You should probably TRAIN this model.*")
warnings.filterwarnings("ignore", message=".*return_all_scores.*")
warnings.filterwarnings("ignore", message=".*resume_download.*")
warnings.filterwarnings("ignore", message=".*BertForSequenceClassification.*")
warnings.filterwarnings("ignore", message=".*newly initialized.*")
warnings.filterwarnings("ignore", message=".*down-stream task.*")
warnings.filterwarnings("ignore", message=".*predictions and inference.*")

# Tüm uyarıları kapat
warnings.simplefilter("ignore")

from location_information import konum_bul
from emergancy_information import (
    advanced_emergency_detection_gdpr, 
    acil_durum_bildirim_gonder_llm,
    categorize_emergency,
    initialize_on_device_llm
)

def uygulama():
    # Modelleri bir kez yükle
    whisper_model, classifier = initialize_on_device_llm()
    
    try:
        # LLM tabanlı acil durum algılama (10 saniye)
        is_emergency, emergency_text = advanced_emergency_detection_gdpr(whisper_model, classifier)
        
        if is_emergency and emergency_text:
            konum = konum_bul()
            
            # Acil durum kategorisini belirle
            emergency_category, all_categories = categorize_emergency(emergency_text)
            
            acil_durum_bildirim_gonder_llm(konum, emergency_text, emergency_category)
                
    except KeyboardInterrupt:
        print("Uygulama kapatılıyor...")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        print("Uygulama kapatılıyor...")

if __name__ == "__main__":
    uygulama()


