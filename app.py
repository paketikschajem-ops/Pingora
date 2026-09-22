from flask import Flask, request, jsonify, render_template_string, session
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.secret_key = "pingora-dev-secret"
DB = Path(__file__).with_name("pingora.db")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def setup():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS chats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT NOT NULL,
        avatar TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Online',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        time TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'sent',
        FOREIGN KEY(chat_id) REFERENCES chats(id)
    );
    """)
    if con.execute("SELECT COUNT(*) FROM chats").fetchone()[0] == 0:
        demo = [
            ("Maya Chen", "@mayachen", "MC", "Online"),
            ("Alex Rivera", "@alexr", "AR", "Away"),
            ("Design Team", "@design-team", "DT", "5 members"),
            ("Noah Williams", "@noahw", "NW", "Offline"),
        ]
        for name, username, avatar, status in demo:
            cur = con.execute(
                "INSERT INTO chats(name,username,avatar,status,created_at) VALUES(?,?,?,?,?)",
                (name, username, avatar, status, datetime.now().isoformat())
            )
            cid = cur.lastrowid
            samples = {
                "Maya Chen": [("them", "Hey! Did you see the new design?"),
                              ("me", "Yeah, it looks really clean. I like the new spacing."),
                              ("them", "Same! I think we're almost ready 🚀")],
                "Alex Rivera": [("them", "Want to test the new build later?"),
                                ("me", "Absolutely. Send it when it's ready.")],
                "Design Team": [("them", "Sam uploaded the latest mockups."),
                                ("them", "The purple accent feels much better.")],
                "Noah Williams": [("me", "Thanks for the recommendation!"),
                                  ("them", "Anytime 😄")]
            }
            for sender, text in samples.get(name, []):
                con.execute(
                    "INSERT INTO messages(chat_id,sender,text,time,state) VALUES(?,?,?,?,?)",
                    (cid, sender, text, datetime.now().strftime("%H:%M"), "read")
                )
    con.commit()
    con.close()

def chat_json(row, con):
    msgs = con.execute(
        "SELECT id,sender,text,time,state FROM messages WHERE chat_id=? ORDER BY id",
        (row["id"],)
    ).fetchall()
    return {
        "id": row["id"], "name": row["name"], "username": row["username"],
        "avatar": row["avatar"], "status": row["status"],
        "messages": [dict(x) for x in msgs]
    }

HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pingora</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080a11;color:#eef0f8;font:14px system-ui,sans-serif}
button,input,textarea{font:inherit}.app{height:100vh;display:grid;grid-template-columns:300px 1fr 245px;background:radial-gradient(circle at 60% 0,#272052,#0b0d16 42%,#080a11 75%)}
.side,.details{background:#0b0e16ee}.side{border-right:1px solid #202432;padding:18px 12px;display:flex;flex-direction:column}
.brand{font-size:21px;font-weight:800;display:flex;gap:10px;align-items:center;padding:0 10px 18px}.logo,.avatar{display:grid;place-items:center;font-weight:800}
.logo{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,#8b5cf6,#4f7cff)}
.avatar{width:43px;height:43px;flex:none;border-radius:14px;font-size:12px;background:linear-gradient(135deg,#7c5cff,#3f7cff)}
.me,.chat{display:flex;align-items:center;gap:10px;padding:10px;border-radius:14px}.me{background:#111520;border:1px solid #232738}
small{color:#858ca3;font-size:11px;display:block}.search{margin:12px 0;background:#111520;border:1px solid #24283a;border-radius:13px;padding:9px;color:#858ca3}
.search input{border:0;outline:0;background:none;color:white;width:90%}.chat{width:100%;border:0;background:none;color:white;text-align:left;cursor:pointer}
.chat:hover,.chat.active{background:#171a28}.meta{min-width:0;flex:1}.top,.bottom{display:flex;justify-content:space-between;gap:7px}.bottom{color:#777e92;font-size:11px}
.bottom span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.new,.secondary{border:1px solid #2a2e40;color:#ddd;border-radius:13px;padding:10px;cursor:pointer}
.new{margin-top:auto;background:#171a27}.secondary{background:#111520;margin-top:8px;width:100%}
.main{min-width:0;display:flex;flex-direction:column}.head{height:76px;border-bottom:1px solid #202432;display:flex;justify-content:space-between;align-items:center;padding:0 22px;background:#0c0f18cc}
.person{display:flex;align-items:center;gap:10px}.actions button,.attach,.emoji{background:none;border:0;color:#a1a8bc;cursor:pointer;font-size:18px}
.messages{flex:1;overflow:auto;padding:28px 6vw;display:flex;flex-direction:column;gap:9px}.msg{max-width:72%;animation:pop .2s}.mine{align-self:flex-end}
.bubble{background:#151925;border:1px solid #25293a;padding:10px 13px;border-radius:16px 16px 16px 5px;line-height:1.45;white-space:pre-wrap}
.mine .bubble{background:linear-gradient(135deg,#6046bf,#5162dc);border-color:#7560df;border-radius:16px 16px 5px 16px}.foot{text-align:right;font-size:9px;color:#7c8398;margin-top:4px}
.mine .foot{color:#d8dcff}.msg-tools{display:none;font-size:10px;margin-top:3px;gap:5px}.mine:hover .msg-tools{display:flex;justify-content:flex-end}
.msg-tools button{border:0;background:#111520;color:#aaa;border-radius:6px;padding:3px 6px;cursor:pointer}
.typing{height:0;opacity:0;padding-left:6vw;color:#858ca0;font-size:11px;transition:.2s}.typing.show{height:24px;opacity:1}
.composer{display:flex;gap:8px;align-items:center;padding:12px 22px 18px}.input{flex:1;background:#121520;border:1px solid #282c3c;border-radius:17px;padding:4px 10px 4px 14px;display:flex}
.input textarea{flex:1;resize:none;background:none;border:0;outline:0;color:white;padding:9px}.send{width:42px;height:42px;border:0;border-radius:14px;background:linear-gradient(135deg,#805cff,#4f73ff);color:white;cursor:pointer}
.details{border-left:1px solid #202432;padding:35px 20px;text-align:center}.details .avatar{width:76px;height:76px;margin:auto;border-radius:24px}
.pill{display:inline-block;margin:10px;background:#111821;border:1px solid #242b37;padding:6px 10px;border-radius:20px;color:#98a0b4;font-size:10px}
.section{text-align:left;border-top:1px solid #202432;padding-top:18px;margin-top:18px;color:#7f869b}.section p{color:#c2c7d5}
.modal{position:fixed;inset:0;background:#0009;display:none;place-items:center;z-index:5}.modal.open{display:grid}.card{background:#121520;border:1px solid #2a2e40;border-radius:20px;padding:25px;width:min(390px,90vw)}
.card input{width:100%;margin:10px 0;padding:11px;border-radius:10px;border:1px solid #30354a;background:#0d1018;color:white}
.card button{padding:10px 14px;border:0;border-radius:10px;background:#6651d9;color:white;cursor:pointer}
.file{display:none}@keyframes pop{from{opacity:0;transform:translateY(5px)}to{opacity:1}}
@media(max-width:1050px){.app{grid-template-columns:280px 1fr}.details{display:none}}@media(max-width:700px){.app{display:block}.side{display:none}.head{padding:0 14px}.messages{padding:20px 14px}.composer{padding:10px 12px}.msg{max-width:86%}}
</style>
</head>
<body>
<div class="app">
<aside class="side">
<div class="brand"><span class="logo">P</span>Pingora</div>
<div class="me"><div class="avatar">YO</div><div><b>You</b><small>Available</small></div></div>
<div class="search">⌕ <input id="search" placeholder="Search chats..."></div>
<div id="list">{% for c in chats %}<button class="chat {% if loop.first %}active{% endif %}" data-id="{{c.id}}">
<div class="avatar">{{c.avatar}}</div><div class="meta"><div class="top"><b>{{c.name}}</b><small>{{c.time}}</small></div>
<div class="bottom"><span>{{c.last}}</span></div></div></button>{% endfor %}</div>
<button class="new" id="new">＋ New chat</button>
<button class="secondary" id="settings">⚙ Settings</button>
</aside>
<main class="main">
<header class="head"><div class="person"><div class="avatar" id="ha">MC</div><div><b id="hn">Maya Chen</b><small>● <span id="hs">Online</span></small></div></div>
<div class="actions"><button id="info" title="Profile">ⓘ</button></div></header>
<section class="messages" id="messages"></section>
<div class="typing" id="typing">••• <span id="typingName">Maya</span> is typing…</div>
<div class="composer"><label class="attach" title="Attach file">＋<input class="file" id="file" type="file"></label>
<div class="input"><textarea id="input" rows="1" placeholder="Write a message..."></textarea><button class="emoji" id="emoji">☺</button></div>
<button class="send" id="send">➤</button></div>
</main>
<aside class="details"><div class="avatar" id="da">MC</div><h2 id="dn">Maya Chen</h2><small id="du">@mayachen</small><div class="pill">● <span id="ds">Online</span></div>
<div class="section">ABOUT<p>Designing useful things and collecting good ideas.</p></div>
<div class="section">MESSAGES<p id="count">0 messages</p></div></aside>
</div>

<div class="modal" id="modal"><div class="card"><h2 id="modalTitle">New chat</h2><input id="modalInput" placeholder="Chat name or username"><div style="text-align:right"><button id="cancel">Cancel</button> <button id="confirm">Create</button></div></div></div>

<script>
let chats={{chats|tojson}},cur=chats[0];
const $=id=>document.getElementById(id), M=$('messages');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function render(){
 M.innerHTML=cur.messages.length?cur.messages.map(m=>'<div class="msg '+(m.sender==='me'?'mine':'')+'"><div class="bubble">'+esc(m.text)+'<div class="foot">'+esc(m.time)+(m.sender==='me'?'　✓✓':'')+'</div></div>'+(m.sender==='me'?'<div class="msg-tools"><button onclick="editMsg('+m.id+')">Edit</button><button onclick="deleteMsg('+m.id+')">Delete</button></div>':'')+'</div>').join(''):'<div style="margin:auto;color:#777">Start the conversation ✨</div>';
 M.scrollTop=M.scrollHeight;$('count').textContent=cur.messages.length+' message'+(cur.messages.length===1?'':'s');
}
function select(id){cur=chats.find(c=>c.id==id)||cur;document.querySelectorAll('.chat').forEach(x=>x.classList.toggle('active',x.dataset.id==cur.id));
$('ha').textContent=cur.avatar;$('hn').textContent=cur.name;$('hs').textContent=cur.status;$('da').textContent=cur.avatar;$('dn').textContent=cur.name;$('du').textContent=cur.username;$('ds').textContent=cur.status;$('typingName').textContent=cur.name.split(' ')[0];render();}
async function send(){
 const i=$('input'),t=i.value.trim();if(!t)return;
 const r=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:cur.id,text:t})});
 const d=await r.json();if(d.ok){cur.messages.push(d.message);i.value='';render();}else alert(d.error||'Could not send message');
}
async function editMsg(id){const m=cur.messages.find(x=>x.id===id);const t=prompt('Edit message:',m.text);if(t===null||!t.trim())return;
const r=await fetch('/api/message/'+cur.id+'/'+id+'/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});const d=await r.json();if(d.ok){m.text=d.message.text;m.time=d.message.time;render();}}
async function deleteMsg(id){if(!confirm('Delete this message?'))return;const r=await fetch('/api/message/'+cur.id+'/'+id,{method:'DELETE'});const d=await r.json();if(d.ok){cur.messages=cur.messages.filter(x=>x.id!==id);render();}}
function modal(open){$('modal').classList.toggle('open',open);if(open){$('modalInput').value='';$('modalInput').focus();}}
document.querySelectorAll('.chat').forEach(x=>x.onclick=()=>select(x.dataset.id));
$('send').onclick=send;$('input').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}};
$('emoji').onclick=()=>{$('input').value+=' 😊';$('input').focus()};
$('search').oninput=e=>document.querySelectorAll('.chat').forEach(x=>x.style.display=x.innerText.toLowerCase().includes(e.target.value.toLowerCase())?'flex':'none');
$('new').onclick=()=>modal(true);$('cancel').onclick=()=>modal(false);
$('confirm').onclick=async()=>{const n=$('modalInput').value.trim();if(!n)return;const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})});const d=await r.json();if(d.ok)location.reload()};
$('info').onclick=()=>alert(cur.name+'\n'+cur.username+'\nStatus: '+cur.status);
$('settings').onclick=()=>alert('Pingora settings\n\nTheme: Dark\nNotifications: Enabled\nMessages are saved in pingora.db');
$('file').onchange=e=>{if(e.target.files[0]){$('input').value+=' 📎 '+e.target.files[0].name;$('input').focus();e.target.value=''}};
setTimeout(()=>{$('typing').classList.add('show');setTimeout(()=>$('typing').classList.remove('show'),1800)},700);
select(cur.id);
</script>
</body>
</html>"""

