// SPDX-License-Identifier: Apache-2.0. Copyright 2026 Hangry Labs.
import {LANGUAGE_NAMES, MESSAGES, chooseLanguage, createRouter} from './i18n.mjs';

(() => {
  const content = document.querySelector('#main-content article');
  if (!content) return;
  // README HTML anchors remain useful on GitHub; map them to rendered pages here.
  const pages = JSON.parse(document.querySelector('#hangry-page-map').textContent);
  const base = document.body.dataset.baseurl || '';
  const defaultLanguage = document.body.dataset.defaultLang || 'en';
  const configured = JSON.parse(document.querySelector('#hangry-language-config').textContent);
  const languages = Array.isArray(configured) && configured.length ? configured : [defaultLanguage];
  const router = createRouter(pages,{base,origin:location.origin,siteUrl:document.body.dataset.siteUrl,languages,defaultLanguage});
  const current = router.bySource.get(document.body.dataset.pagePath);
  const storageKey = 'hangry-pages-language:'+base;
  let stored;
  try { stored = localStorage.getItem(storageKey); } catch { /* Storage can be disabled. */ }
  let language = chooseLanguage({query:new URL(location.href).searchParams.get('lang'),page:current?.language,stored,languages,defaultLanguage});
  const text = key => (MESSAGES[language] || MESSAGES.en)[key] || MESSAGES.en[key];
  const selector = document.querySelector('#site-language');

  function applyLanguage() {
    const url = new URL(location.href);
    if (current) {
      const target = router.resolve(current,language);
      if (target.path !== location.pathname) {
        location.replace(router.url(target,language,url));
        return false;
      }
      document.documentElement.lang = current.language;
    }
    url.searchParams.set('lang',language);
    history.replaceState(null,'',url);
    try { localStorage.setItem(storageKey,language); } catch { /* Navigation still works. */ }
    for (const element of document.querySelectorAll('[data-site-text]')) element.textContent = text(element.dataset.siteText);
    for (const element of document.querySelectorAll('.site-header,.section-sidebar,.site-footer')) element.lang = language;
    for (const button of document.querySelectorAll('.copy-code')) { button.textContent = text('copy'); button.setAttribute('aria-label',text('copyCode')); button.lang = language; }
    for (const table of document.querySelectorAll('.table-scroll')) table.setAttribute('aria-label',text('table'));
    document.querySelector('.site-navigation').setAttribute('aria-label',text('project'));
    document.querySelector('#page-sections')?.setAttribute('aria-label',text('sections'));
    selector.value = language; selector.setAttribute('aria-label',text('language'));
    const notice = document.querySelector('#translation-notice');
    notice.hidden = !current || current.language === language;
    notice.lang = language;
    notice.textContent = text('fallback').replace('{language}',LANGUAGE_NAMES[current?.language] || current?.language || defaultLanguage);
    for (const anchor of document.querySelectorAll('.site-navigation a[href], #main-content a[href], .skip-link')) {
      if (!anchor.dataset.sourceHref) anchor.dataset.sourceHref = anchor.getAttribute('href');
      const href = anchor.dataset.sourceHref;
      const target = router.rewrite(href,location.href,language,{explicitOverview:content.contains(anchor)});
      if (target) {
        anchor.href = target;
        if (anchor.closest('.site-navigation')) {
          const destination = router.byPath.get(target.pathname);
          if (current?.key === destination?.key) anchor.setAttribute('aria-current','page');
          else anchor.removeAttribute('aria-current');
        }
      } else {
        const original = new URL(href,location.href);
        const sourceFile = /\.(?:md|py|ps1|toml|yml|gemspec)$/.test(original.pathname) || /\/(?:LICENSE|NOTICE|Dockerfile)$/.test(original.pathname);
        if (original.origin === location.origin && document.body.dataset.repository && sourceFile && original.pathname.startsWith(base+'/')) {
          anchor.href = document.body.dataset.repository+'/blob/'+document.body.dataset.sourceBranch+'/'+original.pathname.slice(base.length+1)+original.hash;
        }
      }
    }
    return true;
  }
  for (const code of languages) { const option = new Option(LANGUAGE_NAMES[code] || code,code); option.lang = code; selector.append(option); }
  selector.closest('label').hidden = languages.length < 2;
  selector.addEventListener('change',() => { language = selector.value; applyLanguage(); });
  if (!applyLanguage()) return;
  const header = document.querySelector('.site-header');
  const updateHeader = () => document.documentElement.style.setProperty('--header-height', `${header.getBoundingClientRect().height}px`);
  new ResizeObserver(updateHeader).observe(header);
  updateHeader();

  const headings = [...content.querySelectorAll('h2[id]')];
  const navigation = document.querySelector('#page-sections');
  const toc = document.querySelector('#section-index');
  if (navigation && toc) {
    for (const heading of headings) {
      const link = document.createElement('a');
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      link.lang = document.documentElement.lang;
      navigation.append(link);
    }
    if (!headings.length) toc.parentElement.hidden = true;
    const compact = matchMedia('(max-width: 900px)');
    const fitToc = () => { toc.open = !compact.matches; };
    fitToc(); compact.addEventListener('change', fitToc);
    const links = [...navigation.querySelectorAll('a')];
    const sectionObserver = new IntersectionObserver(entries => {
      const first = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top-b.boundingClientRect.top)[0];
      if (!first) return;
      for (const link of links) {
        if (link.hash === `#${first.target.id}`) link.setAttribute('aria-current','location');
        else link.removeAttribute('aria-current');
      }
    }, {rootMargin:'-10% 0px -65% 0px'});
    headings.forEach(heading => sectionObserver.observe(heading));
  }

  function revealHash() {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
    if (!target) return;
    const parents = [];
    for (let node=target.parentElement; node; node=node.parentElement) if (node.tagName === 'DETAILS') parents.push(node);
    parents.reverse().forEach(node => { node.open = true; });
    if (parents.length) requestAnimationFrame(() => target.scrollIntoView());
  }
  addEventListener('hashchange',revealHash);
  if (location.hash) revealHash();

  for (const table of content.querySelectorAll('.readme-content table')) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll'; wrapper.tabIndex = 0;
    wrapper.setAttribute('role','region'); wrapper.setAttribute('aria-label',text('table'));
    table.before(wrapper); wrapper.append(table);
  }
  for (const pre of content.querySelectorAll('.readme-content pre')) {
    const code = pre.querySelector('code');
    if (!code) continue;
    const button = document.createElement('button');
    button.className = 'copy-code'; button.type = 'button'; button.textContent = text('copy');
    button.lang = language;
    button.setAttribute('aria-label',text('copyCode'));
    button.addEventListener('click',async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = text('copied');
        document.querySelector('#copy-status').textContent = text('copiedStatus');
      } catch {
        const range = document.createRange(); range.selectNodeContents(code);
        const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
        document.querySelector('#copy-status').textContent = text('selectStatus');
      }
      setTimeout(() => { button.textContent = text('copy'); },1800);
    });
    pre.prepend(button);
  }

  const canvas = document.querySelector('#hangry-background');
  const context = canvas.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let drops = [], frame = null, last = 0;
  function resize() {
    canvas.width = innerWidth; canvas.height = innerHeight;
    drops = Array.from({length:Math.ceil(innerWidth/20)},() => Math.random()*-60);
  }
  function draw(now) {
    if (document.hidden || reduced.matches) { frame = null; return; }
    if (now-last >= 120) {
      last = now;
      context.fillStyle = 'rgba(0,0,0,.12)'; context.fillRect(0,0,canvas.width,canvas.height);
      context.fillStyle = '#ff6b00'; context.font = '14px monospace';
      drops.forEach((drop,index) => {
        context.fillText('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random()*36)],index*20,drop*20);
        drops[index] = drop*20>canvas.height && Math.random()>.97 ? 0 : drop+1;
      });
    }
    frame = requestAnimationFrame(draw);
  }
  function animate() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    if (document.body.dataset.background === 'matrix' && !document.hidden && !reduced.matches) frame = requestAnimationFrame(draw);
    else context.clearRect(0,0,canvas.width,canvas.height);
  }
  resize(); animate();
  addEventListener('resize',resize); document.addEventListener('visibilitychange',animate); reduced.addEventListener('change',animate);
})();
