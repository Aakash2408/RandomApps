"""HTML for the two pages. Plain HTML + a little vanilla JS, no build step."""
from __future__ import annotations

import html

from . import config as _config

_CSS = """
:root{--ink:#14161a;--muted:#5b616b;--line:#e5e7eb;--bg:#fff;--soft:#f6f7f9;--brand:#0f5bd8;--brand-ink:#fff;
--high:#b42318;--high-bg:#fdecea;--med:#8a5300;--med-bg:#fff4dc;--low:#1d7044;--low-bg:#e7f6ed}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Sans Arabic",sans-serif;
color:var(--ink);background:var(--bg);line-height:1.55}
a{color:var(--brand)}.wrap{max-width:68rem;margin:0 auto;padding:0 1.25rem}
nav{display:flex;justify-content:space-between;align-items:center;padding:1rem 0}
nav .logo{font-weight:800;font-size:1.15rem;text-decoration:none;color:var(--ink)}
nav .links a{margin-left:1.1rem;text-decoration:none;color:var(--muted)}
.btn{display:inline-block;background:var(--brand);color:var(--brand-ink);border:0;border-radius:10px;
padding:.75rem 1.2rem;font-size:1rem;font-weight:600;text-decoration:none;cursor:pointer}
.btn.ghost{background:var(--bg);color:var(--brand);border:1.5px solid var(--brand)}
.btn:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #f2a900;outline-offset:2px}
.hero{padding:3rem 0 2rem;text-align:center}.hero h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.1;margin:.2rem 0 1rem;letter-spacing:-.02em}
.hero p.sub{font-size:1.15rem;color:var(--muted);max-width:40rem;margin:0 auto 1.5rem}
.pill{display:inline-block;background:var(--soft);color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:.25rem .8rem;font-size:.85rem}
.tool{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:1.25rem;margin:1rem 0 3rem}
@media(max-width:820px){.tool{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--bg);border:1px solid var(--line);border-radius:14px;padding:1.25rem;box-shadow:0 1px 2px rgba(0,0,0,.04)}
label{display:block;font-weight:600;font-size:.9rem;margin:.7rem 0 .25rem}
input,select{width:100%;padding:.6rem .7rem;font-size:1rem;border:1px solid #8a9099;border-radius:8px;background:var(--bg);color:var(--ink)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.result-empty{color:var(--muted);text-align:center;padding:2.5rem 1rem}
.score{display:flex;align-items:baseline;gap:.75rem;margin-bottom:.5rem}.score b{font-size:3rem;line-height:1}
.band{display:inline-block;padding:.15rem .7rem;border-radius:999px;font-weight:700;font-size:.9rem}
.band.high{color:var(--high);background:var(--high-bg)}.band.medium{color:var(--med);background:var(--med-bg)}.band.low{color:var(--low);background:var(--low-bg)}
ul.reasons{padding-left:1.1rem}ul.reasons li{margin:.3rem 0}
.verdict{background:var(--soft);border-radius:10px;padding:.75rem;margin-top:.75rem}
section{padding:2.5rem 0}h2{font-size:1.8rem;letter-spacing:-.01em;margin:0 0 1rem;text-align:center}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}@media(max-width:820px){.steps{grid-template-columns:minmax(0,1fr)}}
.steps .card h3{margin:.2rem 0 .4rem}.steps .n{color:var(--brand);font-weight:800}
.plans{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;align-items:stretch}
@media(max-width:820px){.plans{grid-template-columns:minmax(0,1fr)}}
.plan{display:flex;flex-direction:column}.plan .price{font-size:2.2rem;font-weight:800}.plan .price span{font-size:1rem;color:var(--muted);font-weight:500}
.plan ul{padding-left:1.1rem;flex:1}.plan.best{border:2px solid var(--brand)}
.faq details{border-bottom:1px solid var(--line);padding:.9rem 0}.faq summary{font-weight:600;cursor:pointer}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:.9rem;padding:1.5rem 0 2.5rem}
.note{color:var(--muted);font-size:.88rem}.err{color:var(--high);font-weight:600}
code{background:var(--soft);padding:.1rem .35rem;border-radius:5px}
.visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
"""

