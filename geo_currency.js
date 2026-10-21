/**
 * IdolJapan.store — Privacy-First Currency Locale Auto-Detector
 * File path: /geo_currency.js
 */

(function() {
  const CURRENCY_STORAGE_KEY = 'idoljapan_selected_currency';

  // Map browser language/locale tags to supported store currencies
  const LOCALE_CURRENCY_MAP = {
    'ja': 'JPY',
    'ja-JP': 'JPY',
    'en-GB': 'GBP',
    'en-CA': 'CAD',
    'en-AU': 'AUD',
    'en-NZ': 'AUD',
    'zh-TW': 'TWD',
    'zh-HK': 'HKD',
    'en-HK': 'HKD',
    'ko': 'KRW',
    'ko-KR': 'KRW',
    'en-SG': 'SGD',
    'zh-SG': 'SGD',
    'de': 'EUR',
    'de-DE': 'EUR',
    'fr': 'EUR',
    'fr-FR': 'EUR',
    'it': 'EUR',
    'es': 'EUR',
    'es-ES': 'EUR',
    'nl': 'EUR'
  };

  function autoDetectCurrency() {
    const saved = localStorage.getItem(CURRENCY_STORAGE_KEY);
    if (saved) return saved;

    const languages = navigator.languages || [navigator.language || 'en-US'];
    
    for (const lang of languages) {
      if (LOCALE_CURRENCY_MAP[lang]) {
        return LOCALE_CURRENCY_MAP[lang];
      }
      const primaryCode = lang.split('-')[0].toLowerCase();
      if (LOCALE_CURRENCY_MAP[primaryCode]) {
        return LOCALE_CURRENCY_MAP[primaryCode];
      }
    }

    return 'USD';
  }

  window.IdolGeo = {
    getInitialCurrency: autoDetectCurrency,
    applyAutoCurrency: function() {
      if (!localStorage.getItem(CURRENCY_STORAGE_KEY)) {
        const detected = autoDetectCurrency();
        localStorage.setItem(CURRENCY_STORAGE_KEY, detected);
        const sel = document.getElementById('currency-select');
        if (sel) sel.value = detected;
        return detected;
      }
      return localStorage.getItem(CURRENCY_STORAGE_KEY);
    }
  };
})();
