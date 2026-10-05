/* ME-AITA 数字素养诊断页（试用版） */
(function () {
  "use strict";
  var API = "";
  var $ = function (s) { return document.querySelector(s); };
  var toastTimer = null;
  var META = null;

  function notify(msg) {
    var el = $("#toast");
    el.textContent = msg;
    el.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("on"); }, 2600);
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function init() {
    Promise.all([
      fetch(API + "api/diagnosis/meta").then(function (r) { return r.json(); }),
      fetch(API + "api/diagnosis/questions").then(function (r) { return r.json(); })
    ]).then(function (results) {
      META = results[0];
      var qs = results[1].questions || [];
      $("#trialNote").textContent = (META.trial_note || "") + " 共 " + qs.length + " 题，请按实际情况作答（约 3 分钟）。";
      renderForm(META, qs);
    }).catch(function () {
      $("#trialNote").textContent = "无法连接后端服务，请先运行 启动智能体.bat。";
    });
  }

  function renderForm(meta, questions) {
    var wrap = $("#diagFormWrap");
    var html = '<div class="diag-toolbar">';
    html += '<div class="diag-field"><label>身份</label><select id="fIdentity">' + meta.identities.map(function (v) { return '<option>' + esc(v) + "</option>"; }).join("") + "</select></div>";
    html += '<div class="diag-field"><label>学段</label><select id="fStage">' + meta.stages.map(function (v) { return '<option>' + esc(v) + "</option>"; }).join("") + "</select></div>";
    html += '<div class="diag-field"><label>学科</label><select id="fSubject">' + meta.subjects.map(function (v) { return '<option>' + esc(v) + "</option>"; }).join("") + "</select></div>";
    html += "</div>";

    // 按维度分组
    var groups = {};
    questions.forEach(function (q) {
      (groups[q.dimension] = groups[q.dimension] || []).push(q);
    });
    Object.keys(groups).forEach(function (dim) {
      html += '<div class="quiz-group"><h3><span class="dim-badge">维度</span>' + esc(dim) + "</h3>";
      groups[dim].forEach(function (q) {
        html += '<div class="quiz-item"><div class="q-text">' + esc(q.text) + "</div>";
        html += '<div class="opt-row" data-qid="' + esc(q.id) + '">';
        var labels = ["非常不符合", "比较不符合", "一般", "比较符合", "非常符合"];
        for (var i = 1; i <= 5; i++) {
          html += '<label><input type="radio" name="' + esc(q.id) + '" value="' + i + '"><span>' + i + " · " + labels[i - 1] + "</span></label>";
        }
        html += "</div></div>";
      });
      html += "</div>";
    });
    html += '<div style="display:flex;gap:12px;flex-wrap:wrap"><button class="btn-primary" id="submitDiag" type="button">提交测评</button><button class="btn-ghost" type="button" id="resetDiag">重置</button></div>';
    wrap.innerHTML = html;

    // 单选高亮
    wrap.querySelectorAll(".opt-row").forEach(function (row) {
      row.querySelectorAll("input").forEach(function (input) {
        input.addEventListener("change", function () {
          row.querySelectorAll("label").forEach(function (l) { l.classList.remove("on"); });
          input.closest("label").classList.add("on");
        });
      });
    });

    $("#resetDiag").addEventListener("click", function () {
      wrap.querySelectorAll("input:checked").forEach(function (i) { i.checked = false; });
      wrap.querySelectorAll("label.on").forEach(function (l) { l.classList.remove("on"); });
      notify("已重置");
    });

    $("#submitDiag").addEventListener("click", function () { submit(questions); });
  }

  function submit(questions) {
    var answers = {};
    var missing = [];
    questions.forEach(function (q) {
      var checked = document.querySelector('input[name="' + q.id + '"]:checked');
      if (checked) answers[q.id] = parseInt(checked.value, 10);
      else missing.push(q.text);
    });
    if (missing.length) {
      notify("还有 " + missing.length + " 题未作答");
      return;
    }
    var btn = $("#submitDiag");
    btn.disabled = true;
    btn.textContent = "提交中…";

    fetch(API + "api/diagnosis/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identity: $("#fIdentity").value,
        stage: $("#fStage").value,
        subject: $("#fSubject").value,
        answers: answers
      })
    }).then(function (r) { return r.json(); }).then(function (data) {
      btn.disabled = false;
      btn.textContent = "提交测评";
      if (!data.ok) {
        notify(data.message || "提交失败");
        return;
      }
      showResult(data.report);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }).catch(function () {
      btn.disabled = false;
      btn.textContent = "提交测评";
      notify("提交失败：无法连接后端");
    });
  }

  function showResult(report) {
    $("#diagFormWrap").style.display = "none";
    var wrap = $("#diagResultWrap");
    wrap.style.display = "block";

    var html = '<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap">';
    html += '<div><h2 style="margin:0 0 6px;color:#16408c;font-size:21px">测评结果（试用版）</h2>';
    html += '<div class="trial-note" style="margin:0">' + esc(report.trial_note) + "</div></div>";
    html += '<div class="total-badge">总分 <b>' + report.total + "</b> / " + report.max_total + '　等级：' + esc(report.level) + "</div>";
    html += "</div>";

    html += '<div class="result-grid">';
    report.dimensions.forEach(function (d) {
      var pct = Math.round(d.ratio * 100);
      html += '<div class="result-item"><div class="dim-name">' + esc(d.dimension) + "</div>";
      html += '<div class="bar-track"><div class="bar-fill" style="width:' + pct + '%"></div></div>';
      html += '<div class="band">' + d.score + " / " + d.max + "　·　" + esc(d.band) + "</div></div>";
    });
    html += "</div>";

    html += '<div class="suggestion-box"><b>总体发展建议：</b><br>' + esc(report.overall_suggestion) + "</div>";
    report.dimensions.forEach(function (d) {
      html += '<div class="suggestion-box"><b>' + esc(d.dimension) + "（" + d.score + "/" + d.max + "）：</b><br>" + esc(d.suggestion) + "</div>";
    });
    html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:20px">';
    html += '<button class="btn-ghost" type="button" id="retestBtn">再测一次</button>';
    html += '<a class="btn-primary" style="text-decoration:none;display:inline-flex;align-items:center" href="index.html">返回首页提问</a>';
    html += '<a class="btn-ghost" style="text-decoration:none;display:inline-flex;align-items:center" href="resources.html">查看学习资源</a>';
    html += "</div>";

    wrap.innerHTML = html;
    $("#retestBtn").addEventListener("click", function () {
      wrap.style.display = "none";
      $("#diagFormWrap").style.display = "";
      document.querySelectorAll("input:checked").forEach(function (i) { i.checked = false; });
      document.querySelectorAll("label.on").forEach(function (l) { l.classList.remove("on"); });
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  init();
})();
