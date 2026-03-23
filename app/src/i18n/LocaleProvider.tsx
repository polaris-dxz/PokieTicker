import { useMemo, useState, useEffect, type ReactNode } from 'react';
import { interpolate, messages } from './messages';
import { LocaleContext, type Locale, type TFn } from './locale-context';

const STORAGE_KEY = 'pokieticker-locale';

function readStoredLocale(): Locale {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'en' || v === 'zh') return v;
  } catch {
    /* ignore */
  }
  return 'en';
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readStoredLocale);

  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  }, [locale]);

  const setLocale = (l: Locale) => {
    setLocaleState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
  };

  const t = useMemo(
    (): TFn => (key, vars) => {
      const raw = messages[locale][key] ?? messages.en[key] ?? key;
      return interpolate(raw, vars);
    },
    [locale]
  );

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}
