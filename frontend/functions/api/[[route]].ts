// ME-AITA Cloudflare Pages Functions — 统一 API 入口
// 对应原 FastAPI 后端全部接口，使用 D1 替代 SQLite，直连智谱 OpenAI 兼容接口。

const SYSTEM_PROMPT = `你是"ME-AITA 教师成长智能体"，由河南大学建设，面向师范生和中小学在职教师，为数字素养提升、教学设计、课堂实践、教研反思和专业成长提供智能支持。

【角色定位】
- 你是一位兼具基础教育一线经验与教育技术专长的教研导师。
- 回答以真实教学应用为导向，具体、可操作，避免空泛套话。

【核心能力】
1. 教学设计：根据学段、学科和教学主题，辅助设计教学目标、教学重难点、教学活动、板书/课件要点与课堂评价。
2. 课堂实践：提供人工智能及数字工具在基础教育中的落地应用建议。
3. 教研反思：辅助开展课例研究、听评课分析、教学反思与教学方案改进。
4. 专业发展：根据教师提出的问题，推荐适合的学习方向、培训主题与成长路径。
5. 师范生支持：辅助微格教学设计、说课稿准备、模拟课堂训练与实习反思。
6. 政策与标准：对教育政策、课程标准等问题，仅在具有可靠依据时提供解读；不得编造政策文件、参考文献或资源链接。

【回答要求】
- 涉及具体教学设计时，先确认或合理假设学段、学科、课时与学情；信息不足时明确请教师补充关键信息。
- 教案与教学建议属于辅助生成内容，请在给出方案后提醒教师结合课程标准、教材版本、学情和实际教学条件审核后使用。
- 需要列举外部资源、政策或文献时，只说明可检索的真实来源类型与检索途径；不虚构具体文件名、链接或文献。
- 使用清晰的结构（分点、小标题、表格），便于阅读与直接用于备课。
- 用中文回答，语气专业、亲切、简洁。`;

