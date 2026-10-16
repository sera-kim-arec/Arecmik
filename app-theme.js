// Apply the saved preference before paint; this never touches account or widget data.
(() => {
 const key='arecmik.app.theme';
 const choices=Object.freeze([
  {id:'glass',name:'반투명',description:'은은한 배경과 유리처럼 비치는 카드',color:'#E7EFE9'},
  {id:'lemon',name:'레몬 크림',description:'따뜻한 크림 바탕에 레몬 포인트',color:'#F8F5E8'},
  {id:'mono',name:'흑백',description:'차분한 무채색과 또렷한 대비',color:'#F4F4F3'}
 ]);
 const valid=id=>choices.some(choice=>choice.id===id);
 let saved='glass';try{saved=localStorage.getItem(key)||saved;}catch(_){}
 function apply(id,persist=true){
  if(!valid(id))return false;
  document.documentElement.dataset.appTheme=id;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',choices.find(choice=>choice.id===id).color);
  let stored=true;if(persist)try{localStorage.setItem(key,id);}catch(_){stored=false;}
  document.querySelectorAll('[data-app-theme-choice]').forEach(button=>{
   const selected=button.dataset.appThemeChoice===id;
   button.setAttribute('aria-checked',String(selected));button.tabIndex=selected?0:-1;
  });
  const label=document.querySelector('[data-app-theme-label]');if(label)label.textContent=choices.find(choice=>choice.id===id).name;
  return stored;
 }
 apply(valid(saved)?saved:'glass',false);
 document.addEventListener('DOMContentLoaded',()=>apply(document.documentElement.dataset.appTheme,false),{once:true});
 window.ArecmikTheme=Object.freeze({choices,current:()=>document.documentElement.dataset.appTheme,apply});
})();
