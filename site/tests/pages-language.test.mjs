import test from 'node:test';
import assert from 'node:assert/strict';
import {LANGUAGE_NAMES,MESSAGES,chooseLanguage,createRouter} from '../theme/assets/hangry-pages/i18n.mjs';

const base='/a-tool', origin='http://127.0.0.1:9005';
const languages=Object.keys(LANGUAGE_NAMES);
const pages={
  [`${base}/README.md`]:`${base}/`,
  [`${base}/README.nb.md`]:`${base}/README.nb.html`,
  [`${base}/README.pl.md`]:`${base}/README.pl.html`,
  [`${base}/docs/API.md`]:`${base}/docs/API.html`,
  [`${base}/docs/API.nb.md`]:`${base}/docs/API.nb.html`,
  [`${base}/docs/ENGINE.md`]:`${base}/docs/ENGINE.html`,
  [`${base}/examples/index.md`]:`${base}/examples/`,
};
const router=()=>createRouter(pages,{base,origin,siteUrl:'https://example.github.io',languages});

test('website catalogs have matching keys and translated language names',()=>{
  for(const code of languages){
    assert.deepEqual(Object.keys(MESSAGES[code]).sort(),Object.keys(MESSAGES.en).sort());
    assert(MESSAGES[code].fallback.includes('{language}'));
  }
});
test('explicit URL and translated documents precede a saved language preference',()=>{
  const pick=values=>chooseLanguage({languages,...values});
  assert.equal(pick({query:'en',page:'nb',stored:'pl'}),'en');
  assert.equal(pick({page:'nb',stored:'pl'}),'nb');
  assert.equal(pick({page:'en',stored:'pl'}),'pl');
  assert.equal(pick({query:'unsupported',stored:'unsupported',page:'en'}),'en');
});
test('translated technical Markdown is served when available, with an honest fallback otherwise',()=>{
  const r=router(),api=r.bySource.get(base+'/docs/API.md'),engine=r.bySource.get(base+'/docs/ENGINE.md');
  assert.equal(r.resolve(api,'nb').path,base+'/docs/API.nb.html');
  assert.equal(r.resolve(api,'pl').language,'en');
  assert.equal(r.resolve(engine,'nb'),engine);
});
test('public examples CTA stays inside the website preview and preserves the requested locale',()=>{
  const target=router().rewrite('https://example.github.io/a-tool/examples/?lang=nb',origin+base+'/README.nb.html','pl');
  assert.equal(target.href,origin+base+'/examples/?lang=nb');
});
test('overview links follow the selected locale while explicit README language links keep their intent',()=>{
  const r=router(),from=origin+base+'/';
  assert.equal(r.rewrite(base+'/',from,'nb').pathname,base+'/README.nb.html');
  assert.equal(r.rewrite('README.pl.md',from,'nb',{explicitOverview:true}).searchParams.get('lang'),'pl');
  assert.equal(r.rewrite('README.md',from,'nb',{explicitOverview:true}).searchParams.get('lang'),'en');
});
test('fallback documents retain fragments and query values while translated pages avoid stale anchors',()=>{
  const r=router(),from=origin+base+'/';
  assert.equal(r.rewrite('docs/ENGINE.md?example=1#limits',from,'nb').href,origin+base+'/docs/ENGINE.html?example=1&lang=nb#limits');
  assert.equal(r.rewrite('docs/API.md#english-heading',from,'nb').hash,'');
  assert.equal(r.rewrite('https://elsewhere.example/guide',from,'nb'),null);
  assert.equal(r.rewrite('examples/definitions.json',from,'nb'),null);
});
