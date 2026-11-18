'use strict';
// Keep panel DOM intact so selections, scroll position and filters survive folding.
(() => {
  const layout=document.querySelector('.layout');
  for(const [side,selector,label] of [['left','nav','目录'],['right','aside','详情']]) {
    const panel=layout.querySelector(selector),content=document.createElement('div');
    content.className='panel-content';content.id=`${side}PanelContent`;
    while(panel.firstChild)content.append(panel.firstChild);
    const button=document.createElement('button');
    button.id=`toggle${side==='left'?'Left':'Right'}Panel`;button.type='button';
    button.className='panel-toggle';button.setAttribute('aria-controls',content.id);
    button.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="2.5" y="3.5" width="19" height="17" rx="4"/><path d="M8.5 4v16"/></svg>';
    panel.append(button,content);
    function setCollapsed(collapsed) {
      layout.classList.toggle(`${side}-collapsed`,collapsed);
      panel.classList.toggle('panel-collapsed',collapsed);content.hidden=collapsed;
      button.setAttribute('aria-expanded',String(!collapsed));
      button.title=collapsed?`展开${label}栏`:`收起${label}栏`;
      button.setAttribute('aria-label',button.title);
    }
    button.onclick=()=>setCollapsed(button.getAttribute('aria-expanded')==='true');
    setCollapsed(window.innerWidth<800);
  }
})();
