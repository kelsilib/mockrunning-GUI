from pathlib import Path

root = Path(__file__).parent
original = (root.parent / "src/ios_location_controller/static/index.html").read_text(encoding="utf-8")
editor = original[original.index('      <section id="editor-panel">'):original.index('      <section id="player-panel"')]
player = original[original.index('      <section id="player-panel"'):original.index('    </aside>')]
editor = editor.replace('<h2>在地图上布设路线</h2>', '<h2>画出你的路线</h2>').replace('01 / ROUTE BUILDER', 'ROUTE EDITOR')
editor = editor.replace('草稿自动保存在此浏览器。', '草稿自动保存在这台电脑。')
editor = editor.replace('<input type="file" id="editor-file"', '<button id="save-route" class="wide">保存到路线库</button><input type="file" id="editor-file"')
player = player.replace('<h2>在手机上回放</h2>', '<h2>按熟悉的节奏回放</h2>').replace('02 / DEVICE PLAYBACK', 'PLAYBACK')
start = player.index('        <fieldset id="connection-options">')
end = player.index('        <div class="device-card">')
advanced = player[start:end]
player = player[:start] + '<details class="advanced"><summary>连接选项与能力说明</summary>' + advanced + '</details>' + player[end:]
start = player.index('        <section class="place-card">')
end = player.index('        <form id="settings">')
player = player[:start] + '<details class="advanced"><summary>搜索地点与切换位置</summary>' + player[start:end] + '</details>' + player[end:]
player = player.replace('<legend>运动参数</legend>', '<legend>回放节奏</legend>')
player = player.replace('<button type="submit" id="apply">保存参数</button>', '<div class="preset-bar"><select id="preset-select" aria-label="常用配置"><option value="">选择常用配置</option></select><button id="save-preset" type="button" title="保存当前配置">收藏配置</button></div><button type="submit" id="apply">保存参数</button>')
player = player.replace('          <div class="row"><label>速度波动', '          <details class="advanced"><summary>更多回放参数</summary><div class="row"><label>速度波动')
player = player.replace('          <div class="preset-bar">', '          </details><div class="preset-bar">')
controls_start = player.index('        <div class="transport">')
controls_end = player.index('        <p class="hint">橙色', controls_start)
transport_controls = player[controls_start:controls_end]
player = player[:controls_start] + player[controls_end:]
player = player.replace('        <form id="settings">', transport_controls + '        <form id="settings">')

html = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Route Studio</title><link rel="stylesheet" href="/static/leaflet.css"><link rel="stylesheet" href="/static/app.css">
<script defer src="/static/leaflet.js"></script><script defer src="/static/app.js"></script><script defer src="/static/desktop.js"></script></head>
<body>
<aside class="sidebar">
  <div class="brand"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 25V10a4 4 0 0 1 4-4h12a4 4 0 0 1 0 8h-8a4 4 0 0 0 0 8h10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6" cy="25" r="2.7" fill="currentColor"/><circle cx="24" cy="22" r="2.7" fill="currentColor"/></svg><span>Route Studio</span></div>
  <p class="brand-caption">路线与定位工作台</p>
  <div class="nav-label">工作空间</div>
  <nav class="side-nav" aria-label="主导航">
    <button id="view-workspace" class="selected"><svg viewBox="0 0 24 24"><path d="M3 10l9-7 9 7v10H3zM9 20v-7h6v7"/></svg><span>工作台</span><kbd>1</kbd></button>
    <button id="view-library"><svg viewBox="0 0 24 24"><path d="M3 5h7l2 3h9v12H3z"/></svg><span>路线库</span><span id="library-count" class="nav-count">0</span></button>
    <button id="view-history"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg><span>回放历史</span></button>
  </nav>
  <div class="sidebar-note"><div class="small-spark"><svg viewBox="0 0 32 32" width="25" height="25"><path d="M6 25V10a4 4 0 0 1 4-4h12a4 4 0 0 1 0 8h-8a4 4 0 0 0 0 8h10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="6" cy="25" r="2" fill="currentColor"/><circle cx="24" cy="22" r="2" fill="currentColor"/></svg></div><h3>下次打开，接着用。</h3><p>路线、配速与草稿<br>都留在这台电脑。</p></div>
  <section class="usb-card" aria-live="polite"><div class="usb-top"><span id="usb-dot" class="status-dot"></span><b id="usb-title">正在检测 USB</b><button id="refresh-usb" title="重新检测" aria-label="重新检测 USB"><svg viewBox="0 0 24 24"><path d="M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0114-2l1 6M4 12l1 6a8 8 0 0014-2"/></svg></button></div><p id="usb-detail">正在检查 iPhone 连接</p><button id="clear-leftover" hidden>清除遗留定位</button></section>
  <div class="memory-footer"><span class="status-dot good"></span><span id="memory-state">本地记忆已开启</span><small>v1.0</small></div>
