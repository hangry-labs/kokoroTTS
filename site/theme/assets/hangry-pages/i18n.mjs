// SPDX-License-Identifier: Apache-2.0. Copyright 2026 Hangry Labs.
export const LANGUAGE_NAMES = {en:'English',nb:'Norsk bokmål',pl:'Polski',ja:'日本語',zh:'简体中文',es:'Español'};
export const MESSAGES = {
  en: {overview:'Overview',examples:'Listen to examples',documentation:'Documentation',language:'Language',sections:'On this page',project:'Project',skip:'Skip to content',copy:'Copy',copied:'Copied',copyCode:'Copy code',copiedStatus:'Code copied to clipboard.',selectStatus:'Code selected. Use your copy shortcut.',source:'View source',tagline:'Useful tools, easy to run',footer:'Local tools. Your machine. Your work.',table:'Scrollable table',fallback:'This page is shown in {language}; a translation is not available yet.'},
  nb: {overview:'Oversikt',examples:'Lytt til eksempler',documentation:'Dokumentasjon',language:'Språk',sections:'På denne siden',project:'Prosjekt',skip:'Hopp til innhold',copy:'Kopier',copied:'Kopiert',copyCode:'Kopier kode',copiedStatus:'Koden er kopiert til utklippstavlen.',selectStatus:'Koden er markert. Bruk hurtigtasten for å kopiere.',source:'Vis kilde',tagline:'Nyttige verktøy, enkle å kjøre',footer:'Lokale verktøy. Din maskin. Ditt arbeid.',table:'Tabell med rulling',fallback:'Denne siden vises på {language}; en oversettelse er ikke tilgjengelig ennå.'},
  pl: {overview:'Przegląd',examples:'Posłuchaj przykładów',documentation:'Dokumentacja',language:'Język',sections:'Na tej stronie',project:'Projekt',skip:'Przejdź do treści',copy:'Kopiuj',copied:'Skopiowano',copyCode:'Kopiuj kod',copiedStatus:'Kod skopiowano do schowka.',selectStatus:'Kod zaznaczono. Użyj skrótu kopiowania.',source:'Zobacz źródło',tagline:'Przydatne narzędzia, łatwe uruchomienie',footer:'Lokalne narzędzia. Twój komputer. Twoja praca.',table:'Tabela z przewijaniem',fallback:'Ta strona jest wyświetlana w języku {language}; tłumaczenie nie jest jeszcze dostępne.'},
  ja: {overview:'概要',examples:'音声サンプル',documentation:'ドキュメント',language:'言語',sections:'このページの内容',project:'プロジェクト',skip:'本文へ移動',copy:'コピー',copied:'コピー済み',copyCode:'コードをコピー',copiedStatus:'コードをクリップボードにコピーしました。',selectStatus:'コードを選択しました。コピーのショートカットを使用してください。',source:'ソースを見る',tagline:'便利なツールを、手軽に実行',footer:'ローカルのツール。あなたのマシン。あなたの作業。',table:'スクロール可能な表',fallback:'このページは {language} で表示されています。選択した言語への翻訳はまだありません。'},
  zh: {overview:'概览',examples:'收听语音示例',documentation:'文档',language:'语言',sections:'本页目录',project:'项目',skip:'跳转到正文',copy:'复制',copied:'已复制',copyCode:'复制代码',copiedStatus:'代码已复制到剪贴板。',selectStatus:'代码已选中，请使用复制快捷键。',source:'查看源文件',tagline:'实用工具，轻松运行',footer:'本地工具。你的电脑。你的创作。',table:'可滚动表格',fallback:'此页面目前以 {language} 显示，尚无所选语言的译文。'},
  es: {overview:'Resumen',examples:'Escuchar ejemplos',documentation:'Documentación',language:'Idioma',sections:'En esta página',project:'Proyecto',skip:'Ir al contenido',copy:'Copiar',copied:'Copiado',copyCode:'Copiar código',copiedStatus:'Código copiado al portapapeles.',selectStatus:'Código seleccionado. Usa el atajo para copiar.',source:'Ver código fuente',tagline:'Herramientas útiles, fáciles de ejecutar',footer:'Herramientas locales. Tu equipo. Tu trabajo.',table:'Tabla desplazable',fallback:'Esta página se muestra en {language}; la traducción aún no está disponible.'},
};

export function chooseLanguage({query,page,stored,languages,defaultLanguage='en'}) {
  if (languages.includes(query)) return query;
  if (page !== defaultLanguage && languages.includes(page)) return page;
  return languages.includes(stored) ? stored : defaultLanguage;
}

// Group translated Markdown with its original, without copying document content.
export function createRouter(pageMap,{base='',origin,siteUrl,languages=['en'],defaultLanguage='en'}) {
  const byPath = new Map(), bySource = new Map(), groups = new Map();
  const canonicalOrigin = siteUrl ? new URL(siteUrl).origin : origin;
  for (const [source,path] of Object.entries(pageMap)) {
    const suffix = languages.find(code => source.endsWith(`.${code}.md`));
    const key = suffix ? source.slice(0,-suffix.length-4)+'.md' : source;
    const record = {source,path,key,language:suffix || defaultLanguage};
    bySource.set(source,record); byPath.set(path,record);
    if (!groups.has(key)) groups.set(key,new Map());
    groups.get(key).set(record.language,record);
  }
  const resolve = (record,language) => groups.get(record.key)?.get(language) || groups.get(record.key)?.get(defaultLanguage) || record;
  function url(record,language,from) {
    const result = new URL(record.path,origin);
    if (from) { result.search = from.search; if (from.pathname === record.path) result.hash = from.hash; }
    result.searchParams.set('lang',language);
    return result;
  }
  function rewrite(href,from,language,{explicitOverview=false}={}) {
    const target = new URL(href,from);
    if (![origin,canonicalOrigin].includes(target.origin) || !target.pathname.startsWith(base+'/')) return null;
    const record = bySource.get(target.pathname) || byPath.get(target.pathname);
    if (!record) return null;
    const query = target.searchParams.get('lang');
    const isOverview = resolve(record,defaultLanguage).path === base+'/';
    const desired = languages.includes(query) ? query : (record.language !== defaultLanguage || (explicitOverview && isOverview)) ? record.language : language;
    const destination = resolve(record,desired);
    const result = url(destination,desired,target);
    // Markdown paths are aliases of their rendered page; retain their fragments.
    if (destination === record && bySource.has(target.pathname)) result.hash = target.hash;
    return result;
  }
  return {byPath,bySource,resolve,url,rewrite};
}
