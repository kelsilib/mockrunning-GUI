'use strict';
let desktopMemory = {routes:[],presets:[],history:[],preferences:{}};
let desktopView = 'workspace', restoreDone = false, memoryTimer, mapMemoryTimer, lastUsbEvent = '', lastHistorySync = 0;
const originalApi = api, originalSetMode = setMode, originalSaveDraft = saveDraft, originalRenderStatus = renderStatus;
const el = (tag, cls, text) => {const element=document.createElement(tag);if(cls)element.className=cls;if(text!==undefined)element.textContent=text;return element;};
function memoryStatus(text, error=false){$('memory-state').textContent=text;$('memory-state').style.color=error?'#a6543a':'';}
async function memoryChange(payload){
  try{desktopMemory=await originalApi('memory',payload);renderMemory();memoryStatus('已保存在这台电脑');return desktopMemory;}
  catch(error){memoryStatus('保存失败，请重试',true);throw error;}
}
async function refreshMemory(){desktopMemory=await originalApi('memory');renderMemory();}
function remember(values){return memoryChange({action:'preferences',values});}
function laterRemember(values){clearTimeout(memoryTimer);memoryStatus('正在保存…');memoryTimer=setTimeout(()=>remember(values).catch(e=>message(e.message,'error')),350);}
function cacheNativePreferences(){
  if(window.pywebview?.api?.cache_preferences)window.pywebview.api.cache_preferences({draft:{name:$('route-name').value,points:draft},mode,view:desktopView,platform:$('platform').value,transport:$('transport').value,follow:$('follow').checked}).catch(()=>{});
}
window.addEventListener('pywebviewready',cacheNativePreferences);
function showView(view, persist=true){
  desktopView=['workspace','library','history'].includes(view)?view:'workspace';
  for(const id of ['workspace','library','history']){$(`${id}-view`).hidden=id!==desktopView;$(`view-${id}`).classList.toggle('selected',id===desktopView);}
  $('view-label').textContent={workspace:'工作台',library:'路线库',history:'回放历史'}[desktopView];
  if(desktopView==='workspace'&&map)requestAnimationFrame(()=>map.invalidateSize());
  if(persist&&restoreDone)remember({view:desktopView}).catch(e=>message(e.message,'error'));
  cacheNativePreferences();
}
setMode=function(value){const previous=mode;originalSetMode(value);if(previous!==value)document.querySelector('.inspector').scrollTop=0;if(restoreDone)remember({mode:value}).catch(e=>message(e.message,'error'));cacheNativePreferences();};
saveDraft=function(){originalSaveDraft();if(restoreDone)laterRemember({draft:{name:$('route-name').value,points:draft}});cacheNativePreferences();};
api=async function(action,data){
  const result=await originalApi(action,data);
  if(['start','stop','disconnect','clear-route','settings','connect','clear-leftover'].includes(action)&&data!==undefined){
    if(action==='connect')remember({platform:$('platform').value,transport:$('transport').value,device:data.udid||''}).catch(()=>{});
    await refreshMemory();
  }
  return result;
};
renderStatus=function(data){
  const previousState=status?.state;
  originalRenderStatus(data);
  const usb=data.desktop?.usb_devices||[];
  for(const option of $('devices').options){const row=usb.find(d=>d.udid===option.value);if(row)option.textContent=`${row.name||'iPhone'} · USB`;}
  if(restoreDone&&desktopMemory.preferences.device&&lastDeviceKey&&!data.connected){
    const wanted=desktopMemory.preferences.device;
    if(!$('devices').dataset.restored&&[...$('devices').options].some(o=>o.value===wanted)){$('devices').value=wanted;$('devices').dataset.restored='1';}
  }
  const selected=usb.find(d=>d.udid===$('devices').value)||usb[0];
  let title='未连接 iPhone',detail='使用 USB 连接并解锁手机。',kind='';
  if(data.desktop?.usb_error){title='USB 检测暂不可用';detail='请检查 Apple Devices 或重新插入 USB。';kind='warn';}
  else if(usb.length){
    title=usb.length>1?`${usb.length} 台 USB 手机`:'USB 已连接';kind='good';
    detail=`${selected.name||'iPhone'}${selected.ios_version?' · iOS '+selected.ios_version:''}`;
    if(selected.error){title='请解锁 iPhone';detail=selected.error;kind='warn';}
    else if(selected.paired===false){title='等待手机信任';detail='解锁 iPhone，点击“信任此电脑”。';kind='warn';}
    else if(selected.developer_mode===false){title='开发者模式未开启';detail='开启开发者模式并完成重启确认。';kind='warn';}
    else if(data.connected){title='定位服务已连接';detail+=' · 可以回放';}
    else detail+=' · 点击“连接手机”建立定位服务';
  }else if(data.connected){title='无线定位已连接';detail='当前通过无线通道连接。';kind='good';}
  if(data.desktop?.cleanup_pending){detail='模拟位置尚未确认清除。重连后点击下方按钮。';kind='warn';}
  $('usb-title').textContent=title;$('usb-detail').textContent=detail;$('usb-dot').className='status-dot '+kind;
  $('clear-leftover').hidden=!data.desktop?.cleanup_pending;
  $('clear-leftover').disabled=busy||data.connected||usb.length!==1;
  if(!data.error&&!data.discovery_error)$('device-help').textContent=data.connected?'结束时请清除模拟，并在手机地图上确认恢复。':'连接后，已载入路线的起点会发送到手机。';
  const event=data.desktop?.usb_event;
  if(event&&event.at!==lastUsbEvent){
    if(lastUsbEvent||event.kind==='removed')message(event.kind==='inserted'?'已检测到 USB 手机，请解锁并连接。':'USB 已断开。请重新连接手机。',event.kind==='removed'?'error':'');
    lastUsbEvent=event.at;
  }
  if(previousState!==data.state&&['completed','error'].includes(data.state))setTimeout(()=>refreshMemory().catch(()=>{}),1200);
  if(Date.now()-lastHistorySync>15000){lastHistorySync=Date.now();refreshMemory().catch(()=>{});}
};
function nameDialog(title,description,initial){
  $('name-title').textContent=title;$('name-description').textContent=description;$('name-input').value=initial||'';
  const dialog=$('name-dialog');dialog.returnValue='';dialog.showModal();setTimeout(()=>$('name-input').select(),30);
  return new Promise(resolve=>dialog.addEventListener('close',()=>resolve(dialog.returnValue==='save'?$('name-input').value.trim():null),{once:true}));
}
function confirmDialog(title,description){$('confirm-title').textContent=title;$('confirm-description').textContent=description;const dialog=$('confirm-dialog');dialog.returnValue='';dialog.showModal();return new Promise(resolve=>dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true}));}
function routeDistance(points){let distance=0;if(map)for(let i=1;i<points.length;i++)distance+=map.distance(coord(points[i-1]),coord(points[i]));return distance;}
function distanceText(distance){return distance>=1000?(distance/1000).toFixed(2)+' km':Math.round(distance)+' m';}
function dateText(value){return new Date(value).toLocaleDateString('zh-CN',{month:'long',day:'numeric'});}
function preview(points){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 220 100');
  const xs=points.map(p=>p.lng*Math.cos(points[0].lat*Math.PI/180)),ys=points.map(p=>p.lat);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const scale=Math.min(180/Math.max(maxX-minX,.0000001),70/Math.max(maxY-minY,.0000001));
  const width=(maxX-minX)*scale,height=(maxY-minY)*scale;
  const coordinates=points.map((p,i)=>[20+(180-width)/2+(xs[i]-minX)*scale,15+(70-height)/2+(maxY-ys[i])*scale]);
  const path=document.createElementNS(svg.namespaceURI,'polyline');path.setAttribute('points',coordinates.map(p=>p.join(',')).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','#b67252');path.setAttribute('stroke-width','2.5');path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');svg.append(path);
  for(const [index,color]of [[0,'#bd754e'],[coordinates.length-1,'#71856b']]){const dot=document.createElementNS(svg.namespaceURI,'circle');dot.setAttribute('cx',coordinates[index][0]);dot.setAttribute('cy',coordinates[index][1]);dot.setAttribute('r','4');dot.setAttribute('fill',color);dot.setAttribute('stroke','#fbf6e8');dot.setAttribute('stroke-width','2');svg.append(dot);}
  return svg;
}
function emptyState(symbol,title,description,buttonText,onClick){const box=el('div','empty-state');box.append(el('div','empty-symbol',symbol),el('h2','',title),el('p','',description));if(buttonText){const button=el('button','primary',buttonText);button.onclick=onClick;box.append(button);}return box;}
function renderRoutes(){
  const container=$('route-cards');container.replaceChildren();const query=$('library-search').value.trim().toLowerCase();
  const routes=desktopMemory.routes.filter(r=>r.name.toLowerCase().includes(query)).sort((a,b)=>b.updated_at.localeCompare(a.updated_at));
  $('library-count').textContent=desktopMemory.routes.length;$('route-total').textContent=desktopMemory.routes.length;
  if(!routes.length){container.append(emptyState('⌁',query?'没有匹配的路线':'给下一次，留一条路线。',query?'换个名称再搜索。':'在地图上布设或导入 GPX，然后保存到路线库。','去布设路线',()=>{showView('workspace');setMode('editor');}));return;}
  for(const route of routes){
    const card=el('article','route-card'),visual=el('div','route-preview');visual.append(preview(route.points),el('span','route-count',`${route.points.length} 个节点`));
    const info=el('div','route-card-info');info.append(el('h3','',route.name),el('p','',`${distanceText(routeDistance(route.points))} · 更新于 ${dateText(route.updated_at)}`));
    const actions=el('div','route-card-actions'),load=el('button','primary','载入回放'),edit=el('button','','编辑'),remove=el('button','delete','删除');
    load.onclick=()=>operation('载入保存的路线…',async()=>{await uploadRoute(route.points,route.name);showView('workspace');});
    edit.onclick=()=>{draft=route.points.map(p=>({...p}));$('route-name').value=route.name;showView('workspace');setMode('editor');edited();fit();};
    remove.onclick=async()=>{if(await confirmDialog('删除这条路线？',`“${route.name}”将从路线库删除，当前回放路线不会改变。`))operation('删除路线…',()=>memoryChange({action:'delete-route',id:route.id}));};
    actions.append(load,edit,remove);card.append(visual,info,actions);container.append(card);
  }
}
function renderPresets(){const select=$('preset-select'),previous=select.value;select.replaceChildren(new Option('选择常用配置',''));for(const preset of desktopMemory.presets)select.add(new Option(preset.name,preset.id));if(desktopMemory.presets.some(p=>p.id===previous))select.value=previous;}
function renderHistory(){
  const history=desktopMemory.history,container=$('history-list');container.replaceChildren();
  const today=new Date().toLocaleDateString();$('today-count').textContent=history.filter(h=>new Date(h.started_at).toLocaleDateString()===today).length;$('history-count').textContent=history.length;
  if(!history.length){container.append(emptyState('◷','下一次回放，从这里记起。','完成或停止回放后，日期、路线和参数会自动保留。'));return;}
  let lastDay='';const labels={stop:'已停止',disconnect:'已断开','clear-route':'已清空',completed:'已完成',error:'出现错误','usb-disconnected':'USB 断开',interrupted:'意外中断','window-closed':'关闭软件'};
  for(const record of history){const started=new Date(record.started_at),day=started.toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric'});if(day!==lastDay){container.append(el('div','history-day',day));lastDay=day;}
    const row=el('article','history-row'),time=el('span','time',started.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})),name=el('div');name.append(el('h3','',record.route_name||'未命名路线'),el('small','',record.platform==='ios'?'iPhone · 模拟回放':'Android · 模拟回放'));
    const pace=el('div','metric',(60/record.settings.speed_kmh).toFixed(2));pace.append(el('small','','min/km'));
    const distance=el('div','metric',distanceText(record.distance_m||0));distance.append(el('small','',Math.round(record.elapsed_s||0)+' 秒'));
    row.append(time,name,pace,distance,el('span','pill',labels[record.outcome]||'已结束'));container.append(row);
  }
}
function renderMemory(){renderRoutes();renderPresets();renderHistory();}
for(const view of ['workspace','library','history'])$(`view-${view}`).onclick=()=>showView(view);
$('open-library').onclick=()=>showView('library');$('library-search').oninput=renderRoutes;
$('new-route').onclick=()=>{showView('workspace');setMode('editor');draft=[];$('route-name').value='我的路线';edited();};
$('save-route').onclick=()=>operation('保存路线…',async()=>{if(draft.length<2)throw new Error('请先添加至少两个路线节点。');const name=await nameDialog('把路线留到下次。','保存后，可以在路线库中一键载入。',$('route-name').value);if(!name)return;$('route-name').value=name;saveDraft();const existing=desktopMemory.routes.find(r=>r.name===name);await memoryChange({action:'save-route',id:existing?.id,name,points:draft});message('路线已保存，下次打开仍可使用。','success');});
$('save-preset').onclick=()=>operation('收藏当前配置…',async()=>{if(!$('settings').reportValidity())return;const values=settings();const name=await nameDialog('记住这个节奏。','配速与高级参数会一起保存。',`${(60/values.speed_kmh).toFixed(2)} 分钟 / 公里`);if(name){await memoryChange({action:'save-preset',name,settings:values});message('常用配置已收藏。','success');}});
$('preset-select').onchange=()=>{const preset=desktopMemory.presets.find(p=>p.id===$('preset-select').value);if(preset){fillSettings(preset.settings);message('已填入常用配置，点击“保存参数”应用。');}};
$('clear-history').onclick=async()=>{if(await confirmDialog('清空回放历史？','只删除本机历史记录，路线库与常用配置会保留。'))operation('清空历史…',()=>memoryChange({action:'clear-history'}));};
$('clear-leftover').onclick=()=>operation('正在清除遗留定位，请保持 USB 连接…',async()=>{renderStatus(await api('clear-leftover',{}));message('已重新发送清除请求，请在手机地图上确认恢复真实位置。','success');});
$('refresh-usb').onclick=()=>operation('重新检测 USB…',async()=>{renderStatus(await api('refresh-usb',{}));message('USB 状态已更新。');});
$('about-open').onclick=()=>$('about-dialog').showModal();$('about-close').onclick=()=>$('about-dialog').close();
const originalFollowChange=$('follow').onchange;$('follow').onchange=()=>{originalFollowChange();remember({follow:$('follow').checked}).catch(()=>{});};
if(map)map.on('moveend',()=>{if(!restoreDone)return;clearTimeout(mapMemoryTimer);mapMemoryTimer=setTimeout(()=>remember({map_view:{lat:map.getCenter().lat,lng:map.getCenter().lng,zoom:map.getZoom()}}).catch(()=>{}),700);});
window.addEventListener('keydown',event=>{if(event.ctrlKey&&['1','2','3'].includes(event.key)){event.preventDefault();showView(['workspace','library','history'][Number(event.key)-1]);}if(event.ctrlKey&&event.key==='s'){event.preventDefault();$('save-route').click();}});
async function bootMemory(){
  try{await refreshMemory();const p=desktopMemory.preferences;
    if(p.draft){draft=p.draft.points;$('route-name').value=p.draft.name||'我的路线';originalSaveDraft();renderRoute();}
    if(['ios','android'].includes(p.platform))$('platform').value=p.platform;
    if(['auto','wireless'].includes(p.transport))$('transport').value=p.transport;
    connectionOptions();$('follow').checked=!!p.follow;
    originalSetMode(p.mode==='player'?'player':'editor');showView(p.view||'workspace',false);
    if(p.map_view&&map&&Number.isFinite(p.map_view.lat)&&Number.isFinite(p.map_view.lng)&&Number.isFinite(p.map_view.zoom))map.setView([p.map_view.lat,p.map_view.lng],p.map_view.zoom,{animate:false});else fit();
    restoreDone=true;memoryStatus('已保存在这台电脑');
  }catch(error){restoreDone=true;message('本地记忆加载失败：'+error.message,'error');memoryStatus('记忆加载失败',true);}
}
bootMemory();
