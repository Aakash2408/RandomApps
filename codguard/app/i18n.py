"""Shopper-facing strings for the confirmation page, by language.

The language comes from the order's `customer_locale` (what the shopper used
at checkout), falling back to English. These translations were written without
a native-speaker review; have each one checked before marketing in that market.
`{name}` and `{order}` are substituted after HTML-escaping.
"""
from __future__ import annotations

import re

RTL = {"ar"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Confirm your order",
        "intro": "Hi {name}, please confirm your cash-on-delivery order <strong>{order}</strong> so the courier can find you.",
        "helps": "To help the courier:",
        "ask.phone": "Share a phone number the courier can reach.",
        "ask.postal": "Check your postal code.",
        "ask.postal_region": "Check that your postal code matches your state or region.",
        "ask.door": "Add your house, flat or building number.",
        "ask.full_address": "Add your full street address.",
        "ask.city": "Add your city.",
        "confirm": "Yes, this address is correct",
        "details_label": "Add details for the courier",
        "details_placeholder": "e.g. Building 4, flat 302, next to the pharmacy",
        "save": "Save and confirm",
        "cancel": "Cancel this order",
        "done": "Done",
        "done.confirmed": "Thanks! Your order is confirmed.",
        "done.updated": "Thanks! We've added your details for the courier.",
        "done.cancel_requested": "Your cancellation request has been sent to the store.",
        "expired_title": "Link expired",
        "expired": "This link has expired or was already used.",
    },
    "ar": {
        "title": "أكّد طلبك",
        "intro": "مرحبًا {name}، يُرجى تأكيد طلبك بالدفع عند الاستلام <strong>{order}</strong> حتى يتمكن المندوب من الوصول إليك.",
        "helps": "لمساعدة المندوب:",
        "ask.phone": "أضف رقم هاتف يمكن للمندوب الاتصال به.",
        "ask.postal": "تحقق من الرمز البريدي.",
        "ask.postal_region": "تأكد من أن الرمز البريدي يطابق منطقتك.",
        "ask.door": "أضف رقم المنزل أو الشقة أو المبنى.",
        "ask.full_address": "أضف عنوانك الكامل.",
        "ask.city": "أضف مدينتك.",
        "confirm": "نعم، هذا العنوان صحيح",
        "details_label": "أضف تفاصيل للمندوب",
        "details_placeholder": "مثال: مبنى 4، شقة 302، بجانب الصيدلية",
        "save": "احفظ وأكّد",
        "cancel": "إلغاء هذا الطلب",
        "done": "تم",
        "done.confirmed": "شكرًا! تم تأكيد طلبك.",
        "done.updated": "شكرًا! أضفنا تفاصيلك للمندوب.",
        "done.cancel_requested": "تم إرسال طلب الإلغاء إلى المتجر.",
        "expired_title": "انتهت صلاحية الرابط",
        "expired": "انتهت صلاحية هذا الرابط أو تم استخدامه بالفعل.",
    },
    "es": {
        "title": "Confirma tu pedido",
        "intro": "Hola {name}, confirma tu pedido contra reembolso <strong>{order}</strong> para que el repartidor pueda encontrarte.",
        "helps": "Para ayudar al repartidor:",
        "ask.phone": "Indica un teléfono en el que el repartidor pueda localizarte.",
        "ask.postal": "Revisa tu código postal.",
        "ask.postal_region": "Comprueba que tu código postal corresponde a tu estado o región.",
        "ask.door": "Añade el número de casa, departamento o edificio.",
        "ask.full_address": "Añade tu dirección completa.",
        "ask.city": "Añade tu ciudad.",
        "confirm": "Sí, la dirección es correcta",
        "details_label": "Añade detalles para el repartidor",
        "details_placeholder": "p. ej. Edificio 4, depto. 302, junto a la farmacia",
        "save": "Guardar y confirmar",
        "cancel": "Cancelar este pedido",
        "done": "Listo",
        "done.confirmed": "¡Gracias! Tu pedido está confirmado.",
        "done.updated": "¡Gracias! Hemos añadido tus detalles para el repartidor.",
        "done.cancel_requested": "Tu solicitud de cancelación se ha enviado a la tienda.",
        "expired_title": "Enlace caducado",
        "expired": "Este enlace ha caducado o ya se ha usado.",
    },
    "pt": {
        "title": "Confirme seu pedido",
        "intro": "Olá {name}, confirme seu pedido com pagamento na entrega <strong>{order}</strong> para que o entregador encontre você.",
        "helps": "Para ajudar o entregador:",
        "ask.phone": "Informe um telefone em que o entregador possa falar com você.",
        "ask.postal": "Confira seu CEP / código postal.",
        "ask.postal_region": "Confira se o código postal corresponde ao seu estado ou região.",
        "ask.door": "Adicione o número da casa, apartamento ou prédio.",
        "ask.full_address": "Adicione seu endereço completo.",
        "ask.city": "Adicione sua cidade.",
        "confirm": "Sim, o endereço está correto",
        "details_label": "Adicione detalhes para o entregador",
        "details_placeholder": "ex.: Prédio 4, apto 302, ao lado da farmácia",
        "save": "Salvar e confirmar",
        "cancel": "Cancelar este pedido",
        "done": "Pronto",
        "done.confirmed": "Obrigado! Seu pedido está confirmado.",
        "done.updated": "Obrigado! Adicionamos seus detalhes para o entregador.",
        "done.cancel_requested": "Seu pedido de cancelamento foi enviado à loja.",
        "expired_title": "Link expirado",
        "expired": "Este link expirou ou já foi usado.",
    },
    "fr": {
        "title": "Confirmez votre commande",
        "intro": "Bonjour {name}, merci de confirmer votre commande payable à la livraison <strong>{order}</strong> pour que le livreur puisse vous trouver.",
        "helps": "Pour aider le livreur :",
        "ask.phone": "Indiquez un numéro où le livreur peut vous joindre.",
        "ask.postal": "Vérifiez votre code postal.",
        "ask.postal_region": "Vérifiez que votre code postal correspond à votre région.",
        "ask.door": "Ajoutez le numéro de maison, d'appartement ou d'immeuble.",
        "ask.full_address": "Ajoutez votre adresse complète.",
        "ask.city": "Ajoutez votre ville.",
        "confirm": "Oui, cette adresse est correcte",
        "details_label": "Ajoutez des précisions pour le livreur",
        "details_placeholder": "ex. Immeuble 4, appt 302, à côté de la pharmacie",
        "save": "Enregistrer et confirmer",
        "cancel": "Annuler cette commande",
        "done": "Terminé",
        "done.confirmed": "Merci ! Votre commande est confirmée.",
        "done.updated": "Merci ! Nous avons ajouté vos précisions pour le livreur.",
        "done.cancel_requested": "Votre demande d'annulation a été envoyée à la boutique.",
        "expired_title": "Lien expiré",
        "expired": "Ce lien a expiré ou a déjà été utilisé.",
    },
    "id": {
        "title": "Konfirmasi pesanan Anda",
        "intro": "Halo {name}, mohon konfirmasi pesanan COD <strong>{order}</strong> agar kurir dapat menemukan Anda.",
        "helps": "Untuk membantu kurir:",
        "ask.phone": "Cantumkan nomor telepon yang bisa dihubungi kurir.",
        "ask.postal": "Periksa kode pos Anda.",
        "ask.postal_region": "Pastikan kode pos sesuai dengan provinsi Anda.",
        "ask.door": "Tambahkan nomor rumah, unit, atau gedung.",
        "ask.full_address": "Tambahkan alamat lengkap Anda.",
        "ask.city": "Tambahkan kota Anda.",
        "confirm": "Ya, alamat ini benar",
        "details_label": "Tambahkan detail untuk kurir",
        "details_placeholder": "mis. Gedung 4, unit 302, sebelah apotek",
        "save": "Simpan dan konfirmasi",
        "cancel": "Batalkan pesanan ini",
        "done": "Selesai",
        "done.confirmed": "Terima kasih! Pesanan Anda sudah dikonfirmasi.",
        "done.updated": "Terima kasih! Detail Anda sudah kami tambahkan untuk kurir.",
        "done.cancel_requested": "Permintaan pembatalan Anda telah dikirim ke toko.",
        "expired_title": "Tautan kedaluwarsa",
        "expired": "Tautan ini sudah kedaluwarsa atau sudah digunakan.",
    },
    "tr": {
        "title": "Siparişinizi onaylayın",
        "intro": "Merhaba {name}, kuryenin sizi bulabilmesi için kapıda ödemeli <strong>{order}</strong> siparişinizi onaylayın.",
        "helps": "Kuryeye yardımcı olmak için:",
        "ask.phone": "Kuryenin size ulaşabileceği bir telefon numarası ekleyin.",
        "ask.postal": "Posta kodunuzu kontrol edin.",
        "ask.postal_region": "Posta kodunuzun ilinizle eşleştiğini kontrol edin.",
        "ask.door": "Bina, daire veya kapı numarasını ekleyin.",
        "ask.full_address": "Açık adresinizi ekleyin.",
        "ask.city": "Şehrinizi ekleyin.",
        "confirm": "Evet, adres doğru",
        "details_label": "Kurye için ayrıntı ekleyin",
        "details_placeholder": "örn. 4 numaralı bina, daire 302, eczanenin yanı",
        "save": "Kaydet ve onayla",
        "cancel": "Bu siparişi iptal et",
        "done": "Tamam",
        "done.confirmed": "Teşekkürler! Siparişiniz onaylandı.",
        "done.updated": "Teşekkürler! Ayrıntılarınızı kurye için ekledik.",
        "done.cancel_requested": "İptal talebiniz mağazaya iletildi.",
        "expired_title": "Bağlantının süresi doldu",
        "expired": "Bu bağlantının süresi dolmuş veya bağlantı zaten kullanılmış.",
    },
}


def lang_for(locale: str | None) -> str:
    """'pt-BR' -> 'pt'; unknown -> 'en'."""
    base = (locale or "").replace("_", "-").split("-")[0].lower()
    return base if base in STRINGS else "en"


def t(lang: str, key: str) -> str:
    return STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"][key]


def intro(lang: str, name_html: str, order_html: str) -> str:
    """Greeting with already-escaped values; drops the name slot cleanly when unknown."""
    text = t(lang, "intro")
    if not name_html:
        text = re.sub(r"\s*\{name\}", "", text)
    return text.replace("{name}", name_html).replace("{order}", order_html)
