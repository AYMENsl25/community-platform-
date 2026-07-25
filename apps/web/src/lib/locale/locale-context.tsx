"use client";

import {
  applyDocumentLocale,
  getLocaleDirection,
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type LocaleContextValue = {
  direction: "ltr" | "rtl";
  locale: LocaleCode;
  setLocale: (locale: LocaleCode) => void;
  t: (key: TranslationKey) => string;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

export function LocaleProvider({
  children,
  initialLocale,
}: {
  children: ReactNode;
  initialLocale: LocaleCode;
}) {
  const router = useRouter();
  const [locale, updateLocale] = useState(initialLocale);
  const setLocale = useCallback(
    (nextLocale: LocaleCode) => {
      applyDocumentLocale(nextLocale);
      document.cookie = `talaqi_locale=${nextLocale}; Path=/; Max-Age=31536000; SameSite=Lax`;
      updateLocale(nextLocale);
      router.refresh();
    },
    [router],
  );
  const value = useMemo<LocaleContextValue>(
    () => ({
      direction: getLocaleDirection(locale),
      locale,
      setLocale,
      t: (key) => translate(locale, key),
    }),
    [locale, setLocale],
  );
  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useLocale must be used within LocaleProvider");
  return context;
}
