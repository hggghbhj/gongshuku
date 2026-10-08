# -*- coding: utf-8 -*-
"""通用 SaaS 下载站（nportal/fwebapi 类）浏览器逐页翻页收集 PDF。
用法：在 bu 里逐 tab、逐页点击翻页，收集 PDF。此脚本记录的是要执行的 bu.js 逻辑（供 computer_use 调用）。"""
COLLECT_JS = r'''
(function(category){
  function cur(){
    // 当前激活 tab 的可见 p_list 区域内的 PDF
    var active=document.querySelector('.tab-item.p_active');
    var root=document;
    var links=[...document.querySelectorAll('a[href*=".pdf"]')].map(a=>({
       href:a.href,
       txt:(a.textContent||'').trim()||(a.closest('li,tr,.p_item,.file-item')||{}).innerText||''
    }));
    // 找当前可见的分页组件：取可见的那个 p_page
    var pages=[...document.querySelectorAll('.p_page')].filter(p=>{
       var r=p.getBoundingClientRect();return r.width>0&&r.height>0;
    }).map(p=>[...p.querySelectorAll('.page_num')].map(a=>a.textContent.trim()));
    return JSON.stringify({category:active?active.textContent.trim():'',links:links,pages:pages});
  }
  return cur();
})()
'''
NEXT_JS = r'''
(function(){
  // 找到当前可见分页的“下一页”按钮并点击
  var pags=[...document.querySelectorAll('.p_page')].filter(p=>{
    var r=p.getBoundingClientRect();return r.width>0&&r.height>0;
  });
  if(!pags.length)return 'no visible pager';
  var pg=pags[0];
  var next=pg.querySelector('.page_next');
  if(!next)return 'no next';
  if(next.classList.contains('disabled'))return 'next disabled';
  next.click();return 'clicked next';
})()
'''
TAB_JS = r'''
(function(){
  var tabs=[...document.querySelectorAll('.p_tablist .tab-item')].map((t,i)=>({i:i,txt:t.textContent.trim(),active:t.classList.contains('p_active')}));
  return JSON.stringify(tabs);
})()
'''
def click_tab_js(i):
    return "(function(){var t=document.querySelectorAll('.p_tablist .tab-item')[%d];if(!t)return 'no tab';t.click();return 'clicked tab %d';})()"%(i,i)
