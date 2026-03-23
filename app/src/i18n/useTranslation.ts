import { useContext } from 'react';
import { LocaleContext } from './locale-context';

export function useTranslation() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error('useTranslation must be used within LocaleProvider');
  return ctx;
}