const DIMENSIONS = ["数字意识","数字技术知识与技能","数字化教学应用","数字化专业发展","数字社会责任"];
const QUESTION_BANK = [
  {id:"d1q1",dimension:"数字意识",text:"我能认识到数字技术对教学改革和自身专业发展的重要性。"},
  {id:"d1q2",dimension:"数字意识",text:"我主动关注国家教育数字化战略与基础教育信息化相关政策动态。"},
  {id:"d1q3",dimension:"数字意识",text:"面对新的数字工具和教学方式，我愿意主动了解并尝试。"},
  {id:"d2q1",dimension:"数字技术知识与技能",text:"我能熟练使用办公软件（文档、表格、演示）处理教学材料。"},
  {id:"d2q2",dimension:"数字技术知识与技能",text:"我能独立完成教学资源的检索、下载、整理与二次编辑。"},
  {id:"d2q3",dimension:"数字技术知识与技能",text:"我能理解并初步运用人工智能工具（如生成式AI）辅助备课与教学。"},
  {id:"d3q1",dimension:"数字化教学应用",text:"我能使用多媒体和互动工具设计并实施数字化课堂活动。"},
  {id:"d3q2",dimension:"数字化教学应用",text:"我能利用平台或工具开展学情分析、作业布置与学习反馈。"},
  {id:"d3q3",dimension:"数字化教学应用",text:"我能借助数字手段关注学生差异，进行分层或个性化教学调整。"},
  {id:"d4q1",dimension:"数字化专业发展",text:"我会利用网络研修平台、在线课程持续学习提升。"},
  {id:"d4q2",dimension:"数字化专业发展",text:"我能借助数字工具开展课例研究、听评课与教学反思。"},
  {id:"d4q3",dimension:"数字化专业发展",text:"我乐于在教研组或网络社群中分享数字教学经验并协作共创。"},
  {id:"d5q1",dimension:"数字社会责任",text:"我了解并遵守信息安全、数据隐私与网络伦理规范。"},
  {id:"d5q2",dimension:"数字社会责任",text:"我注重引导学生正确、安全、健康地使用数字设备和网络。"},
  {id:"d5q3",dimension:"数字社会责任",text:"我能辨别网络信息真伪，并重视在教学中渗透数字公民教育。"},
];
const IDENTITIES = ["师范生","在职教师","教研员","教育管理者","其他"];
const STAGES = ["小学","初中","高中","其他"];
const SUBJECTS = ["语文","数学","英语","物理","化学","生物","历史","地理","道德与法治","科学","信息技术","体育与健康","音乐","美术","通用","其他"];
const CATEGORIES = ["课程标准","数字素养学习材料","教学设计案例","课堂教学资源","教研资料","AI教学工具使用指南"];
const DIMENSION_SUGGESTIONS = {
  "数字意识":{high:"数字意识较强。建议保持对教育数字化政策的持续关注，并将意识转化为具体的课堂实践行动。",mid:"已有一定数字意识。建议定期阅读教育数字化政策与案例，尝试将AI工具引入一次真实教学环节。",low:"数字意识有待提升。建议从了解《教师数字素养》标准与教育数字化战略开始。"},
  "数字技术知识与技能":{high:"数字技术基础扎实。建议进一步学习数据可视化、AI提示词工程等进阶技能。",mid:"具备一定技术基础。建议重点练习教学资源的检索与二次编辑、AI工具辅助备课。",low:"数字技术技能需要加强。建议从办公软件与资源检索入手。"},
  "数字化教学应用":{high:"数字化教学应用能力突出。建议尝试常态化应用并开展效果对比研究。",mid:"已有数字化教学应用尝试。建议针对学情分析、作业反馈和个性化调整各做一次专项优化。",low:"数字化教学应用尚少。建议从单节课的互动工具入手，小步快跑积累经验。"},
  "数字化专业发展":{high:"数字化专业发展意识强。建议将分散的网络学习整合为系统研修计划。",mid:"有一定研修习惯。建议利用平台研修课程完成专题学习。",low:"数字化研修参与不足。建议先从网络研修平台的免费课程开始。"},
  "数字社会责任":{high:"数字社会责任意识强。建议在教研组或班级中主动开展网络安全与数字伦理教育实践。",mid:"具备基本责任意识。建议系统学习相关法律法规，完善课堂中的数字公民教育。",low:"数字社会责任意识需要提升。建议学习信息安全基础知识和未成年人网络保护要求。"}
};

function json(data, init={}) {
  return new Response(JSON.stringify(data), {
    headers: {"content-type":"application/json; charset=utf-8", ...(init.headers||{})},
    ...init
  });
}

function sse(event, data) {
  return `event: ${event}\ndata: ${JSON.stringify(Object.assign({type:event}, data))}\n\n`;
}

async function ensureSchema(env) {
  const stmts = [
    "CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL DEFAULT '新会话', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS diagnosis_records(id INTEGER PRIMARY KEY AUTOINCREMENT, identity TEXT NOT NULL, stage TEXT NOT NULL, subject TEXT NOT NULL, answers_json TEXT NOT NULL, scores_json TEXT NOT NULL, total_score INTEGER NOT NULL, level TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, source TEXT DEFAULT '', stage TEXT DEFAULT '通用', subject TEXT DEFAULT '通用', category TEXT NOT NULL, content TEXT DEFAULT '', url TEXT DEFAULT '', created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS community_posts(id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL)"
  ];
  for (const sql of stmts) {
    await env.DB.prepare(sql).run();
  }
}