_COUNTRIES = [("AE", "United Arab Emirates"), ("SA", "Saudi Arabia"), ("KW", "Kuwait"), ("QA", "Qatar"),
              ("BH", "Bahrain"), ("OM", "Oman"), ("EG", "Egypt"), ("MA", "Morocco"), ("TR", "Türkiye"),
              ("IN", "India"), ("PK", "Pakistan"), ("ID", "Indonesia"), ("PH", "Philippines"), ("MY", "Malaysia"),
              ("VN", "Vietnam"), ("MX", "Mexico"), ("BR", "Brazil"), ("CO", "Colombia"), ("PE", "Peru"),
              ("CL", "Chile"), ("PL", "Poland"), ("RO", "Romania"), ("CZ", "Czechia"), ("GR", "Greece"),
              ("IT", "Italy"), ("ES", "Spain"), ("US", "United States"), ("GB", "United Kingdom")]


def _country_options(selected: str = "AE") -> str:
    return "".join(f'<option value="{c}"{" selected" if c == selected else ""}>{html.escape(n)}</option>'
                   for c, n in _COUNTRIES)


def _shell(title: str, body: str, description: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(description)}">
<style>{_CSS}</style></head><body>{body}</body></html>"""


def _nav() -> str:
    return """<div class="wrap"><nav aria-label="Main"><a class="logo" href="/">CODGuard</a>
<div class="links"><a href="/#how">How it works</a><a href="/#pricing">Pricing</a><a href="/app">Log in</a></div></nav></div>"""


def landing(s: "_config.Settings", plans: dict) -> str:
    def plan_card(p, best=False):
        url = s.checkout_urls.get(p.key) or "#pricing"
        disabled = "" if s.checkout_urls.get(p.key) else ' aria-disabled="true"'
        return f"""<div class="card plan{' best' if best else ''}"><h3>{p.name}{' · most popular' if best else ''}</h3>
<div class="price">${p.usd}<span>/month</span></div>
<ul><li><b>{p.checks:,}</b> COD orders checked a month</li><li>Upload your Shopify order export, or any CSV</li>
<li>Riskiest orders first, with the reason for each</li><li>API for automatic checks</li></ul>
<a class="btn{'' if best else ' ghost'}" href="{html.escape(url)}"{disabled}>Start with {p.name}</a></div>"""

    contact = (f' · <a href="mailto:{html.escape(s.contact_email)}">{html.escape(s.contact_email)}</a>'
               if s.contact_email else "")
    body = f"""{_nav()}
<main>
<div class="wrap hero">
  <span class="pill">For stores that sell with Cash on Delivery</span>
  <h1>Stop shipping COD orders<br>that come back.</h1>
  <p class="sub">CODGuard checks each cash-on-delivery order's address and phone before you ship. It flags fake numbers,
  addresses a courier can't find, and test orders, and it knows how addresses work in 45+ countries.</p>
  <a class="btn" href="#try">Check an address free</a> <a class="btn ghost" href="#pricing">See pricing</a>
</div>

<div class="wrap" id="try">
 <div class="tool">
  <form class="card" id="checker" novalidate>
   <h2 style="text-align:left;font-size:1.3rem">Try it on a real order</h2>
   <label for="country">Country</label><select id="country" name="country_code">{_country_options()}</select>
   <label for="name">Customer name</label><input id="name" name="name" autocomplete="off" placeholder="Fatima Al Mansoori">
   <label for="address1">Address</label><input id="address1" name="address1" autocomplete="off" placeholder="Villa 12, Street 7, Al Barsha 2">
   <div class="row"><div><label for="city">City</label><input id="city" name="city" autocomplete="off" placeholder="Dubai"></div>
   <div><label for="zip">Postal code</label><input id="zip" name="zip" autocomplete="off" placeholder="optional in UAE"></div></div>
   <div class="row"><div><label for="phone">Phone</label><input id="phone" name="phone" autocomplete="off" inputmode="tel" placeholder="050 123 4567"></div>
   <div><label for="total">Order value <span class="note">(optional)</span></label><input id="total" name="order_total" inputmode="decimal" placeholder="250"></div></div>
   <p style="margin-top:1rem"><button class="btn" type="submit">Check this order</button>
   <button class="btn ghost" type="button" id="example">Load a risky example</button></p>
   <p class="note">Free: {s.free_checks_per_day} checks a day. Nothing you enter is stored.</p>
  </form>
  <div class="card" id="result" aria-live="polite"><div class="result-empty">Enter an order to see its risk score and why.</div></div>
 </div>
