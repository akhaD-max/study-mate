'use strict';
const routes = new Map(screens.map(screen => [screen[0], screen]));
const byId = id => document.getElementById(id);
const auth = new Set(['home','login','loginError','register','registerError','reset','resetSent','newPassword','google']);
const forms = new Set(['login','loginError','register','registerError','reset','newPassword','editProfile','profileError','catalog','create','createError','editProject','apply','applyError','invite','comments']);
const errorRoute = {login:'loginError',register:'registerError',editProfile:'profileError',create:'createError',apply:'applyError'};
const navItems = [['Проекты','catalog'],['Профиль','profile'],['Заявки','applications'],['Мои проекты','mine'],['Уведомления','notifications'],['Состояния','states'],['Выход','logout']];
const catalogRoutes = new Set(['catalog','results','empty','error']);
const projectRoutes = new Set(['project','owner','mine','team','comments']);
const applicationRoutes = new Set(['applications','incoming','candidate','candidateFull','candidateZero','candidateNone','candidateError','invites','notifications','read']);
const confirmations = new Set(['delete','reject','close','remove','logout','accepted','rejected','removed','closed','sent','commentSent']);
const layouts = {
  catalog:['Поиск по кампусу','Уточни направление, навыки или статус набора.',[['Мои проекты','mine'],['Создать проект','create']]],
  project:['Команда проекта','Проверь роли и свободные места перед откликом.',[['Каталог проектов','catalog'],['Мои заявки','applications']]],
  applications:['Работа с откликами','Здесь можно вернуться к своим заявкам или управлять откликами на свой проект.',[['Мои заявки','applications'],['Мои проекты','mine']]],
  profile:['Твои навыки','Команда увидит профиль при рассмотрении твоей заявки.',[['Редактировать профиль','editProfile'],['Посмотреть проекты','catalog']]],
  editor:['Перед сохранением','Проверь обязательные поля и сроки. Данные останутся в рамках демо.',[['В каталог','catalog']]],
};
function layoutFor(id) {
  if(auth.has(id)) return 'auth';
  if(confirmations.has(id)) return 'confirmation';
  if(catalogRoutes.has(id)) return 'catalog';
  if(projectRoutes.has(id)) return 'project';
  if(applicationRoutes.has(id)) return 'applications';
  if(id==='profile') return 'profile';
  if(id==='states') return 'states';
  return 'editor';
}
function element(parent, tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  parent.append(node);
  return node;
}
function link(parent, label, key, className) {
  const node = element(parent,'a',label,className);
  node.href = '#' + key;
  return node;
}
function portfolio(parent) {
  const tabs = element(parent,'nav',null,'folder-tabs');
  tabs.setAttribute('aria-label','Разделы портфолио');
  const stack = element(parent,'div',null,'folio-stack');
  let sheet;
  const sections = {
    'Обо мне': () => {
      for (const corner of ['tl','tr','bl','br']) {
        element(sheet,'span',null,'pixel-corner '+corner).setAttribute('aria-hidden','true');
      }
      element(sheet,'p','Александра Морозова · НГУ','cover-owner');
      const heading = element(sheet,'h2','Портфолио','cover-word');
      element(heading,'span',null,'cover-cursor').setAttribute('aria-hidden','true');
      element(sheet,'p','Прикладная информатика · 3 курс','cover-degree');
      const skills = element(sheet,'div',null,'folder-skills');
      ['Python','SQL','Git','Figma'].forEach(skill => element(skills,'span',skill,'folder-tag'));
      const about = element(sheet,'details',null,'cover-about');
      element(about,'summary','Об интересах Александры');
      element(about,'p','Ищу команду, в которой можно развивать идеи и получать практический опыт.');
    },
    'Проекты': () => {
      element(sheet,'p','МОЁ ПОРТФОЛИО','folder-kicker');
      element(sheet,'h2','Проекты','folder-section-title');
      const item = element(sheet,'article',null,'folder-project');
      element(item,'h3','Campus Map');
      element(item,'p','Навигация по университету · Backend');
      link(item,'Открыть проект','project','button');
      link(sheet,'Мои проекты','mine','button');
    },
    'Заявки': () => {
      element(sheet,'p','МОЯ АКТИВНОСТЬ','folder-kicker');
      element(sheet,'h2','Заявки','folder-section-title');
      element(sheet,'p','Campus Map · На рассмотрении','folder-project');
      link(sheet,'Посмотреть заявки','applications','button');
    }
  };
  const panels = [];
  for (const [name, draw] of Object.entries(sections)) {
    const tab = element(tabs,'button',name,'folder-tab');
    tab.type = 'button';
    sheet = element(stack,'section',null,'folder-sheet');
    const panel = sheet;
    panel.dataset.page = String(panels.length);
    panel.setAttribute('aria-label',name);
    panel.id = 'portfolio-page-' + panels.length;
    tab.setAttribute('aria-controls',panel.id);
    draw();
    panel.hidden = panels.length > 0;
    tab.setAttribute('aria-pressed',String(!panel.hidden));
    tab.addEventListener('click',() => {
      if (tab.getAttribute('aria-pressed') === 'true') return;
      const motion = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      for (const entry of panels) {
        const active = entry.panel === panel;
        const outgoing = entry.tab.getAttribute('aria-pressed') === 'true';
        entry.panel.getAnimations().forEach(animation => animation.cancel());
        entry.tab.setAttribute('aria-pressed',String(active));
        entry.panel.inert = !active;
        entry.panel.hidden = !(active || (motion && outgoing));
        if (!motion || (!active && !outgoing)) continue;
        const frames = active
          ? [{transform:'translateY(36px) rotate(1deg)',opacity:0},{transform:'none',opacity:1}]
          : [{transform:'none',opacity:1},{transform:'translateY(-24px) scale(.96)',opacity:0}];
        const transition = entry.panel.animate(frames,{duration:active ? 450 : 220,easing:'cubic-bezier(.2,.8,.2,1)'});
        transition.onfinish = () => { entry.panel.hidden = entry.tab.getAttribute('aria-pressed') !== 'true'; };
      }
    });
    panels.push({tab,panel});
  }
}
function fieldsFor(parent, key, fields) {
  for (const value of fields) {
    if ((key === 'apply' || key === 'applyError') && value.includes('место')) {
      const label = element(parent,'label',null,'field');
      const radio = element(label,'input'); radio.type='radio'; radio.name='role'; radio.required=true;
      label.append(' '+value); continue;
    }
    if (!forms.has(key) || value.includes('занято') || /Campus Map ·|Ответ команды ·|Анна ·/.test(value)) {
      const [heading,...meta]=value.split(' · ');
      const card=element(parent,'article',null,'item');
      element(card,'strong',heading);
      for(const part of meta)element(card,'span',part,'item-label');
      continue;
    }
    const label = element(parent,'label',null,'field');
    element(label,'strong',value);
    const field = element(label,/описание|письмо|сообщение|о себе|комментарий/i.test(value)?'textarea':'input');
    if (field.tagName === 'INPUT') field.type = /Email/i.test(value)?'email':/пароль/i.test(value)?'password':/дедлайн/i.test(value)?'date':/аватар|файлы/i.test(value)?'file':'text';
    field.required = /^(Email|Пароль|Новый пароль|Повтор пароля|Вуз|Специальность|Курс|Навыки|Название|Описание|Роль · Места)/i.test(value) && !['catalog','comments'].includes(key);
    if (field.type==='password') field.minLength=6;
    if (field.type==='email') field.placeholder='student@example.com';
    if (key==='catalog' && value==='Название или описание') field.name='q';
  }
}
function render(focusTitle=false) {
  const key = location.hash.slice(1) || 'catalog';
  const state = key === 'states';
  const [id,title,description,fields,actions] = state
    ? ['states','Состояния интерфейса','Статусы заявок, набор, навыки и обратная связь.','','']
    : routes.get(key) || routes.get('catalog');
  byId('title').textContent=title; byId('description').textContent=description;
  const heading = byId('title');
  heading.classList.remove('pixel-heading');
  heading.removeAttribute('aria-label');
  if (['catalog','applications','notifications','mine','invites','create','profile'].includes(id)) pixelHeading(heading);
  const layout=layoutFor(id);
  document.body.dataset.layout=layout;
  const sectionNames={auth:'Аккаунт',catalog:'Кампус / Каталог',project:'Проекты / Команда',applications:'Активность',profile:'Личный кабинет',editor:'Редактирование',states:'Компоненты',confirmation:'Подтверждение'};
  byId('section').textContent=sectionNames[layout];
  const context=layouts[layout];
  byId('context-title').textContent=context?.[0]||'';
  byId('context-copy').textContent=context?.[1]||'';
  const contextLinks=byId('context-links');
  contextLinks.replaceChildren();
  for(const [label,target] of context?.[2]||[])link(contextLinks,label,target,'navlink');
  document.title=title+' · StudyMate';
  const nav=byId('nav'), content=byId('content'), list=byId('screens');
  nav.replaceChildren(); content.replaceChildren(); list.replaceChildren();
  for(const [label,target] of auth.has(id)?[['Проекты','catalog'],['Регистрация','register'],['Состояния','states']]:navItems){
    const item=link(nav,label,target,'navlink');
    if(target===id)item.setAttribute('aria-current','page');
  }
  document.querySelector('.entry').hidden=!auth.has(id);
  const body=element(content,'div',null,'fields');
  if(state)for(const [heading,...labels] of groups){
    const group=element(body,'section',null,'state');
    element(group,'h2',heading);
    for(const label of labels)element(group,'span',label,'badge '+(/ошиб|отклон|некоррект|короткий|занят|отменён/i.test(label)?'danger':/принят|открыт|сохранено|совпали/i.test(label)?'success':/рассмотрении|загрузка|ожидает/i.test(label)?'pending':''));
  }
  if(id==='profile') portfolio(body);
  else if(fields)fieldsFor(body,id,fields.split('|'));
  const buttons=element(content,'div',null,'actions');
  const parsed=actions?actions.split('|').map(item=>item.split(':')):[];
  let submitTo;
  for(const [i,[label,target]] of parsed.entries()){
    const submit = forms.has(id) && (id==='catalog'?target==='results':i===0);
    if(submit){
      const button=element(buttons,'button',label,'button primary');
      button.type='submit'; submitTo=target;
    }else link(buttons,label,target,'button'+(i===0?' primary':''));
  }
  content.onsubmit=event=>{
    event.preventDefault();
    if(id==='catalog'){
      const query=new FormData(content).get('q')?.trim() || '';
      location.hash = query && !/campus|python|карта/i.test(query)?'empty':'results';
    }else if(submitTo){location.hash=submitTo;}
  };
  for(const [target,label] of routes.values())link(list,label,target);
  link(list,'Состояния интерфейса','states');
  const poster=document.querySelector('.poster');
  poster.classList.remove('enter'); void poster.offsetWidth; poster.classList.add('enter');
  if(focusTitle){byId('title').focus({preventScroll:true}); window.scrollTo(0,0);}
}
addEventListener('hashchange',()=>render(true));
byId('content').addEventListener('invalid',event=>{
  const target=errorRoute[location.hash.slice(1)];
  if(target){
    event.preventDefault();
    location.hash=target;
  }
},true);
render();
