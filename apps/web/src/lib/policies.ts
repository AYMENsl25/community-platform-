import type { LocaleCode } from "@talaqi/translations";

export const POLICY_VERSION = "2026-08-15-draft";
export const POLICY_SLUGS = [
  "terms",
  "privacy",
  "age",
  "community",
  "organizer",
  "cancellation",
  "moderation",
  "support",
] as const;
export type PolicySlug = (typeof POLICY_SLUGS)[number];

type Copy = { title: string; summary: string; points: readonly string[] };
export type PolicyDocument = Copy & {
  slug: PolicySlug;
  version: string;
  legalDraft: true;
};

const copy: Record<LocaleCode, Record<PolicySlug, Copy>> = {
  en: {
    terms: {
      title: "Terms of use",
      summary: "Rules for using the Talaqi closed beta.",
      points: [
        "Use Talaqi lawfully and provide accurate account information.",
        "Do not misuse private links, attendee data, reports, or platform access.",
        "Talaqi may restrict unsafe accounts or content with an auditable review process.",
      ],
    },
    privacy: {
      title: "Privacy notice",
      summary: "How Talaqi handles closed-beta personal data.",
      points: [
        "We collect account, profile, event, registration, safety, and operational data needed to run the service.",
        "Exact venues and attendee data are limited to authorized audiences.",
        "You may request an export or deletion; deletion has a 30-day recovery window before anonymization.",
      ],
    },
    age: {
      title: "18+ age policy",
      summary: "The closed beta is for adults only.",
      points: [
        "You must be at least 18 years old to create an account or attend through Talaqi.",
        "Accounts that cannot satisfy the age requirement are restricted.",
        "Report suspected child-safety risks immediately through the safety channel.",
      ],
    },
    community: {
      title: "Community rules",
      summary: "Standards for safe and respectful participation.",
      points: [
        "No harassment, hate, threats, fraud, stalking, exploitation, or illegal content.",
        "Respect consent, privacy, venue rules, and organizer instructions.",
        "Use reporting tools honestly; emergencies must go to local emergency services.",
      ],
    },
    organizer: {
      title: "Organizer rules",
      summary: "Responsibilities for clubs and independent organizers.",
      points: [
        "Publish accurate schedules, capacity, accessibility, venue, and cash-reservation terms.",
        "Protect attendee information and never export it without an operational need.",
        "Handle cancellations, cash confirmations, waitlists, and safety reports promptly and fairly.",
      ],
    },
    cancellation: {
      title: "Cancellation and cash rules",
      summary: "How reservations and cancellations work.",
      points: [
        "Each event shows its cancellation cutoff and cash-confirmation deadline before registration.",
        "Expired cash reservations release capacity for deterministic waitlist promotion.",
        "Talaqi does not process online payments or refunds in the MVP.",
      ],
    },
    moderation: {
      title: "Moderation and reporting",
      summary: "How safety and conduct reports are handled.",
      points: [
        "Safety or emergency reports enter the queue immediately; high priority targets acknowledgement within four hours.",
        "Standard reports target acknowledgement within two business days.",
        "Authorized MFA administrators record assignment, decisions, reasons, restoration, and audit evidence.",
      ],
    },
    support: {
      title: "Support",
      summary: "Get help with Talaqi.",
      points: [
        "For account, privacy, organizer, or accessibility help, email support@talaqi.app.",
        "Do not email passwords, session codes, private links, identity documents, or payment data.",
        "For immediate danger, contact local emergency services before reporting to Talaqi.",
      ],
    },
  },
  tr: {
    terms: {
      title: "Kullanım koşulları",
      summary: "Talaqi kapalı betasını kullanma kuralları.",
      points: [
        "Talaqi'yi yasal biçimde kullanın ve doğru hesap bilgileri verin.",
        "Özel bağlantıları, katılımcı verilerini veya platform erişimini kötüye kullanmayın.",
        "Güvenli olmayan hesaplar ve içerikler denetlenebilir bir süreçle kısıtlanabilir.",
      ],
    },
    privacy: {
      title: "Gizlilik bildirimi",
      summary: "Kapalı beta kişisel verilerinin işlenmesi.",
      points: [
        "Hizmet için gerekli hesap, profil, etkinlik, kayıt, güvenlik ve operasyon verileri işlenir.",
        "Kesin konum ve katılımcı bilgileri yalnızca yetkili kişilere gösterilir.",
        "Veri aktarımı veya silme isteyebilirsiniz; silme öncesi 30 günlük kurtarma süresi vardır.",
      ],
    },
    age: {
      title: "18+ yaş politikası",
      summary: "Kapalı beta yalnızca yetişkinler içindir.",
      points: [
        "Hesap açmak ve katılmak için en az 18 yaşında olmalısınız.",
        "Yaş koşulunu karşılayamayan hesaplar kısıtlanır.",
        "Çocuk güvenliği risklerini güvenlik kanalından hemen bildirin.",
      ],
    },
    community: {
      title: "Topluluk kuralları",
      summary: "Güvenli ve saygılı katılım standartları.",
      points: [
        "Taciz, nefret, tehdit, dolandırıcılık, takip veya yasa dışı içerik yasaktır.",
        "Rızaya, gizliliğe, mekan kurallarına ve düzenleyici talimatlarına uyun.",
        "Acil durumlarda önce yerel acil servislere başvurun.",
      ],
    },
    organizer: {
      title: "Düzenleyici kuralları",
      summary: "Kulüp ve bağımsız düzenleyici sorumlulukları.",
      points: [
        "Takvim, kapasite, erişilebilirlik, mekan ve nakit koşullarını doğru yayınlayın.",
        "Katılımcı bilgilerini yalnızca operasyonel ihtiyaç için kullanın.",
        "İptal, nakit onayı, bekleme listesi ve güvenlik raporlarını zamanında yönetin.",
      ],
    },
    cancellation: {
      title: "İptal ve nakit kuralları",
      summary: "Rezervasyon ve iptal işleyişi.",
      points: [
        "İptal ve nakit onay süreleri kayıttan önce gösterilir.",
        "Süresi dolan nakit rezervasyonları kapasiteyi sıradaki kişiye bırakır.",
        "MVP çevrim içi ödeme veya iade işlemez.",
      ],
    },
    moderation: {
      title: "Moderasyon ve bildirim",
      summary: "Güvenlik raporlarının ele alınması.",
      points: [
        "Yüksek öncelikli raporlar için dört saat içinde insan onayı hedeflenir.",
        "Standart raporlar iki iş günü içinde ele alınır.",
        "MFA yetkili yöneticiler karar ve gerekçeleri denetim kaydına alır.",
      ],
    },
    support: {
      title: "Destek",
      summary: "Talaqi ile ilgili yardım alın.",
      points: [
        "Hesap, gizlilik, düzenleyici veya erişilebilirlik yardımı için support@talaqi.app adresine yazın.",
        "Parola, oturum kodu, özel bağlantı veya kimlik belgesi göndermeyin.",
        "Acil tehlikede önce yerel acil servislere başvurun.",
      ],
    },
  },
  fr: {
    terms: {
      title: "Conditions d’utilisation",
      summary: "Règles de la bêta fermée Talaqi.",
      points: [
        "Utilisez Talaqi légalement et fournissez des informations exactes.",
        "N’abusez pas des liens privés, données des participants ou accès administratifs.",
        "Les comptes ou contenus dangereux peuvent être restreints avec une procédure auditée.",
      ],
    },
    privacy: {
      title: "Avis de confidentialité",
      summary: "Traitement des données de la bêta fermée.",
      points: [
        "Nous traitons les données nécessaires aux comptes, événements, inscriptions, sécurité et opérations.",
        "Les lieux exacts et listes de participants sont réservés aux personnes autorisées.",
        "Vous pouvez demander un export ou une suppression avec un délai de récupération de 30 jours.",
      ],
    },
    age: {
      title: "Politique 18+",
      summary: "La bêta fermée est réservée aux adultes.",
      points: [
        "Vous devez avoir au moins 18 ans pour créer un compte ou participer.",
        "Les comptes ne satisfaisant pas cette condition sont restreints.",
        "Signalez immédiatement les risques pour les mineurs par le canal de sécurité.",
      ],
    },
    community: {
      title: "Règles de la communauté",
      summary: "Normes de participation sûre et respectueuse.",
      points: [
        "Le harcèlement, la haine, les menaces, la fraude et les contenus illégaux sont interdits.",
        "Respectez le consentement, la vie privée, le lieu et les consignes de l’organisateur.",
        "En cas d’urgence, contactez d’abord les services d’urgence locaux.",
      ],
    },
    organizer: {
      title: "Règles des organisateurs",
      summary: "Responsabilités des clubs et organisateurs indépendants.",
      points: [
        "Publiez des horaires, capacités, lieux et conditions de réservation exacts.",
        "Protégez les données des participants et limitez les exports au besoin opérationnel.",
        "Traitez rapidement les annulations, confirmations, listes d’attente et signalements.",
      ],
    },
    cancellation: {
      title: "Annulation et espèces",
      summary: "Fonctionnement des réservations et annulations.",
      points: [
        "Les délais d’annulation et de confirmation sont affichés avant l’inscription.",
        "Une réservation expirée libère la place selon l’ordre de la liste d’attente.",
        "Le MVP ne traite ni paiement en ligne ni remboursement.",
      ],
    },
    moderation: {
      title: "Modération et signalement",
      summary: "Traitement des signalements de sécurité.",
      points: [
        "Les signalements prioritaires visent un accusé humain sous quatre heures.",
        "Les signalements standards visent deux jours ouvrés.",
        "Les administrateurs MFA consignent décisions, motifs et restaurations.",
      ],
    },
    support: {
      title: "Assistance",
      summary: "Obtenir de l’aide pour Talaqi.",
      points: [
        "Écrivez à support@talaqi.app pour les comptes, la confidentialité ou l’accessibilité.",
        "N’envoyez jamais mot de passe, code de session, lien privé ou pièce d’identité.",
        "En cas de danger immédiat, contactez d’abord les secours locaux.",
      ],
    },
  },
  ar: {
    terms: {
      title: "شروط الاستخدام",
      summary: "قواعد استخدام النسخة التجريبية المغلقة من تلاقي.",
      points: [
        "استخدم تلاقي بصورة قانونية وقدّم معلومات حساب صحيحة.",
        "لا تُسئ استخدام الروابط الخاصة أو بيانات الحضور أو صلاحيات المنصة.",
        "قد تُقيّد الحسابات أو المحتويات غير الآمنة ضمن مسار موثق.",
      ],
    },
    privacy: {
      title: "إشعار الخصوصية",
      summary: "كيفية التعامل مع البيانات الشخصية في النسخة المغلقة.",
      points: [
        "نعالج بيانات الحساب والفعاليات والتسجيل والسلامة اللازمة لتشغيل الخدمة.",
        "تظهر المواقع الدقيقة وبيانات الحضور للمصرح لهم فقط.",
        "يمكنك طلب نسخة أو حذف؛ وتوجد مهلة استرداد 30 يوماً قبل إخفاء الهوية.",
      ],
    },
    age: {
      title: "سياسة سن 18+",
      summary: "النسخة التجريبية المغلقة للبالغين فقط.",
      points: [
        "يجب أن يكون عمرك 18 عاماً على الأقل لإنشاء حساب أو المشاركة.",
        "تُقيّد الحسابات التي لا تستوفي شرط العمر.",
        "أبلغ فوراً عن مخاطر سلامة الأطفال عبر قناة السلامة.",
      ],
    },
    community: {
      title: "قواعد المجتمع",
      summary: "معايير المشاركة الآمنة والمحترمة.",
      points: [
        "يُحظر التحرش والكراهية والتهديد والاحتيال والملاحقة والمحتوى غير القانوني.",
        "احترم الموافقة والخصوصية وقواعد المكان وتعليمات المنظم.",
        "عند الخطر اتصل أولاً بخدمات الطوارئ المحلية.",
      ],
    },
    organizer: {
      title: "قواعد المنظمين",
      summary: "مسؤوليات الأندية والمنظمين المستقلين.",
      points: [
        "انشر مواعيد وسعة ومكان وشروط حجز دقيقة.",
        "احمِ بيانات الحضور ولا تصدّرها إلا لحاجة تشغيلية.",
        "عالج الإلغاء والتأكيد وقائمة الانتظار وبلاغات السلامة بسرعة وعدل.",
      ],
    },
    cancellation: {
      title: "قواعد الإلغاء والنقد",
      summary: "آلية الحجوزات والإلغاءات.",
      points: [
        "تظهر مهلة الإلغاء وتأكيد النقد قبل التسجيل.",
        "الحجز النقدي المنتهي يحرر المقعد للترقية حسب ترتيب الانتظار.",
        "لا يعالج المنتج الأولي الدفع الإلكتروني أو الاسترداد.",
      ],
    },
    moderation: {
      title: "الإشراف والإبلاغ",
      summary: "كيفية معالجة بلاغات السلامة.",
      points: [
        "يستهدف الإقرار البشري بالبلاغات عالية الأولوية خلال أربع ساعات.",
        "تستهدف البلاغات العادية يومي عمل.",
        "يسجل مديرو MFA القرارات والأسباب والاستعادة في سجل التدقيق.",
      ],
    },
    support: {
      title: "الدعم",
      summary: "احصل على مساعدة بشأن تلاقي.",
      points: [
        "للحساب أو الخصوصية أو الوصول راسل support@talaqi.app.",
        "لا ترسل كلمات المرور أو رموز الجلسة أو الروابط الخاصة أو وثائق الهوية.",
        "عند الخطر المباشر اتصل أولاً بخدمات الطوارئ المحلية.",
      ],
    },
  },
};

export function getPolicy(
  locale: LocaleCode,
  slug: PolicySlug,
): PolicyDocument {
  return {
    ...copy[locale][slug],
    slug,
    version: POLICY_VERSION,
    legalDraft: true,
  };
}
