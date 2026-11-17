/* HidroSopó · piezas comunes de las páginas secundarias
   (laboratorio, Sopó Cuida el Agua, Mi recibo de agua, resultados).
   1. Aplica el tema que el usuario eligió en la app (Automático / Claro / Oscuro).
   2. Pone la barra superior con «Volver a la app» y los accesos a las demás páginas.
   3. Deja un botón flotante para volver a la app desde cualquier punto de la página. */
(function(){
  'use strict';
  var pref = 'auto';
  try{ pref = localStorage.getItem('hs_tema') || 'auto'; }catch(e){}
  if(pref === 'oscuro') document.documentElement.setAttribute('data-theme', 'dark');
  if(pref === 'claro') document.documentElement.setAttribute('data-theme', 'light');

  var PAGINAS = [
    ['gemelo.html', 'Laboratorio'],
    ['comunidad.html', 'Sopó Cuida el Agua'],
    ['recibo.html', 'Mi recibo'],
    ['resultados.html', 'Resultados']
  ];
  var css = ''
    + '.hs-barra{background:#14100C;color:#EDE7DC;font:600 13.5px "Inter",system-ui,sans-serif}'
    + '.hs-barra .hs-in{max-width:1080px;margin:0 auto;display:flex;align-items:center;gap:6px;overflow-x:auto;scrollbar-width:none;'
    + 'padding:8px max(16px,env(safe-area-inset-right,0px)) 8px max(16px,env(safe-area-inset-left,0px));padding-top:calc(8px + env(safe-area-inset-top,0px))}'
    + '.hs-barra .hs-in::-webkit-scrollbar{display:none}'
    + '.hs-barra a{color:#CFC6B8;text-decoration:none;padding:6px 11px;border-radius:999px;white-space:nowrap;flex:none}'
    + '.hs-barra a:hover{color:#fff;background:rgba(255,255,255,.08)}'
    + '.hs-barra a[aria-current="page"]{color:#fff;background:rgba(255,255,255,.14)}'
    + '.hs-barra a.hs-volver{display:inline-flex;align-items:center;gap:8px;color:#fff;background:#1F7FA8;font-weight:700;margin-right:6px}'
    + '.hs-barra a.hs-volver:hover{background:#2A8FBA}'
    + '.hs-barra img{width:20px;height:20px;border-radius:6px;display:block}'
    + '.hs-flota{position:fixed;left:max(14px,env(safe-area-inset-left,0px));bottom:calc(14px + env(safe-area-inset-bottom,0px));z-index:40;'
    + 'display:inline-flex;align-items:center;gap:8px;padding:10px 15px 10px 11px;border-radius:999px;background:#14100C;color:#fff;'
    + 'font:700 14px "Inter",system-ui,sans-serif;text-decoration:none;box-shadow:0 10px 26px -10px rgba(0,0,0,.6);opacity:0;transform:translateY(10px);transition:opacity .25s, transform .25s;pointer-events:none}'
    + '.hs-flota.ver{opacity:1;transform:none;pointer-events:auto}'
    + '.hs-flota img{width:22px;height:22px;border-radius:7px}'
    + '.hs-barra a:focus-visible,.hs-flota:focus-visible{outline:2px solid #7FC6E6;outline-offset:2px}'
    + '@media (prefers-reduced-motion:reduce){.hs-flota{transition:none}}';

  function montar(){
    var s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    var actual = (location.pathname.split('/').pop() || '').toLowerCase();
    var barra = document.createElement('nav');
    barra.className = 'hs-barra'; barra.setAttribute('aria-label', 'Páginas de HidroSopó');
    var html = '<div class="hs-in"><a class="hs-volver" href="index.html"><img src="iconos/icono-192.png" alt="">← Volver a la app</a>';
    PAGINAS.forEach(function(p){
      html += '<a href="' + p[0] + '"' + (actual === p[0] ? ' aria-current="page"' : '') + '>' + p[1] + '</a>';
    });
    barra.innerHTML = html + '</div>';
    document.body.insertBefore(barra, document.body.firstChild);
    var flota = document.createElement('a');
    flota.className = 'hs-flota'; flota.href = 'index.html';
    flota.innerHTML = '<img src="iconos/icono-192.png" alt="">App';
    flota.setAttribute('aria-label', 'Volver a la app de HidroSopó');
    document.body.appendChild(flota);
    var mirar = function(){ flota.classList.toggle('ver', window.scrollY > 260); };
    window.addEventListener('scroll', mirar, {passive:true}); mirar();
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar); else montar();
})();