@app.get("/")
def index():
    setup()
    con = db()
    rows = con.execute("SELECT * FROM chats ORDER BY id DESC").fetchall()
    data = []
    for row in rows:
        msgs = con.execute("SELECT text FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT 1", (row["id"],)).fetchone()
        data.append({**dict(row), "last": msgs["text"] if msgs else "Start a conversation", "time": ""})
    con.close()
    return render_template_string(HTML, chats=data)

@app.get("/api/chats")
def get_chats():
    setup()
    con = db()
    rows = con.execute("SELECT * FROM chats ORDER BY id DESC").fetchall()
    result = [chat_json(r, con) for r in rows]
    con.close()
    return jsonify(chats=result)

@app.post("/api/message")
def message():
    setup()
    d = request.get_json() or {}
    try: chat_id = int(d.get("chat_id"))
    except (TypeError, ValueError): return jsonify(ok=False, error="Invalid chat"), 400
    text = str(d.get("text", "")).strip()
    if not text: return jsonify(ok=False, error="Message is empty"), 400
    con = db()
    if not con.execute("SELECT id FROM chats WHERE id=?", (chat_id,)).fetchone():
        con.close(); return jsonify(ok=False, error="Chat not found"), 404
    now = datetime.now().strftime("%H:%M")
    cur = con.execute("INSERT INTO messages(chat_id,sender,text,time,state) VALUES(?,?,?,?,?)", (chat_id,"me",text,now,"sent"))
    con.commit()
    row = con.execute("SELECT id,sender,text,time,state FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
    con.close()
    return jsonify(ok=True, message=dict(row))

@app.post("/api/message/<int:chat_id>/<int:message_id>/edit")
def edit_message(chat_id, message_id):
    setup()
    d = request.get_json() or {}
    text = str(d.get("text", "")).strip()
    if not text: return jsonify(ok=False, error="Message is empty"), 400
    con = db()
    cur = con.execute("UPDATE messages SET text=?, time=? WHERE id=? AND chat_id=? AND sender='me'", (text, datetime.now().strftime("%H:%M"), message_id, chat_id))
    con.commit()
    row = con.execute("SELECT id,sender,text,time,state FROM messages WHERE id=?", (message_id,)).fetchone()
    con.close()
    if cur.rowcount == 0 or not row: return jsonify(ok=False, error="Message not found"), 404
    return jsonify(ok=True, message=dict(row))

@app.delete("/api/message/<int:chat_id>/<int:message_id>")
def delete_message(chat_id, message_id):
    setup()
    con = db()
    cur = con.execute("DELETE FROM messages WHERE id=? AND chat_id=? AND sender='me'", (message_id, chat_id))
    con.commit(); con.close()
    if cur.rowcount == 0: return jsonify(ok=False, error="Message not found"), 404
    return jsonify(ok=True)

@app.post("/api/chat")
def new_chat():
    setup()
    d = request.get_json() or {}
    name = str(d.get("name", "")).strip() or "New Chat"
    username = name if name.startswith("@") else "@"+name.lower().replace(" ","")
    avatar = "".join(x[0] for x in name.split()[:2]).upper() or "NC"
    con = db()
    cur = con.execute("INSERT INTO chats(name,username,avatar,status,created_at) VALUES(?,?,?,?,?)", (name,username,avatar,"Online",datetime.now().isoformat()))
    con.commit()
    row = con.execute("SELECT * FROM chats WHERE id=?", (cur.lastrowid,)).fetchone()
    con.close()
    return jsonify(ok=True, chat=dict(row))

@app.post("/api/reset")
def reset():
    con = db()
    con.execute("DELETE FROM messages"); con.execute("DELETE FROM chats"); con.commit(); con.close()
    setup()
    return jsonify(ok=True)

setup()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