</div>

<section id="how"><div class="wrap"><h2>How it works</h2><div class="steps">
 <div class="card"><div class="n">1</div><h3>Export your orders</h3><p>Download today's orders as a CSV from Shopify or your store platform. Nothing to install.</p></div>
 <div class="card"><div class="n">2</div><h3>Upload to CODGuard</h3><p>Every COD order gets a 0–100 risk score with plain-English reasons, riskiest first.</p></div>
 <div class="card"><div class="n">3</div><h3>Call before you ship</h3><p>Confirm the few risky orders with the customer before they go out. Ship the rest as normal.</p></div>
</div></div></section>

<section id="pricing" style="background:var(--soft)"><div class="wrap"><h2>Simple monthly pricing</h2>
<p class="note" style="text-align:center;margin-top:-.5rem">Cancel any time. Checkout and invoices by Lemon Squeezy.</p>
<div class="plans">{plan_card(plans['starter'])}{plan_card(plans['growth'], best=True)}{plan_card(plans['pro'])}</div></div></section>

<section class="faq"><div class="wrap" style="max-width:46rem"><h2>Questions</h2>
<details><summary>What does it actually check?</summary><p>The phone number is valid for the delivery country and isn't made up.
The postal code has the right format, or isn't expected at all (UAE, Qatar). The address has a house, flat, building or street number.
It isn't placeholder text like "test" or "asdf", and the order value isn't unusually high. In India it also checks the PIN code matches the state.</p></details>
<details><summary>Does it flag landmark addresses in the Gulf?</summary><p>No. "Near Safa Park, Jumeirah" is a normal UAE address, and couriers there call ahead.
In countries where a landmark-only address is a real risk, such as India and Mexico, it is flagged.</p></details>
<details><summary>Which stores does it work with?</summary><p>Anything that exports orders as CSV. It reads Shopify's order export directly,
and for other platforms it looks for columns like address, city, postal code, country and phone.</p></details>
<details><summary>Is my customers' data stored?</summary><p>No. Files are scored in memory and the result is sent straight back to you.
We keep only a count of how many orders you've checked this month.</p></details>
<details><summary>How do I log in after subscribing?</summary><p>Your receipt email from Lemon Squeezy includes a license key.
Paste it on the <a href="/app">log in</a> page. It works for as long as your subscription is active.</p></details>
</div></section>
</main>
<footer><div class="wrap">© CODGuard{contact} · Payments by Lemon Squeezy</div></footer>
<script>
const f=document.getElementById('checker'),out=document.getElementById('result');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const verdict={{high:"Don't ship this yet. Call the customer first.",medium:"Confirm with the customer before you ship.",low:"Looks deliverable. Ship as normal."}};
document.getElementById('example').onclick=()=>{{f.country_code.value='AE';f.name.value='test';f.address1.value='near mall';
 f.city.value='';f.zip.value='';f.phone.value='0500000000';f.order_total.value='';f.requestSubmit();}};
f.onsubmit=async e=>{{e.preventDefault();
 const d={{}};for(const k of ['country_code','name','address1','city','zip','phone'])d[k]=f[k].value;
 const t=parseFloat(f.order_total.value);if(t>0)d.order_total=t;
 out.innerHTML='<div class="result-empty">Checking…</div>';
 try{{const r=await fetch('/api/check',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(d)}});
  const j=await r.json();if(!r.ok){{out.innerHTML='<p class="err">'+esc(j.error||'Something went wrong')+'</p><p><a class="btn" href="#pricing">See plans</a></p>';return;}}
  const label={{high:'High risk',medium:'Medium risk',low:'Low risk'}}[j.band];
  out.innerHTML='<div class="score"><b>'+j.risk+'</b><span class="band '+j.band+'">'+label+'</span></div>'
   +(j.reasons.length?'<ul class="reasons">'+j.reasons.map(x=>'<li>'+esc(x.message)+'</li>').join('')+'</ul>':'<p>No problems found.</p>')
   +'<div class="verdict">'+verdict[j.band]+'</div><p class="note">'+j.free_checks_left_today+' free checks left today. '
   +'<a href="#pricing">Check a whole day\\'s orders at once →</a></p>';
 }}catch(err){{out.innerHTML='<p class="err">Could not reach the server. Try again.</p>';}}
}};
</script>"""
    return _shell("CODGuard · Stop shipping COD orders that come back", body,
                  "Check cash-on-delivery orders for fake phones and undeliverable addresses before you ship. 45+ countries.")


def app_page(s: "_config.Settings") -> str:
    body = f"""{_nav()}
