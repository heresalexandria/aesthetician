/* Run with the isolated Electron harness:
 * app/node_modules/.bin/electron app --shot /tmp/controls.png
 *   --shot-file videos-samples/untreated.mp4 --shot-js tests/renderer_controls_shot.js
 *   --shot-size 1120x700
 */
(async () => {
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  G.autoPreview = false; $('auto-preview').checked = false;
  G.refineOpen = true;
  G.filterFamilies.clear(); G.guideOpen = false; G.filterEra = '';
  $('preset-search').value = '2026'; buildFilterBar(); buildPresetList();
  const search=$('preset-search').getBoundingClientRect();
  const era=$('era-filter').getBoundingClientRect();
  const pane=$('preset-pane').getBoundingClientRect();
  assert(search.bottom < era.top, 'Search must have its own row');
  assert(search.width > pane.width - 32, 'Search must span the library pane');
  const refine=document.querySelector('.refine-chip'); refine.focus(); refine.click();
  assert(document.activeElement.classList.contains('refine-chip'),'Filter updates must retain keyboard focus');
  document.activeElement.click();
  $('era-filter').focus();
  assert(getComputedStyle($('era-filter')).outlineStyle!=='none','Dropdown focus must be visible');
  selectPreset('atlas-hollywood-blockbuster-2026');
  document.querySelectorAll('.effect-card').forEach(c=>c.classList.add('open'));
  const setNumber=(path,text,key='Enter')=>{
    const input=document.getElementById('param-'+path);
    assert(input && input.type==='number', path+' must accept a number');
    input.focus(); input.value=text;
    input.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true}));
    return input;
  };
  let n=setNumber('tone.contrast','1.237');
  assert(state.sets['tone.contrast']===1.237,'Manual value must reach override');
  assert(n.closest('.prow').querySelector('[type=range]').value==='1.237','Slider must follow number');
  setNumber('tone.contrast','7');
  assert(state.sets['tone.contrast']===2.5,'Manual value must clamp');
  setNumber('tone.contrast','1.4','Escape');
  assert(state.sets['tone.contrast']===2.5,'Escape must cancel');
  setNumber('tone.contrast','');
  assert(state.sets['tone.contrast']===2.5,'Empty input must cancel');
  setNumber('tone.contrast','1.18');
  assert(!('tone.contrast' in state.sets),'Preset value must clear override');
  const master=$('texture-val'); master.value='.375'; master.dispatchEvent(new Event('change'));
  assert(state.texture===.375 && $('texture').value==='0.375','Master numeric field must synchronize');
  for(const row of document.querySelectorAll('.prow.numeric')) {
    const r=row.getBoundingClientRect();
    for(const el of row.querySelectorAll('input,button,.number-value')) {
      const b=el.getBoundingClientRect();
      assert(b.left>=r.left-1 && b.right<=r.right+1, 'Control overflows: '+row.innerText);
    }
  }
  // All registry controls can be constructed and edited, including repeated keys.
  const oldSets=state.sets; state.sets={};
  const fixture=document.createElement('div');
  fixture.style.cssText='position:fixed;left:0;top:0;visibility:hidden;';
  fixture.style.width=document.querySelector('.prow').getBoundingClientRect().width+'px';
  document.body.appendChild(fixture);
  let numeric=0,other=0;
  for(const [eid,eff] of Object.entries(G.schema.effects)) {
    for(const prm of eff.params) {
      if(prm.name==='enabled') continue;
      const path=eid+'.'+prm.name;
      const row=paramRow(path,prm,prm.default,prm.default);
      fixture.replaceChildren(row);
      const bounds=row.getBoundingClientRect();
      for(const input of row.querySelectorAll('input,select,button')) {
        const b=input.getBoundingClientRect();
        assert(b.left>=bounds.left-1 && b.right<=bounds.right+1,path+' overflows the parameter pane');
      }
      if(['float','int'].includes(prm.kind)) {
        numeric++;
        const inp=row.querySelector('input[type=number]');
        const target=quantize(prm.lo+(prm.hi-prm.lo)*.63,prm);
        inp.value=target; inp.dispatchEvent(new Event('change'));
        assert((state.sets[path] ?? prm.default)===target,path+' fails manual editing');
      } else {
        other++;
        const inp=row.querySelector('select,input');
        assert(inp && inp.id && row.querySelector('label').htmlFor===inp.id,path+' is unlabeled');
        let want;
        if(prm.kind==='bool') { want=!prm.default; inp.checked=want; }
        else if(prm.kind==='enum') { want=prm.choices.at(-1); inp.value=want; }
        else if(prm.fmt==='datetime') { want='2001-02-03 04:05:06'; inp.value=want.replace(' ','T'); }
        else { want=prm.fmt==='clock' ? '1:23:45' : 'TEST'; inp.value=want; }
        inp.dispatchEvent(new Event('change'));
        assert((state.sets[path] ?? prm.default)===want,path+' fails keyboard/select editing');
      }
    }
  }
  fixture.remove();
  state.sets=oldSets; buildParamPane();
  document.querySelectorAll('.effect-card').forEach(c=>c.classList.add('open'));
  $('param-list').scrollTop=0;
  document.body.dataset.controlAudit = `${numeric} numeric / ${other} other controls passed`;
  console.log('[ui-audit] PASS: '+numeric+' numeric controls, '+other+' other controls; bounds, cancellation, resets, master fields, search layout');
  // Opening a card and resetting a value keeps its disclosure open.
  const first=document.querySelector('.effect-card');
  const disclosure=first.querySelector('.effect-disclosure');
  if(first.classList.contains('open')) disclosure.click();
  disclosure.click();
  first.querySelector('.reset-mini').click();
  assert(document.querySelector('.effect-card').classList.contains('open'),'Reset must preserve expansion');
  // Conditional controls announce their dependency and wake when it changes.
  const cm=effectCard({eid:'codec_era',key:'codec_era',params:{codec:'h264',crf:20}},{});
  const row=name=>cm.querySelector(`[data-param="${name}"]`);
  assert(row('kbps').querySelector('input').disabled,'CRF must disable ignored bitrate');
  const crf=row('crf').querySelector('input[type=number]');
  crf.value=-1; crf.dispatchEvent(new Event('change'));
  assert(!row('kbps').querySelector('input').disabled,'Bitrate must wake in bitrate mode');
  delete state.sets['codec_era.crf'];
  state.texture=.25; state.seed=1; buildParamPane(); syncMasterDials();
  G.autoPreview=true; $('auto-preview').checked=true; syncRenderButton();
  clearTimeout(previewTimer); await runPreview();
  for(let i=0;i<200 && videoA.readyState<2;i++) await new Promise(r=>setTimeout(r,100));
  assert(videoA.readyState>=2 && videoA.videoWidth>0,'Rendered preview must decode');
  const center=$('center-pane').getBoundingClientRect();
  for(const el of document.querySelectorAll('#player-controls button,#player-controls select,#player-controls .switch,#export-bar button,#export-bar .check')) {
    if(!el.getClientRects().length) continue;
    const b=el.getBoundingClientRect();
    assert(b.left>=center.left-1 && b.right<=center.right+1,'Center control overflows: '+el.id);
  }
})();
