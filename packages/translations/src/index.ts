export const LOCALE_CODES = ["en", "tr", "fr", "ar"] as const;
export type LocaleCode = (typeof LOCALE_CODES)[number];

const englishDictionary = {
  "brand.name": "Talaqi",
  "shell.skipToContent": "Skip to main content",
  "shell.navigation.primary": "Primary navigation",
  "shell.navigation.workspace": "Workspace navigation",
  "shell.navigation.home": "Home",
  "shell.navigation.community": "Community",
  "shell.navigation.about": "About",
  "shell.navigation.overview": "Overview",
  "shell.navigation.calendar": "Calendar",
  "shell.navigation.clubs": "Clubs",
  "shell.navigation.events": "Events",
  "shell.navigation.review": "Review queue",
  "shell.navigation.settings": "Settings",
  "shell.footer.tagline": "Community, thoughtfully connected.",
  "shell.role.member": "Member workspace",
  "shell.role.organizer": "Organizer workspace",
  "shell.role.admin": "Platform administration",
  "home.eyebrow": "A place to meet around shared interests",
  "home.title": "Find your people. Build something together.",
  "home.lead":
    "Talaqi is creating a welcoming home for local clubs and independent events.",
  "home.primaryAction": "Explore the foundation",
  "home.secondaryAction": "Learn about Talaqi",
  "home.preview.title": "Designed for every community",
  "home.preview.body":
    "A clear, accessible foundation that works across languages, screens, and ways of navigating.",
} as const;

export type TranslationKey = keyof typeof englishDictionary;
type Dictionary = Record<TranslationKey, string>;

const turkishDictionary: Dictionary = {
  "brand.name": "Talaqi",
  "shell.skipToContent": "Ana içeriğe geç",
  "shell.navigation.primary": "Ana gezinme",
  "shell.navigation.workspace": "Çalışma alanı gezinmesi",
  "shell.navigation.home": "Ana sayfa",
  "shell.navigation.community": "Topluluk",
  "shell.navigation.about": "Hakkında",
  "shell.navigation.overview": "Genel bakış",
  "shell.navigation.calendar": "Takvim",
  "shell.navigation.clubs": "Kulüpler",
  "shell.navigation.events": "Etkinlikler",
  "shell.navigation.review": "İnceleme sırası",
  "shell.navigation.settings": "Ayarlar",
  "shell.footer.tagline": "Topluluk, özenle bir arada.",
  "shell.role.member": "Üye çalışma alanı",
  "shell.role.organizer": "Organizatör çalışma alanı",
  "shell.role.admin": "Platform yönetimi",
  "home.eyebrow": "Ortak ilgi alanları etrafında buluşma yeri",
  "home.title": "İnsanlarını bul. Birlikte bir şey inşa et.",
  "home.lead":
    "Talaqi, yerel kulüpler ve bağımsız etkinlikler için sıcak bir yuva oluşturuyor.",
  "home.primaryAction": "Temeli keşfet",
  "home.secondaryAction": "Talaqi hakkında bilgi al",
  "home.preview.title": "Her topluluk için tasarlandı",
  "home.preview.body":
    "Diller, ekranlar ve gezinme biçimleri arasında çalışan açık ve erişilebilir bir temel.",
};

const frenchDictionary: Dictionary = {
  "brand.name": "Talaqi",
  "shell.skipToContent": "Aller au contenu principal",
  "shell.navigation.primary": "Navigation principale",
  "shell.navigation.workspace": "Navigation de l’espace de travail",
  "shell.navigation.home": "Accueil",
  "shell.navigation.community": "Communauté",
  "shell.navigation.about": "À propos",
  "shell.navigation.overview": "Vue d’ensemble",
  "shell.navigation.calendar": "Calendrier",
  "shell.navigation.clubs": "Clubs",
  "shell.navigation.events": "Événements",
  "shell.navigation.review": "File de révision",
  "shell.navigation.settings": "Paramètres",
  "shell.footer.tagline": "La communauté, reliée avec attention.",
  "shell.role.member": "Espace membre",
  "shell.role.organizer": "Espace organisateur",
  "shell.role.admin": "Administration de la plateforme",
  "home.eyebrow": "Un lieu de rencontre autour d’intérêts communs",
  "home.title": "Trouvez votre communauté. Construisez ensemble.",
  "home.lead":
    "Talaqi crée un espace accueillant pour les clubs locaux et les événements indépendants.",
  "home.primaryAction": "Explorer la fondation",
  "home.secondaryAction": "Découvrir Talaqi",
  "home.preview.title": "Conçu pour chaque communauté",
  "home.preview.body":
    "Une fondation claire et accessible, adaptée aux langues, aux écrans et aux modes de navigation.",
};

const arabicDictionary: Dictionary = {
  "brand.name": "تلاقي",
  "shell.skipToContent": "الانتقال إلى المحتوى الرئيسي",
  "shell.navigation.primary": "التنقل الرئيسي",
  "shell.navigation.workspace": "التنقل في مساحة العمل",
  "shell.navigation.home": "الرئيسية",
  "shell.navigation.community": "المجتمع",
  "shell.navigation.about": "عن تلاقي",
  "shell.navigation.overview": "نظرة عامة",
  "shell.navigation.calendar": "التقويم",
  "shell.navigation.clubs": "النوادي",
  "shell.navigation.events": "الفعاليات",
  "shell.navigation.review": "قائمة المراجعة",
  "shell.navigation.settings": "الإعدادات",
  "shell.footer.tagline": "مجتمع يجمعنا بعناية.",
  "shell.role.member": "مساحة العضو",
  "shell.role.organizer": "مساحة المنظم",
  "shell.role.admin": "إدارة المنصة",
  "home.eyebrow": "مكان للقاء حول الاهتمامات المشتركة",
  "home.title": "اعثر على مجتمعك. وابنوا شيئًا معًا.",
  "home.lead": "تلاقي يبني مساحة مرحبة للنوادي المحلية والفعاليات المستقلة.",
  "home.primaryAction": "استكشف الأساس",
  "home.secondaryAction": "تعرّف على تلاقي",
  "home.preview.title": "مصمم لكل مجتمع",
  "home.preview.body":
    "أساس واضح ومتاح يعمل عبر اللغات والشاشات وطرق التنقل المختلفة.",
};

export const dictionaries = {
  en: englishDictionary,
  tr: turkishDictionary,
  fr: frenchDictionary,
  ar: arabicDictionary,
} satisfies Record<LocaleCode, Dictionary>;

export function translate(locale: LocaleCode, key: TranslationKey): string {
  return dictionaries[locale][key];
}

export function getLocaleDirection(locale: LocaleCode): "ltr" | "rtl" {
  return locale === "ar" ? "rtl" : "ltr";
}
