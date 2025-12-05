"""
Document Translation Service

Provides multi-language support for shipping documents.
Supports bilingual documents and RTL languages.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages"""
    EN = "en"     # English
    AR = "ar"     # Arabic (RTL)
    ZH = "zh"     # Chinese (Simplified)
    ZH_TW = "zh_TW"  # Chinese (Traditional)
    ES = "es"     # Spanish
    FR = "fr"     # French
    DE = "de"     # German
    PT = "pt"     # Portuguese
    TR = "tr"     # Turkish
    HI = "hi"     # Hindi
    BN = "bn"     # Bengali
    UR = "ur"     # Urdu (RTL)


RTL_LANGUAGES = {Language.AR, Language.UR}


@dataclass
class TranslationEntry:
    """A translation entry with context"""
    key: str
    en: str
    translations: Dict[str, str]
    context: Optional[str] = None  # Document context for disambiguation


# Standard document field translations
FIELD_TRANSLATIONS: Dict[str, TranslationEntry] = {
    # Document Headers
    "commercial_invoice": TranslationEntry(
        key="commercial_invoice",
        en="COMMERCIAL INVOICE",
        translations={
            "ar": "فاتورة تجارية",
            "zh": "商业发票",
            "zh_TW": "商業發票",
            "es": "FACTURA COMERCIAL",
            "fr": "FACTURE COMMERCIALE",
            "de": "HANDELSRECHNUNG",
            "tr": "TİCARİ FATURA",
            "hi": "वाणिज्यिक चालान",
            "bn": "বাণিজ্যিক চালান",
            "ur": "تجارتی رسید",
        }
    ),
    "packing_list": TranslationEntry(
        key="packing_list",
        en="PACKING LIST",
        translations={
            "ar": "قائمة التعبئة",
            "zh": "装箱单",
            "zh_TW": "裝箱單",
            "es": "LISTA DE EMPAQUE",
            "fr": "LISTE DE COLISAGE",
            "de": "PACKLISTE",
            "tr": "AMBALAJ LİSTESİ",
            "hi": "पैकिंग सूची",
            "bn": "প্যাকিং তালিকা",
            "ur": "پیکنگ فہرست",
        }
    ),
    "certificate_of_origin": TranslationEntry(
        key="certificate_of_origin",
        en="CERTIFICATE OF ORIGIN",
        translations={
            "ar": "شهادة المنشأ",
            "zh": "原产地证书",
            "zh_TW": "原產地證書",
            "es": "CERTIFICADO DE ORIGEN",
            "fr": "CERTIFICAT D'ORIGINE",
            "de": "URSPRUNGSZEUGNIS",
            "tr": "MENŞE ŞAHADETNAMESİ",
            "hi": "मूल प्रमाण पत्र",
            "bn": "উৎপত্তি সনদ",
            "ur": "سرٹیفیکیٹ آف اوریجن",
        }
    ),
    "bill_of_exchange": TranslationEntry(
        key="bill_of_exchange",
        en="BILL OF EXCHANGE",
        translations={
            "ar": "كمبيالة",
            "zh": "汇票",
            "zh_TW": "匯票",
            "es": "LETRA DE CAMBIO",
            "fr": "LETTRE DE CHANGE",
            "de": "WECHSEL",
            "tr": "POLİÇE",
            "hi": "विनिमय पत्र",
            "bn": "বিনিময় বিল",
            "ur": "حوالہ نامہ",
        }
    ),
    
    # Common Fields
    "invoice_number": TranslationEntry(
        key="invoice_number",
        en="Invoice No.",
        translations={
            "ar": "رقم الفاتورة",
            "zh": "发票号",
            "zh_TW": "發票號",
            "es": "Nº de Factura",
            "fr": "N° de Facture",
            "de": "Rechnungs-Nr.",
            "tr": "Fatura No",
        }
    ),
    "date": TranslationEntry(
        key="date",
        en="Date",
        translations={
            "ar": "التاريخ",
            "zh": "日期",
            "es": "Fecha",
            "fr": "Date",
            "de": "Datum",
            "tr": "Tarih",
        }
    ),
    "beneficiary": TranslationEntry(
        key="beneficiary",
        en="Beneficiary",
        translations={
            "ar": "المستفيد",
            "zh": "受益人",
            "es": "Beneficiario",
            "fr": "Bénéficiaire",
            "de": "Begünstigter",
            "tr": "Lehtar",
        }
    ),
    "applicant": TranslationEntry(
        key="applicant",
        en="Applicant",
        translations={
            "ar": "مقدم الطلب",
            "zh": "申请人",
            "es": "Solicitante",
            "fr": "Demandeur",
            "de": "Antragsteller",
            "tr": "Başvuru Sahibi",
        }
    ),
    "consignee": TranslationEntry(
        key="consignee",
        en="Consignee",
        translations={
            "ar": "المرسل إليه",
            "zh": "收货人",
            "es": "Consignatario",
            "fr": "Destinataire",
            "de": "Empfänger",
            "tr": "Alıcı",
        }
    ),
    "notify_party": TranslationEntry(
        key="notify_party",
        en="Notify Party",
        translations={
            "ar": "الجهة المخطرة",
            "zh": "通知方",
            "es": "Parte a Notificar",
            "fr": "Partie à Notifier",
            "de": "Zu benachrichtigen",
            "tr": "İhbar Tarafı",
        }
    ),
    "port_of_loading": TranslationEntry(
        key="port_of_loading",
        en="Port of Loading",
        translations={
            "ar": "ميناء الشحن",
            "zh": "装货港",
            "es": "Puerto de Carga",
            "fr": "Port de Chargement",
            "de": "Verladehafen",
            "tr": "Yükleme Limanı",
        }
    ),
    "port_of_discharge": TranslationEntry(
        key="port_of_discharge",
        en="Port of Discharge",
        translations={
            "ar": "ميناء التفريغ",
            "zh": "卸货港",
            "es": "Puerto de Descarga",
            "fr": "Port de Déchargement",
            "de": "Entladehafen",
            "tr": "Boşaltma Limanı",
        }
    ),
    "country_of_origin": TranslationEntry(
        key="country_of_origin",
        en="Country of Origin",
        translations={
            "ar": "بلد المنشأ",
            "zh": "原产国",
            "es": "País de Origen",
            "fr": "Pays d'Origine",
            "de": "Ursprungsland",
            "tr": "Menşe Ülkesi",
        }
    ),
    "description_of_goods": TranslationEntry(
        key="description_of_goods",
        en="Description of Goods",
        translations={
            "ar": "وصف البضائع",
            "zh": "货物描述",
            "es": "Descripción de Mercancías",
            "fr": "Description des Marchandises",
            "de": "Warenbeschreibung",
            "tr": "Mal Tanımı",
        }
    ),
    "quantity": TranslationEntry(
        key="quantity",
        en="Quantity",
        translations={
            "ar": "الكمية",
            "zh": "数量",
            "es": "Cantidad",
            "fr": "Quantité",
            "de": "Menge",
            "tr": "Miktar",
        }
    ),
    "unit_price": TranslationEntry(
        key="unit_price",
        en="Unit Price",
        translations={
            "ar": "سعر الوحدة",
            "zh": "单价",
            "es": "Precio Unitario",
            "fr": "Prix Unitaire",
            "de": "Stückpreis",
            "tr": "Birim Fiyat",
        }
    ),
    "total_amount": TranslationEntry(
        key="total_amount",
        en="Total Amount",
        translations={
            "ar": "المبلغ الإجمالي",
            "zh": "总金额",
            "es": "Importe Total",
            "fr": "Montant Total",
            "de": "Gesamtbetrag",
            "tr": "Toplam Tutar",
        }
    ),
    "gross_weight": TranslationEntry(
        key="gross_weight",
        en="Gross Weight",
        translations={
            "ar": "الوزن الإجمالي",
            "zh": "毛重",
            "es": "Peso Bruto",
            "fr": "Poids Brut",
            "de": "Bruttogewicht",
            "tr": "Brüt Ağırlık",
        }
    ),
    "net_weight": TranslationEntry(
        key="net_weight",
        en="Net Weight",
        translations={
            "ar": "الوزن الصافي",
            "zh": "净重",
            "es": "Peso Neto",
            "fr": "Poids Net",
            "de": "Nettogewicht",
            "tr": "Net Ağırlık",
        }
    ),
    "shipping_marks": TranslationEntry(
        key="shipping_marks",
        en="Shipping Marks",
        translations={
            "ar": "علامات الشحن",
            "zh": "唛头",
            "es": "Marcas de Envío",
            "fr": "Marques d'Expédition",
            "de": "Versandmarkierungen",
            "tr": "Nakliye İşaretleri",
        }
    ),
    
    # Certifications
    "we_certify": TranslationEntry(
        key="we_certify",
        en="We hereby certify that the above particulars are true and correct",
        translations={
            "ar": "نشهد بموجب هذا أن البيانات المذكورة أعلاه صحيحة ودقيقة",
            "zh": "特此证明以上内容真实正确",
            "es": "Por la presente certificamos que los datos anteriores son verdaderos y correctos",
            "fr": "Nous certifions par la présente que les informations ci-dessus sont vraies et correctes",
            "de": "Hiermit bestätigen wir, dass die obigen Angaben wahrheitsgemäß und korrekt sind",
            "tr": "Yukarıdaki bilgilerin doğru ve gerçek olduğunu beyan ederiz",
        }
    ),
    "authorized_signature": TranslationEntry(
        key="authorized_signature",
        en="Authorized Signature",
        translations={
            "ar": "توقيع مفوض",
            "zh": "授权签字",
            "es": "Firma Autorizada",
            "fr": "Signature Autorisée",
            "de": "Autorisierte Unterschrift",
            "tr": "Yetkili İmza",
        }
    ),
}


