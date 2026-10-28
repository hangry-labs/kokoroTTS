// SPDX-License-Identifier: Apache-2.0. Keep the gallery and site locales in sync.
// The standalone player owns its translations and speech-language filters.
const requestedGalleryLanguage = new URLSearchParams(location.search).get('lang')?.toLowerCase();
document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.querySelector('.gallery-content');
  const selector = document.querySelector('#site-language');
  if (!gallery || !selector) return;
  const reflectLanguage = () => {
    gallery.lang = currentPageLanguage;
    document.querySelector('#translation-notice').hidden = true;
  };
  const selectLanguage = () => {
    const language = selector.value;
    if (PAGE_LANGUAGES[language]) setLanguageFilter(PAGE_LANGUAGES[language]);
    else if (TRANSLATIONS[language]) { setLanguageFilter('all'); translatePage(language); }
    reflectLanguage();
  };
  // Preserve direct Studio links for speech languages without a README locale.
  if (!requestedGalleryLanguage || [...selector.options].some(option => option.value === requestedGalleryLanguage)) selectLanguage();
  else reflectLanguage();
  selector.addEventListener('change', selectLanguage);
  for (const button of gallery.querySelectorAll('[data-language-value]')) {
    button.addEventListener('click', reflectLanguage);
  }
});
