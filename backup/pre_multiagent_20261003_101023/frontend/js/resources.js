/* ME-AITA 优质资源推荐页 */
(function () {
  "use strict";
  var API = "";
  var $ = function (s) { return document.querySelector(s); };
  var toastTimer = null;
  var SUBJECTS = ["全部", "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "道德与法治", "科学", "信息技术", "体育与健康", "音乐", "美术", "通用", "其他"];

  function notify(msg) {
    var el = $("#toast");
    el.textContent = msg;
    el.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("on"); }, 2600);
  }

  function esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function init() {
    // 学科选项
    $("#fSubject").innerHTML = SUBJECTS.map(function (v) { return '<option>' + esc(v) + "</option>"; }).join("");
    // 类别选项
    fetch(API + "api/resources/categories").then(function (r) { return r.json(); }).then(function (d) {
      $("#fCategory").innerHTML = ["全部"].concat(d.categories || []).map(function (v) { return '<option>' + esc(v) + "</option>"; }).join("");
    }).catch(function () {});
    loadResources();
    $("#searchBtn").addEventListener("click", loadResources);
    $("#fSearch").addEventListener("keydown", function (e) { if (e.key === "Enter") loadResources(); });
    $("#importBtn").addEventListener("click", doImport);
  }

  function loadResources() {
    var params = new URLSearchParams({
      stage: $("#fStage").value,
      subject: $("#fSubject").value,
      category: $("#fCategory").value,
      q: $("#fSearch").value.trim()
    });
    $("#resList").innerHTML = '<div class="res-empty">正在检索…</div>';
    fetch(API + "api/resources?" + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (data) { render(data.resources || []); })
      .catch(function () {
        $("#resList").innerHTML = '<div class="res-empty">无法连接后端服务，请先运行 启动智能体.bat。</div>';
      });
  }

  function render(items) {
    var list = $("#resList");
    if (!items.length) {
      list.innerHTML = '<div class="res-empty">未找到匹配资源。可尝试放宽筛选条件，或通过下方导入功能添加真实资源。</div>';
      return;
    }
    var html = "";
    items.forEach(function (r) {
      html += '<div class="res-card"><h3>' + esc(r.name) + "</h3>";
      html += '<div class="res-tags"><span class="res-tag cat">' + esc(r.category) + "</span>";
      html += '<span class="res-tag">' + esc(r.stage) + "</span>";
      html += '<span class="res-tag">' + esc(r.subject) + "</span></div>";
      html += '<div class="res-content">' + esc(r.content) + "</div>";
      if (r.source) html += '<div class="res-content" style="color:#7291b7;font-size:12px">来源：' + esc(r.source) + "</div>";
      if (r.url) html += '<a class="res-link" href="' + esc(r.url) + '" target="_blank" rel="noopener noreferrer">访问资源 ↗</a>';
      html += "</div>";
    });
    list.innerHTML = html;
  }

  function doImport() {
    var file = $("#importFile").files[0];
    if (!file) { notify("请先选择 JSON 文件"); return; }
    var reader = new FileReader();
    reader.onload = function () {
      var data;
      try { data = JSON.parse(reader.result); } catch (e) { notify("JSON 解析失败，请检查格式"); return; }
      var arr = Array.isArray(data) ? data : (data.resources || null);
      if (!arr || !arr.length) { notify("文件中没有可导入的资源"); return; }
      fetch(API + "api/resources/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resources: arr })
      }).then(function (r) { return r.json(); }).then(function (d) {
        $("#importMsg").textContent = d.ok ? "成功导入 " + d.added + " 条资源" : (d.detail || "导入失败");
        loadResources();
      }).catch(function () { notify("导入失败：无法连接后端"); });
    };
    reader.readAsText(file);
  }

  init();
})();