<main class="wrap" style="max-width:44rem;padding-bottom:3rem">
<h1>Check your orders</h1>
<div class="card" id="login">
 <label for="key">License key</label>
 <input id="key" autocomplete="off" spellcheck="false" placeholder="From your Lemon Squeezy receipt email">
 <p><button class="btn" id="go" type="button">Continue</button></p>
 <p class="note">No license key yet? <a href="/#pricing">Pick a plan</a>. The key stays in this browser tab only.</p>
 <p id="login-msg" role="alert"></p>
</div>
<div class="card" id="upload" hidden>
 <p id="plan"></p>
 <form id="bulk">
  <label for="file">Order export (CSV)</label><input id="file" name="file" type="file" accept=".csv,text/csv" required>
  <label for="dc">Country to assume when the file has none</label>
  <select id="dc" name="default_country"><option value="">(file has a country column)</option>{_country_options('')}</select>
  <p><button class="btn" type="submit">Check orders</button> <button class="btn ghost" type="button" id="logout">Log out</button></p>
 </form>
 <p class="note">Shopify: Orders → Export → current page or date range → CSV. You get the file back with a risk score
 and reasons on every order, riskiest first.</p>
 <p id="bulk-msg" role="alert" aria-live="polite"></p>
</div>
<details class="card" style="margin-top:1rem"><summary><b>API for automatic checks</b></summary>
<p>Each call uses one check from your plan.</p>
<pre style="white-space:pre-wrap;overflow-wrap:anywhere"><code>curl -X POST {html.escape(s.site_url)}/api/v1/check \\
  -H "Authorization: Bearer YOUR_LICENSE_KEY" -H "Content-Type: application/json" \\
  -d '{{"country_code":"AE","name":"Fatima","address1":"Villa 12, Street 7","city":"Dubai","phone":"0501234567"}}'</code></pre></details>
</main>
<script>
const $=id=>document.getElementById(id);
async function showPlan(){{
 const key=sessionStorage.getItem('cg_key');if(!key)return;
 const r=await fetch('/api/v1/usage',{{headers:{{Authorization:'Bearer '+key}}}});const j=await r.json();
 if(!r.ok){{sessionStorage.removeItem('cg_key');$('login-msg').textContent=j.error;$('login-msg').className='err';return;}}
 $('login').hidden=true;$('upload').hidden=false;
 $('plan').textContent=j.plan+' plan · '+j.used_this_month.toLocaleString()+' of '+j.checks_per_month.toLocaleString()+' checks used this month';
}}
$('go').onclick=()=>{{const k=$('key').value.trim();if(!k)return;sessionStorage.setItem('cg_key',k);$('login-msg').textContent='Checking…';showPlan();}};
$('logout').onclick=()=>{{sessionStorage.removeItem('cg_key');location.reload();}};
$('bulk').onsubmit=async e=>{{e.preventDefault();const msg=$('bulk-msg');msg.className='';msg.textContent='Checking orders…';
 const fd=new FormData(e.target);
 const r=await fetch('/api/bulk',{{method:'POST',headers:{{Authorization:'Bearer '+sessionStorage.getItem('cg_key')}},body:fd}});
 if(!r.ok){{const j=await r.json().catch(()=>({{}}));msg.className='err';msg.textContent=j.error||'Upload failed';return;}}
 const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);
 a.download=(r.headers.get('Content-Disposition')||'').split('filename="')[1]?.replace('"','')||'orders-codguard.csv';a.click();
 msg.textContent=r.headers.get('X-CODGuard-Orders')+' orders checked, '+r.headers.get('X-CODGuard-Flagged')+' need a call before shipping. Your file has downloaded.';
 showPlan();
}};
showPlan();
</script>"""
    return _shell("CODGuard · Check your orders", body, "Upload your COD order export and get a risk score for every order.")