async function seedResources(env) {
  const cnt = await env.DB.prepare("SELECT COUNT(*) AS n FROM resources").first();
  if (cnt && cnt.n > 0) return;
  const seed = await fetch("https://meaita-teacher.pages.dev/seed.json").then(r=>r.ok?r.json():[]).catch(()=>[]);
  // fallback: if seed not yet deployed, embed a minimal list
  const items = seed.length ? seed : [
    {name:"国家中小学智慧教育平台",source:"中华人民共和国教育部",stage:"通用",subject:"通用",category:"课堂教学资源",content:"教育部主导建设的基础教育综合服务平台。",url:"https://basic.smartedu.cn/"},
    {name:"教育部关于印发义务教育课程方案和课程标准（2022年版）的通知",source:"教育部",stage:"小学",subject:"通用",category:"课程标准",content:"义务教育课程方案及16个学科课程标准（2022年版）官方文件。",url:"http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    {name:"《教师数字素养》教育行业标准（JY/T 0646—2022）",source:"教育部",stage:"通用",subject:"通用",category:"数字素养学习材料",content:"教师数字素养标准全文，五维度框架。",url:"http://www.moe.gov.cn/srcsite/A16/s3342/202302/t20230214_1044634.html"},
    {name:"河南大学",source:"河南大学",stage:"通用",subject:"通用",category:"教研资料",content:"ME-AITA 建设单位。",url:"https://www.henu.edu.cn/"}
  ];
  const stmt = env.DB.prepare("INSERT INTO resources(name,source,stage,subject,category,content,url,created_at) VALUES(?,?,?,?,?,?,?,?)");
  const now = new Date().toISOString().replace("T"," ").slice(0,19);
  const batch = items.map(it => [it.name,it.source||"",it.stage||"通用",it.subject||"通用",it.category,it.content||"",it.url||"",now]);
  await env.DB.batch(batch.map(row => stmt.bind(...row)));
}

function nowStr() { return new Date().toISOString().replace("T"," ").slice(0,19); }

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname.replace(/^\/api\/?/, "");
  const method = request.method;
  await ensureSchema(env);
  await seedResources(env);

  // ---------- /api/info ----------
  if (path === "info" && method === "GET") {
    return json({service:"ME-AITA 教师成长智能体", model: env.ZHIPU_MODEL || "glm-4-flash", api_configured: !!env.ZHIPU_API_KEY, version:"1.0.0-cloudflare"});
  }

  // ---------- /api/sessions ----------
  if (path === "sessions" && method === "GET") {
    const r = await env.DB.prepare("SELECT id,title,created_at,updated_at FROM sessions ORDER BY updated_at DESC").all();
    return json({sessions: r.results});
  }
  if (path === "sessions" && method === "POST") {
    const body = await request.json().catch(()=>({}));
    const title = (body.title||"新会话").slice(0,60);
    const now = nowStr();
    const r = await env.DB.prepare("INSERT INTO sessions(title,created_at,updated_at) VALUES(?,?,?)").bind(title,now,now).run();
    const s = await env.DB.prepare("SELECT * FROM sessions WHERE id=?").bind(r.meta.last_row_id).first();
    return json({session: s});
  }

  const mSession = path.match(/^sessions\/(\d+)$/);
  if (mSession) {
    const sid = Number(mSession[1]);
    if (method === "GET") {
      const r = await env.DB.prepare("SELECT id,role,content,created_at FROM messages WHERE session_id=? ORDER BY id ASC").bind(sid).all();
      return json({messages: r.results});
    }
    if (method === "DELETE") {
      await env.DB.prepare("DELETE FROM messages WHERE session_id=?").bind(sid).run();
      await env.DB.prepare("DELETE FROM sessions WHERE id=?").bind(sid).run();
      return json({ok:true});
    }
  }

  const mRename = path.match(/^sessions\/(\d+)\/rename$/);
  if (mRename && method === "POST") {
    const body = await request.json().catch(()=>({}));
    await env.DB.prepare("UPDATE sessions SET title=?, updated_at=? WHERE id=?").bind((body.title||"新会话").slice(0,60), nowStr(), Number(mRename[1])).run();
    return json({ok:true});
  }

  // ---------- /api/chat/stream ----------
  if (path === "chat/stream" && method === "POST") {
    const body = await request.json().catch(()=>({}));
    const message = (body.message||"").trim();
    if (!message) return json({detail:"消息不能为空"},{status:400});
    let sid = body.session_id;
    if (!sid) {
      const r = await env.DB.prepare("INSERT INTO sessions(title,created_at,updated_at) VALUES(?,?,?)").bind(message.slice(0,20), nowStr(), nowStr()).run();
      sid = r.meta.last_row_id;
    }
    await env.DB.prepare("INSERT INTO messages(session_id,role,content,created_at) VALUES(?,?,?,?)").bind(sid,"user",message,nowStr()).run();

    const hist = await env.DB.prepare("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 24").bind(sid).all();
    const msgs = [{role:"system",content:SYSTEM_PROMPT}].concat(hist.results.reverse().map(r => ({role:r.role==="assistant"?"assistant":"user", content:r.content})));

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        controller.enqueue(encoder.encode(sse("meta",{session_id:sid})));
        try {
          const zhRes = await fetch("https://open.bigmodel.cn/api/paas/v4/chat/completions", {
            method:"POST",
            headers:{
              "content-type":"application/json",
              "authorization":"Bearer " + env.ZHIPU_API_KEY
            },
            body: JSON.stringify({
              model: env.ZHIPU_MODEL || "glm-4-flash",
              messages: msgs,
              stream: true,
              temperature: 0.7,
              max_tokens: 2048
            })
          });
          if (!zhRes.ok) {
            const t = await zhRes.text();
            controller.enqueue(encoder.encode(sse("error",{code:"upstream",message:"模型服务异常 ("+zhRes.status+")"})));
            controller.close(); return;
          }
          const reader = zhRes.body.getReader();
          const dec = new TextDecoder();
          let buf = "", full = "";
          while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buf += dec.decode(value, {stream:true});
            const lines = buf.split("\n");
            buf = lines.pop();
            for (const line of lines) {
              if (!line.startsWith("data:")) continue;
              const data = line.slice(5).trim();
              if (data === "[DONE]") continue;
              try {
                const j = JSON.parse(data);
                const delta = j.choices?.[0]?.delta?.content || "";
                if (delta) {
                  full += delta;
                  controller.enqueue(encoder.encode(sse("delta",{content:delta})));
                }
              } catch(e) {}
            }
          }
          if (full) {
            await env.DB.prepare("INSERT INTO messages(session_id,role,content,created_at) VALUES(?,?,?,?)").bind(sid,"assistant",full,nowStr()).run();
            await env.DB.prepare("UPDATE sessions SET updated_at=? WHERE id=?").bind(nowStr(),sid).run();
          }
          controller.enqueue(encoder.encode(sse("done",{session_id:sid, content:full})));
        } catch(e) {
          controller.enqueue(encoder.encode(sse("error",{code:"unknown",message:"服务异常："+(e.message||"")})));
        }
        controller.close();
      }
    });
    return new Response(stream, {headers:{"content-type":"text/event-stream","cache-control":"no-cache","connection":"keep-alive"}});
  }

  // ---------- /api/diagnosis ----------
  if (path === "diagnosis/meta" && method === "GET") {
    return json({trial:true, trial_note:"本测评为试用版基础测评，依据《教师数字素养》（JY/T 0646—2022）五维度设计，非正式能力评价。", identities:IDENTITIES, stages:STAGES, subjects:SUBJECTS});
  }
  if (path === "diagnosis/questions" && method === "GET") {
    return json({trial:true, dimensions_note:"五维度", questions:QUESTION_BANK});
  }
  if (path === "diagnosis/submit" && method === "POST") {
    const body = await request.json().catch(()=>({}));
    const answers = body.answers||{};
    const scores = {}; DIMENSIONS.forEach(d=>scores[d]=0);
    const counts = {}; DIMENSIONS.forEach(d=>counts[d]=0);
    for (const q of QUESTION_BANK) {
      const v = Number(answers[q.id]);
      if (v>=1 && v<=5) { scores[q.dimension]+=v; counts[q.dimension]++; }
    }
    DIMENSIONS.forEach(d => scores[d] += (3-counts[d])*1);
    const total = DIMENSIONS.reduce((s,d)=>s+scores[d],0);
    const level = total>=60?"优秀":total>=48?"良好":total>=36?"基础":"待提升";
    const dims = DIMENSIONS.map(d=>{
      const ratio = scores[d]/15;
      const band = ratio>=0.8?"high":ratio>=0.55?"mid":"low";
      const label = ratio>=0.8?"较强":ratio>=0.55?"中等":"待提升";
      return {dimension:d, score:scores[d], max:15, ratio:Math.round(ratio*100)/100, band:label, suggestion:DIMENSION_SUGGESTIONS[d][band]};
    });
    const overall = {
      "优秀":"整体数字素养水平较高。建议发挥示范作用，将数字化经验系统化输出。",
      "良好":"整体数字素养良好。建议对照《教师数字素养》标准查漏补缺。",
      "基础":"已具备一定数字素养基础。建议从得分最低的两个维度入手系统学习。",
      "待提升":"数字素养提升空间较大。建议先建立学习计划，循序渐进。"
    }[level];
    const report = {trial_note:"试用版基础测评结果，非正式能力评价。", scores, total, max_total:75, level, dimensions:dims, overall_suggestion:overall};
    await env.DB.prepare("INSERT INTO diagnosis_records(identity,stage,subject,answers_json,scores_json,total_score,level,created_at) VALUES(?,?,?,?,?,?,?,?)")
      .bind(body.identity||"教师", body.stage||"通用", body.subject||"通用", JSON.stringify(answers), JSON.stringify(scores), total, level, nowStr()).run();
    return json({ok:true, report});
  }
  if (path === "diagnosis/records" && method === "GET") {
    const r = await env.DB.prepare("SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT 20").all();
    return json({records: r.results});
  }

  // ---------- /api/resources ----------
  if (path === "resources/categories" && method === "GET") return json({categories:CATEGORIES});
  if (path === "resources" && method === "GET") {
    const stage = url.searchParams.get("stage")||"全部";
    const subject = url.searchParams.get("subject")||"全部";
    const category = url.searchParams.get("category")||"全部";
    const q = (url.searchParams.get("q")||"").trim();
    let sql = "SELECT * FROM resources WHERE 1=1";
    const binds = [];
    if (stage!=="全部") { sql += " AND (stage=? OR stage='通用')"; binds.push(stage); }
    if (subject!=="全部") { sql += " AND (subject=? OR subject='通用')"; binds.push(subject); }
    if (category!=="全部") { sql += " AND category=?"; binds.push(category); }
    if (q) { sql += " AND (name LIKE ? OR content LIKE ? OR source LIKE ?)"; binds.push(`%${q}%`,`%${q}%`,`%${q}%`); }
    sql += " ORDER BY id ASC";
    const r = await env.DB.prepare(sql).bind(...binds).all();
    return json({total:r.results.length, categories:CATEGORIES, resources:r.results});
  }

  // ---------- /api/community/posts ----------
  if (path === "community/posts" && method === "GET") {
    const r = await env.DB.prepare("SELECT id,author,title,body,created_at FROM community_posts ORDER BY id DESC LIMIT 100").all();
    return json({posts:r.results});
  }
  if (path === "community/posts" && method === "POST") {
    const body = await request.json().catch(()=>({}));
    if (!body.title || !body.body || body.title.length<2 || body.body.length<2) return json({ok:false,message:"标题和正文至少各2字"},{status:400});
    const r = await env.DB.prepare("INSERT INTO community_posts(author,title,body,created_at) VALUES(?,?,?,?)")
      .bind((body.author||"匿名教师").slice(0,30), body.title.slice(0,80), body.body.slice(0,2000), nowStr()).run();
    return json({ok:true, id:r.meta.last_row_id});
  }
  const mPost = path.match(/^community\/posts\/(\d+)$/);
  if (mPost && method === "DELETE") {
    await env.DB.prepare("DELETE FROM community_posts WHERE id=?").bind(Number(mPost[1])).run();
    return json({ok:true});
  }

  return json({detail:"Not Found: "+path},{status:404});
}
