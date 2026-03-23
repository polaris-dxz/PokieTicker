import { useTranslation } from '../i18n/useTranslation';

export default function LocaleToggle() {
  const { locale, setLocale, t } = useTranslation();

  return (
    <div className="header-locale" role="group" aria-label="Language">
      <button
        type="button"
        className={`header-locale-btn ${locale === 'en' ? 'active' : ''}`}
        onClick={() => setLocale('en')}
      >
        {t('locale.en')}
      </button>
      <span className="header-locale-sep" aria-hidden>
        |
      </span>
      <button
        type="button"
        className={`header-locale-btn ${locale === 'zh' ? 'active' : ''}`}
        onClick={() => setLocale('zh')}
      >
        {t('locale.zh')}
      </button>
    </div>
  );
}