</aside>
<div class="app-shell">
  <header class="topbar"><div class="breadcrumb">你的工作空间 <span>/</span> <b id="view-label">工作台</b></div><span id="service" class="service-badge">正在启动…</span></header>
  <section id="workspace-view" class="page-view">
    <div class="page-heading"><div><span class="eyebrow">MAKE ROOM FOR THE NEXT ROUTE</span><h1>把路线，留在手边。</h1><p>从一条熟悉的路线开始，按自己的节奏回放。</p></div><button id="open-library" class="quiet-button">打开路线库 <span>↗</span></button></div>
    <div class="workspace-tabs"><nav aria-label="工作流程"><button id="tab-editor" class="active" aria-selected="true">布设路线</button><button id="tab-player" aria-selected="false">手机回放</button></nav><span class="autosave"><span class="status-dot good"></span>草稿自动保存</span></div>
    <main class="workspace-grid">
      <section class="map-wrap"><div id="map" aria-label="路线地图"></div><div class="map-note" id="map-note">单击添加节点 · 拖动调整</div><div id="map-warning" role="status" hidden></div><div class="map-tools"><button id="fit">查看路线</button><button id="locate-phone">定位到手机</button><label><input type="checkbox" id="follow">跟随位置</label></div><div class="map-coordinate">WGS84 · OpenStreetMap</div></section>
      <aside class="inspector">''' + editor + player + '''</aside>
    </main>
  </section>
  <section id="library-view" class="page-view collection-view" hidden><div class="page-heading"><div><span class="eyebrow">A PLACE FOR YOUR ROUTES</span><h1>熟悉的路线，随时出发。</h1><p>保存一次，下次不必重新布设。</p></div><button id="new-route" class="primary">新建路线 <span>＋</span></button></div><div class="collection-toolbar"><b>你的路线 <span id="route-total">0</span></b><label class="search-field"><svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/></svg><input id="library-search" placeholder="搜索路线名称" aria-label="搜索路线名称"></label></div><div id="route-cards" class="route-cards"></div></section>
  <section id="history-view" class="page-view collection-view" hidden><div class="page-heading"><div><span class="eyebrow">YOUR PLAYBACK JOURNAL</span><h1>每次回放，都有迹可循。</h1><p>保留日期、路线和实际回放参数，方便下次参考。</p></div><button id="clear-history" class="quiet-button">清空历史</button></div><div class="history-summary"><div><span>今天的回放</span><strong id="today-count">0</strong></div><div><span>累计会话</span><strong id="history-count">0</strong></div><div><span>记录内容</span><strong class="summary-text">模拟回放</strong></div></div><div id="history-list"></div></section>
  <footer><span id="message" role="status" aria-live="polite">准备就绪</span><button id="about-open">使用说明</button></footer>
</div>
<dialog id="name-dialog"><form method="dialog"><div class="dialog-eyebrow" id="name-kicker">SAVE FOR NEXT TIME</div><h2 id="name-title">保存路线</h2><p id="name-description">为它取个容易找到的名字。</p><input id="name-input" maxlength="100" required aria-label="名称"><div class="dialog-actions"><button value="cancel" formnovalidate>取消</button><button value="save" class="primary">保存</button></div></form></dialog>
<dialog id="confirm-dialog"><form method="dialog"><h2 id="confirm-title">确认删除？</h2><p id="confirm-description"></p><div class="dialog-actions"><button value="cancel">取消</button><button value="confirm" class="danger">确认删除</button></div></form></dialog>
<dialog id="about-dialog"><h2>准备好，再开始。</h2><p>USB 已发现手机和定位服务已连接是两种状态。请保持 iPhone 解锁、信任电脑并开启开发者模式。</p><p>连接手机时若已有路线，会发送路线起点；载入路线到已连接手机也会发送起点。关闭软件时会尝试停止并清除模拟。</p><p>回放结束后，点击“停止并清除模拟”，等待几秒，再确认手机地图恢复真实位置。断线时需要重连后清理。</p><p>历史只记录本软件的模拟回放，不代表真实运动或第三方平台记录。软件只发送经纬度，不模拟步数和传感器。</p><p>路线、常用配置、草稿和历史保存在本机；不会自动开始或自动连接。</p><button id="about-close" class="primary wide">知道了</button></dialog>
</body></html>'''
(root / "assets/index.html").write_text(html, encoding="utf-8")
print("Desktop HTML created")
