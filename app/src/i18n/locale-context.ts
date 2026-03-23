import { createContext } from 'react';
import type { MessageKey } from './messages';

export type Locale = 'en' | 'zh';

export type TFn = (key: MessageKey, vars?: Record<string, string | number>) => string;

export const LocaleContext = createContext<{
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: TFn;
} | null>(null);