class DocumentTranslationService:
    """
    Service for translating document content.
    
    Supports:
    - Single language documents
    - Bilingual documents (side-by-side or English with translation below)
    - RTL language support (Arabic, Urdu)
    """
    
    def __init__(self):
        self._translations = FIELD_TRANSLATIONS
    
    def translate(
        self,
        key: str,
        language: str,
        fallback_to_english: bool = True
    ) -> str:
        """
        Translate a key to the target language.
        
        Args:
            key: Translation key
            language: Target language code
            fallback_to_english: If True, return English if translation not found
        
        Returns:
            Translated string
        """
        entry = self._translations.get(key)
        if not entry:
            return key  # Return key as-is if not found
        
        # Check for exact language match
        if language in entry.translations:
            return entry.translations[language]
        
        # Check for language family (e.g., "zh" from "zh_TW")
        base_lang = language.split("_")[0]
        if base_lang in entry.translations:
            return entry.translations[base_lang]
        
        # Fallback to English
        if fallback_to_english:
            return entry.en
        
        return key
    
    def get_bilingual_text(
        self,
        key: str,
        primary_language: str,
        secondary_language: str = "en"
    ) -> Tuple[str, str]:
        """
        Get text in two languages for bilingual documents.
        
        Returns:
            Tuple of (primary_text, secondary_text)
        """
        primary = self.translate(key, primary_language)
        secondary = self.translate(key, secondary_language)
        return (primary, secondary)
    
    def is_rtl(self, language: str) -> bool:
        """Check if language is right-to-left"""
        try:
            return Language(language) in RTL_LANGUAGES
        except ValueError:
            return language.lower() in {"ar", "ur", "he", "fa"}
    
    def get_font_for_language(self, language: str) -> str:
        """
        Get appropriate font family for language.
        
        Returns font name that supports the language characters.
        """
        if language in ["ar", "ur"]:
            return "Amiri"  # Arabic font
        elif language in ["zh", "zh_TW"]:
            return "Noto Sans SC"  # Chinese font
        elif language in ["hi", "bn"]:
            return "Noto Sans Devanagari"
        elif language in ["ja"]:
            return "Noto Sans JP"
        elif language in ["ko"]:
            return "Noto Sans KR"
        else:
            return "Helvetica"  # Default
    
    def translate_document_fields(
        self,
        document_data: Dict[str, Any],
        field_mappings: List[str],
        target_language: str
    ) -> Dict[str, Any]:
        """
        Translate specific fields in document data.
        
        This translates the field labels, not the values.
        """
        translated = document_data.copy()
        
        for field in field_mappings:
            translated[f"{field}_label"] = self.translate(field, target_language)
        
        return translated
    
    def list_supported_languages(self) -> List[Dict[str, str]]:
        """List all supported languages"""
        return [
            {"code": "en", "name": "English", "native": "English", "rtl": False},
            {"code": "ar", "name": "Arabic", "native": "العربية", "rtl": True},
            {"code": "zh", "name": "Chinese (Simplified)", "native": "简体中文", "rtl": False},
            {"code": "zh_TW", "name": "Chinese (Traditional)", "native": "繁體中文", "rtl": False},
            {"code": "es", "name": "Spanish", "native": "Español", "rtl": False},
            {"code": "fr", "name": "French", "native": "Français", "rtl": False},
            {"code": "de", "name": "German", "native": "Deutsch", "rtl": False},
            {"code": "tr", "name": "Turkish", "native": "Türkçe", "rtl": False},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी", "rtl": False},
            {"code": "bn", "name": "Bengali", "native": "বাংলা", "rtl": False},
            {"code": "ur", "name": "Urdu", "native": "اردو", "rtl": True},
        ]
    
    def add_translation(self, entry: TranslationEntry):
        """Add or update a translation entry"""
        self._translations[entry.key] = entry


# Singleton
_translation_service: Optional[DocumentTranslationService] = None


def get_translation_service() -> DocumentTranslationService:
    global _translation_service
    if _translation_service is None:
        _translation_service = DocumentTranslationService()
    return _translation_service

