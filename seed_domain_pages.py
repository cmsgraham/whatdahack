#!/usr/bin/env python3
"""
seed_domain_pages.py
Creates / updates CTFd Pages for each CTF domain.

Run on server:
  docker exec ctfd-ctfd-1 python /opt/CTFd/seed_domain_pages.py
"""

import sys, os
sys.path.insert(0, '/opt/CTFd')
os.chdir('/opt/CTFd')

from CTFd import create_app
from CTFd.models import db, Pages

app = create_app()

# ─────────────────────────────────────────────────────────────────────────────
#  Shared CSS injected into every page
# ─────────────────────────────────────────────────────────────────────────────
SHARED_STYLE = """
<style>
/* ── Domain page tokens ────────────────────────────────────────────────── */
:root,[data-bs-theme="light"]{
  --dp-bg:#f6f8fa;--dp-surface:#ffffff;--dp-border:#d0d7de;
  --dp-text:#0f172a;--dp-muted:#5b6b7c;
  --dp-accent:#0369a1;--dp-accent-rgb:3,105,161;
  --dp-accent2:#059669;--dp-accent2-rgb:5,150,105;
  --dp-hero-bg:linear-gradient(135deg,#e8f0fb 0%,#dce8f7 100%);
}
[data-bs-theme="dark"]{
  --dp-bg:#06090f;--dp-surface:#0d1420;--dp-border:#1e2a3a;
  --dp-text:#e2e8f0;--dp-muted:#7c8fa6;
  --dp-accent:#38bdf8;--dp-accent-rgb:56,189,248;
  --dp-accent2:#00ff88;--dp-accent2-rgb:0,255,136;
  --dp-hero-bg:linear-gradient(135deg,#0d1420 0%,#111927 100%);
}
/* ── Layout ─────────────────────────────────────────────────────────────── */
.dp-wrap{max-width:960px;margin:0 auto;padding:1.5rem .5rem 3rem;}
/* ── Hero ────────────────────────────────────────────────────────────────── */
.dp-hero{
  background:var(--dp-hero-bg);
  border:1px solid var(--dp-border);
  border-radius:14px;
  padding:2.8rem 2rem 2.4rem;
  text-align:center;
  margin-bottom:2.75rem;
  position:relative;
  overflow:hidden;
}
.dp-hero::after{
  content:'';position:absolute;inset:0;
  background:radial-gradient(circle at 60% 40%,rgba(var(--dp-accent-rgb),.06) 0%,transparent 70%);
  pointer-events:none;
}
.dp-hero-icon{font-size:3rem;display:block;margin-bottom:.75rem;line-height:1;}
.dp-hero h1{font-size:2rem;font-weight:700;color:var(--dp-accent);margin-bottom:.6rem;}
.dp-hero .dp-hero-lead{color:var(--dp-muted);font-size:1rem;max-width:650px;margin:0 auto;line-height:1.65;}
/* ── Section ─────────────────────────────────────────────────────────────── */
.dp-section{margin-bottom:2.75rem;}
.dp-section-title{
  font-size:1.1rem;font-weight:700;color:var(--dp-text);
  display:flex;align-items:center;gap:.55rem;
  padding-bottom:.55rem;
  border-bottom:2px solid rgba(var(--dp-accent-rgb),.25);
  margin-bottom:1.35rem;
}
.dp-section-title span{color:var(--dp-accent);}
/* ── Resource card ───────────────────────────────────────────────────────── */
.dp-card{
  display:flex;flex-direction:column;
  text-decoration:none!important;
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-radius:10px;
  padding:1.15rem 1.35rem;
  height:100%;
  transition:border-color .18s,box-shadow .18s,transform .18s;
  color:inherit;
}
.dp-card:hover{
  border-color:rgba(var(--dp-accent-rgb),.6);
  box-shadow:0 6px 24px rgba(0,0,0,.12);
  transform:translateY(-2px);
}
.dp-card-title{
  font-size:.92rem;font-weight:700;
  color:var(--dp-accent);
  margin-bottom:.35rem;
  display:flex;align-items:center;gap:.4rem;
}
.dp-card-desc{
  font-size:.82rem;color:var(--dp-muted);
  flex:1;line-height:1.55;margin-bottom:.85rem;
}
.dp-tags{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:auto;}
.dp-tag{
  font-size:.68rem;padding:2px 9px;border-radius:999px;
  background:rgba(var(--dp-accent-rgb),.1);
  color:var(--dp-accent);
  border:1px solid rgba(var(--dp-accent-rgb),.22);
  font-weight:500;
}
/* ── Overview block ─────────────────────────────────────────────────────── */
.dp-overview{
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-radius:12px;
  padding:1.6rem 1.8rem;
  margin-bottom:2.75rem;
}
.dp-overview-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:1.6rem;
}
@media(max-width:640px){.dp-overview-grid{grid-template-columns:1fr;}}
.dp-overview-label{
  font-size:.68rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dp-accent);margin-bottom:.55rem;
}
.dp-overview-text{
  font-size:.88rem;color:var(--dp-text);line-height:1.72;
}
.dp-overview-text p{margin-bottom:.65rem;}
.dp-overview-text p:last-child{margin-bottom:0;}
.dp-examples-wrap{margin-top:1.35rem;}
.dp-examples-label{
  font-size:.68rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dp-accent2);margin-bottom:.65rem;
}
.dp-examples{display:flex;flex-wrap:wrap;gap:.45rem;}
.dp-example-pill{
  font-size:.75rem;padding:.28rem .75rem;
  border-radius:999px;
  background:rgba(var(--dp-accent2-rgb),.1);
  border:1px solid rgba(var(--dp-accent2-rgb),.25);
  color:var(--dp-text);
  font-weight:500;
}
.dp-example-pill code{
  background:none;padding:0;color:inherit;
  font-family:ui-monospace,monospace;
  font-size:.72rem;
}
/* ── Tip box ─────────────────────────────────────────────────────────────── */
.dp-tip{
  background:var(--dp-surface);
  border-left:3px solid var(--dp-accent2);
  padding:.9rem 1.1rem;
  border-radius:0 8px 8px 0;
  font-size:.86rem;color:var(--dp-text);
  margin-bottom:.75rem;
  line-height:1.6;
}
.dp-tip strong{color:var(--dp-accent2);}
/* ── Sample challenge card ──────────────────────────────────────────────── */
.dp-chall{
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-radius:12px;
  overflow:hidden;
  margin-bottom:2.75rem;
}
.dp-chall-header{
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.6rem;
  padding:1rem 1.4rem;
  background:rgba(var(--dp-accent-rgb),.06);
  border-bottom:1px solid var(--dp-border);
}
.dp-chall-name{
  font-size:1.05rem;font-weight:700;color:var(--dp-accent);
  display:flex;align-items:center;gap:.5rem;
}
.dp-chall-meta{
  display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;
}
.dp-chall-badge{
  font-size:.68rem;font-weight:700;padding:.18rem .6rem;
  border-radius:999px;text-transform:uppercase;letter-spacing:.05em;
}
.dp-chall-badge--cat{
  background:rgba(var(--dp-accent-rgb),.15);
  color:var(--dp-accent);
  border:1px solid rgba(var(--dp-accent-rgb),.25);
}
.dp-chall-badge--easy   {background:rgba(5,150,105,.14);color:#059669;border:1px solid rgba(5,150,105,.3);}
.dp-chall-badge--medium {background:rgba(234,179,8,.14);color:#ca8a04;border:1px solid rgba(234,179,8,.3);}
.dp-chall-badge--hard   {background:rgba(239,68,68,.14);color:#dc2626;border:1px solid rgba(239,68,68,.3);}
.dp-chall-pts{
  font-size:.72rem;font-weight:700;
  color:var(--dp-muted);
}
.dp-chall-body{
  padding:1.25rem 1.4rem;
}
.dp-chall-scenario{
  font-size:.88rem;color:var(--dp-text);line-height:1.72;
  margin-bottom:1rem;
}
.dp-chall-files{
  display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:1rem;
}
.dp-chall-file{
  font-size:.73rem;font-family:ui-monospace,monospace;
  padding:.22rem .65rem;border-radius:6px;
  background:var(--dp-bg);border:1px solid var(--dp-border);
  color:var(--dp-muted);
  display:inline-flex;align-items:center;gap:.3rem;
}
.dp-chall-solve{
  margin-top:1rem;
  background:var(--dp-bg);
  border-radius:8px;
  padding:1rem 1.2rem;
}
.dp-chall-solve-label{
  font-size:.68rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dp-accent2);
  margin-bottom:.55rem;
}
.dp-chall-steps{list-style:none;padding:0;margin:0;}
.dp-chall-steps li{
  font-size:.83rem;color:var(--dp-text);line-height:1.65;
  padding:.22rem 0;
  display:flex;align-items:baseline;gap:.5rem;
}
.dp-chall-steps li::before{
  content:counter(step);
  counter-increment:step;
  font-size:.65rem;font-weight:800;
  color:var(--dp-accent2);
  background:rgba(var(--dp-accent2-rgb),.12);
  border:1px solid rgba(var(--dp-accent2-rgb),.25);
  border-radius:999px;
  width:1.3rem;height:1.3rem;
  display:inline-flex;align-items:center;justify-content:center;
  flex-shrink:0;
  margin-top:.15rem;
}
.dp-chall-steps{counter-reset:step;}
.dp-chall-flag{
  font-family:ui-monospace,monospace;
  font-size:.8rem;
  color:var(--dp-accent2);
  background:rgba(var(--dp-accent2-rgb),.08);
  padding:.3rem .75rem;
  border-radius:6px;
  border:1px solid rgba(var(--dp-accent2-rgb),.2);
  display:inline-block;
  margin-top:.65rem;
}
/* ── Landing page grid ───────────────────────────────────────────────────── */
.dp-domain-card{
  display:flex;flex-direction:column;
  text-decoration:none!important;
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-radius:12px;
  padding:1.6rem 1.5rem;
  height:100%;
  transition:border-color .18s,box-shadow .18s,transform .18s;
  color:inherit;
}
.dp-domain-card:hover{
  border-color:rgba(var(--dp-accent-rgb),.6);
  box-shadow:0 8px 28px rgba(0,0,0,.13);
  transform:translateY(-3px);
}
.dp-domain-card-icon{font-size:2rem;margin-bottom:.6rem;display:block;}
.dp-domain-card-name{font-size:1rem;font-weight:700;color:var(--dp-accent);margin-bottom:.35rem;}
.dp-domain-card-desc{font-size:.82rem;color:var(--dp-muted);flex:1;line-height:1.55;}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Helper builders
# ─────────────────────────────────────────────────────────────────────────────

def _tags(tags):
    return "".join(f'<span class="dp-tag">{t}</span>' for t in tags)


def _card(name, url, desc, tags):
    return f"""
      <div class="col-sm-6 col-lg-4">
        <a href="{url}" target="_blank" rel="noopener noreferrer" class="dp-card">
          <div class="dp-card-title">
            <i class="fas fa-external-link-alt" style="font-size:.7rem;opacity:.6;"></i>
            {name}
          </div>
          <div class="dp-card-desc">{desc}</div>
          <div class="dp-tags">{_tags(tags)}</div>
        </a>
      </div>"""


def _tip(text):
    return f'<div class="dp-tip"><strong>💡 Tip:</strong> {text}</div>'


def _section(icon_class, title, cards_html):
    return f"""
    <div class="dp-section">
      <h2 class="dp-section-title">
        <i class="{icon_class}"></i> {title}
      </h2>
      <div class="row g-3">{cards_html}</div>
    </div>"""


def _tips_section(tips):
    tips_html = "\n".join(_tip(t) for t in tips)
    return f"""
    <div class="dp-section">
      <h2 class="dp-section-title">
        <i class="fas fa-lightbulb"></i> Getting Started Tips
      </h2>
      {tips_html}
    </div>"""


def _example_pill(text):
    return f'<span class="dp-example-pill">{text}</span>'


def _sample_challenge(name, category, difficulty, points, scenario, files, steps, flag):
    """Renders a mock CTF challenge card.
    difficulty: 'easy' | 'medium' | 'hard'
    files: list of filename strings
    steps: list of step strings
    """
    diff_labels = {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'}
    files_html = "".join(
        f'<span class="dp-chall-file"><i class="fas fa-file-code"></i>{f}</span>'
        for f in files
    )
    steps_html = "".join(f'<li>{s}</li>' for s in steps)
    return f"""
    <div class="dp-section">
      <h2 class="dp-section-title">
        <i class="fas fa-flag"></i> Sample Challenge
      </h2>
      <div class="dp-chall">
        <div class="dp-chall-header">
          <div class="dp-chall-name"><i class="fas fa-flag"></i> {name}</div>
          <div class="dp-chall-meta">
            <span class="dp-chall-badge dp-chall-badge--cat">{category}</span>
            <span class="dp-chall-badge dp-chall-badge--{difficulty}">{diff_labels[difficulty]}</span>
            <span class="dp-chall-pts">{points} pts</span>
          </div>
        </div>
        <div class="dp-chall-body">
          <div class="dp-chall-scenario">{scenario}</div>
          <div class="dp-chall-files">{files_html}</div>
          <div class="dp-chall-solve">
            <div class="dp-chall-solve-label">How to solve it</div>
            <ol class="dp-chall-steps">{steps_html}</ol>
            <div class="dp-chall-flag">{flag}</div>
          </div>
        </div>
      </div>
    </div>"""


def _overview_section(what, how_it_works, examples):
    """what: str (HTML), how_it_works: str (HTML), examples: list[str]"""
    pills = "".join(_example_pill(e) for e in examples)
    return f"""
    <div class="dp-overview">
      <div class="dp-overview-grid">
        <div>
          <div class="dp-overview-label">What is it?</div>
          <div class="dp-overview-text">{what}</div>
        </div>
        <div>
          <div class="dp-overview-label">How it works in a CTF</div>
          <div class="dp-overview-text">{how_it_works}</div>
        </div>
      </div>
      <div class="dp-examples-wrap">
        <div class="dp-examples-label">Example challenge types</div>
        <div class="dp-examples">{pills}</div>
      </div>
    </div>"""


def _page(icon, title, lead, official, training, tips, tools=None, overview=None, sample=None):
    off_html = "".join(_card(*r) for r in official)
    train_html = "".join(_card(*r) for r in training)

    tool_section = ""
    if tools:
        tool_html = "".join(_card(*r) for r in tools)
        tool_section = _section("fas fa-tools", "Essential Tools", tool_html)

    overview_block = ""
    if overview:
        overview_block = _overview_section(*overview)

    sample_block = ""
    if sample:
        sample_block = _sample_challenge(*sample)

    return SHARED_STYLE + f"""
<div class="dp-wrap">

  <!-- Hero -->
  <div class="dp-hero">
    <span class="dp-hero-icon">{icon}</span>
    <h1>{title}</h1>
    <p class="dp-hero-lead">{lead}</p>
  </div>

  {overview_block}
  {sample_block}
  {_section("fas fa-link", "Official Resources &amp; Standards", off_html)}
  {_section("fas fa-graduation-cap", "Free Training &amp; Practice", train_html)}
  {tool_section}
  {_tips_section(tips)}

</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  LANDING PAGE: /resources
# ─────────────────────────────────────────────────────────────────────────────

DOMAINS = [
    ("🌐", "Web Security",              "resources/web",               "Exploit web apps — XSS, SQLi, SSRF, CORS, OAuth and beyond."),
    ("🔐", "Cryptography",              "resources/crypto",            "Break and build ciphers, hash functions, and protocols."),
    ("🔬", "Reverse Engineering",       "resources/reverse-engineering","Disassemble, decompile, and understand compiled binaries."),
    ("🔍", "Forensics",                 "resources/forensics",         "Recover deleted files, analyse memory dumps, and trace attackers."),
    ("💥", "Binary Exploitation (Pwn)", "resources/pwn",               "Buffer overflows, ROP chains, heap exploits, and shellcode."),
    ("🎲", "Miscellaneous",             "resources/misc",              "Steganography, scripting, encoding puzzles, and more."),
    ("👁️", "OSINT",                    "resources/osint",             "Open-source intelligence — find anything using only public data."),
    ("☁️", "Cloud / DevOps",           "resources/cloud",             "Misconfigurations in AWS, Azure, GCP, Docker, and Kubernetes."),
    ("📱", "Mobile",                    "resources/mobile",            "Hack Android and iOS apps — from APK reversing to runtime hooks."),
    ("🔧", "Hardware / IoT",            "resources/hardware",          "UART, JTAG, firmware analysis, and embedded device exploitation."),
]


def build_landing():
    cards = ""
    for icon, name, route, desc in DOMAINS:
        cards += f"""
      <div class="col-sm-6 col-lg-4 col-xl-3">
        <a href="/{route}" class="dp-domain-card">
          <span class="dp-domain-card-icon">{icon}</span>
          <div class="dp-domain-card-name">{name}</div>
          <div class="dp-domain-card-desc">{desc}</div>
        </a>
      </div>"""

    return SHARED_STYLE + f"""
<div class="dp-wrap">
  <div class="dp-hero">
    <span class="dp-hero-icon">📚</span>
    <h1>CTF Resources</h1>
    <p class="dp-hero-lead">
      Curated links to official documentation, free training platforms, hands-on labs,
      and essential tools — one page per challenge domain.
    </p>
  </div>
  <div class="dp-section">
    <h2 class="dp-section-title"><i class="fas fa-bolt"></i> Quick Reference</h2>
    <div class="row g-3">
      <div class="col-12">
        <a href="/resources/cheatsheet" class="dp-domain-card" style="flex-direction:row;align-items:center;gap:1.1rem;">
          <span class="dp-domain-card-icon" style="margin-bottom:0;">🚩</span>
          <div>
            <div class="dp-domain-card-name">CTF Cheatsheet</div>
            <div class="dp-domain-card-desc">Identify unknown encodings &amp; ciphers at a glance, pick the right RSA attack, and jump to the best tool for every category.</div>
          </div>
        </a>
      </div>
    </div>
  </div>
  <div class="dp-section">
    <h2 class="dp-section-title"><i class="fas fa-th"></i> Challenge Domains</h2>
    <div class="row g-3">{cards}</div>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  1. WEB SECURITY
# ─────────────────────────────────────────────────────────────────────────────

WEB = _page(
    icon="🌐",
    title="Web Security",
    lead="Web challenges test your ability to find and exploit vulnerabilities in websites and APIs. Topics range from classic injection attacks to modern OAuth/JWT flaws, SSRF, GraphQL abuse, and prototype pollution.",
    overview=(
        """<p>Web security is the practice of finding and fixing vulnerabilities in websites, web applications, and APIs. Attackers exploit these flaws to steal data, hijack accounts, execute commands on servers, or pivot deeper into an organisation's infrastructure.</p>
<p>It is one of the most impactful security disciplines because nearly every business has a public-facing web presence. A single misconfigured endpoint can expose millions of user records.</p>""",
        """<p>In a CTF, you are given a URL (or a source-code dump) and must find a vulnerability to read a hidden flag. Challenges are self-contained web apps that deliberately contain one or more bugs — your job is to discover and exploit them before other teams.</p>
<p>Common workflows: intercept HTTP traffic with Burp Suite → inspect parameters and cookies → fuzz inputs → research the bug class → craft a proof-of-concept → extract the flag from the server response or database.</p>""",
        ["SQL Injection (dump the DB)", "XSS → cookie theft", "SSRF → cloud metadata",
         "IDOR (access another user's data)", "JWT algorithm confusion",
         "SSTI (server-side template injection)", "Path traversal / LFI",
         "OAuth state bypass", "GraphQL introspection abuse", "CORS misconfiguration",
         "XXE (external entity injection)", "Command injection via form field"]
    ),
    sample=(
        "Blind Order",
        "Web", "medium", 250,
        """A small e-commerce site lets you sort products by column name via a <code>?sort=</code> query parameter.
        The application passes this value directly into a SQL <code>ORDER BY</code> clause — sanitising only for spaces.
        There is no visible error output, making this a <em>blind SQL injection</em>.""",
        ["shop.zip"],
        [
            "Intercept the <code>GET /products?sort=name</code> request in Burp Suite.",
            "Notice the parameter is reflected in an <code>ORDER BY</code> clause by testing <code>sort=name ASC</code> vs <code>sort=name DESC</code>.",
            "Use a boolean-based payload: <code>sort=(CASE WHEN 1=1 THEN name ELSE price END)</code> — the order changes, confirming blind injection.",
            "Write a Python loop using <code>SUBSTR()</code> to extract the <code>flag</code> column from the <code>secrets</code> table letter by letter.",
            "Assemble the bytes into the flag string.",
        ],
        "FLAG{bl1nd_0rd3r_by_expl01t}"
    ),
    official=[
        ("OWASP Foundation", "https://owasp.org",
         "The Open Web Application Security Project — the gold standard for web app security guidance.", ["Foundation", "Standards"]),
        ("OWASP Top 10", "https://owasp.org/www-project-top-ten/",
         "The ten most critical web application security risks, updated regularly.", ["Reference", "Standards"]),
        ("OWASP Cheat Sheet Series", "https://cheatsheetseries.owasp.org",
         "Concise, developer-focused cheat sheets covering XXE, CSRF, XSS, SQLi and dozens more.", ["Reference"]),
        ("CWE Top 25", "https://cwe.mitre.org/top25/",
         "MITRE's list of the most dangerous software weaknesses.", ["Reference"]),
        ("MDN Web Docs — Security", "https://developer.mozilla.org/en-US/docs/Web/Security",
         "Mozilla's canonical documentation on browser security, CSP, and CORS.", ["Docs"]),
        ("Web Security on RFC Editor", "https://www.rfc-editor.org",
         "Official IETF RFCs for HTTP, TLS, OAuth 2.0, and other web standards.", ["Standards"]),
    ],
    training=[
        ("PortSwigger Web Security Academy", "https://portswigger.net/web-security",
         "Completely free learning platform with 200+ interactive labs covering every major web vuln.", ["Free", "Labs", "Beginner→Advanced"]),
        ("OWASP Juice Shop", "https://owasp.org/www-project-juice-shop/",
         "Intentionally insecure Node.js web app with 100+ challenges from beginner to advanced.", ["Free", "Lab App"]),
        ("OWASP WebGoat", "https://owasp.org/www-project-webgoat/",
         "Deliberately insecure app designed to teach web security lessons step-by-step.", ["Free", "Lab App"]),
        ("TryHackMe — Web Fundamentals", "https://tryhackme.com/path/outline/web",
         "Guided learning path covering HTTP, web enumeration, OWASP Top 10, and common exploits.", ["Free Tier", "Guided"]),
        ("HackTheBox Academy — Web Attacks", "https://academy.hackthebox.com/module/details/134",
         "Hands-on module on XSS, SQLi, IDOR, SSRF, and more with real lab environments.", ["Free Tier", "Labs"]),
        ("PentesterLab", "https://pentesterlab.com",
         "Progressive exercises from basic web bugs to advanced CVE replicas. Many exercises are free.", ["Free Tier", "Labs"]),
        ("DVWA", "https://dvwa.co.uk",
         "Damn Vulnerable Web Application — classic self-hosted practice target with adjustable difficulty.", ["Free", "Lab App"]),
        ("picoCTF", "https://picoctf.org",
         "Carnegie Mellon's beginner-friendly CTF platform with a large Web category.", ["Free", "CTF"]),
    ],
    tools=[
        ("Burp Suite Community", "https://portswigger.net/burp/communitydownload",
         "The industry-standard web proxy for intercepting and modifying HTTP traffic.", ["Free", "Proxy"]),
        ("OWASP ZAP", "https://www.zaproxy.org",
         "Open-source web scanner and proxy — great free alternative to Burp Suite.", ["Free", "Open Source"]),
        ("sqlmap", "https://sqlmap.org",
         "Automatic SQL injection detection and exploitation tool.", ["Free", "Open Source"]),
        ("ffuf", "https://github.com/ffuf/ffuf",
         "Fast web fuzzer for directory busting, parameter fuzzing, and subdomain discovery.", ["Free", "Open Source"]),
    ],
    tips=[
        "Start every web challenge by mapping the app: enumerate endpoints, parameters, cookies, and headers before attempting exploits.",
        "PortSwigger Web Security Academy is the single best free resource — complete the SQLi, XSS, and SSRF labs first.",
        "Set up Burp Suite's browser extension and develop the habit of inspecting every HTTP request/response.",
        "Read writeups after every challenge you solve or give up on — patterns repeat across competitions.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  2. CRYPTOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────

CRYPTO = _page(
    icon="🔐",
    title="Cryptography",
    lead="Crypto challenges require you to break ciphers, identify weaknesses in custom implementations, and exploit mathematical flaws in everything from Caesar shifts to RSA, elliptic curves, and stream ciphers.",
    overview=(
        """<p>Cryptography is the science of securing information through mathematical transformations. It underpins everything from HTTPS and password storage to digital signatures and end-to-end messaging.</p>
<p>In security, the goal is often the opposite — <em>breaking</em> cryptographic schemes that are poorly designed or incorrectly implemented. Even mathematically sound algorithms can be vulnerable when developers misuse them.</p>""",
        """<p>In a CTF, you receive ciphertext, a public key, an encryption oracle, or a custom encryption script and must recover the plaintext flag. Challenges test your ability to spot mathematical weaknesses, abuse implementation mistakes, or apply known academic attacks.</p>
<p>Common workflow: identify the algorithm → check for known vulnerabilities (e.g. small RSA exponent, reused IV) → apply the appropriate mathematical attack using Python/SageMath → decrypt the flag.</p>""",
        ["RSA small-exponent attack (e=3)", "Repeating-key XOR",
         "CBC bit-flipping", "Padding oracle (PKCS#7)",
         "Hash length extension", "ECDSA nonce reuse (k-reuse)",
         "Wiener's RSA attack (small d)", "AES-ECB mode (detect repeated blocks)",
         "Vigenère / frequency analysis", "Diffie-Hellman small subgroup",
         "Common-modulus RSA attack", "Substitute classical cipher (Caesar, ROT13)"]
    ),
    sample=(
        "Tiny Exponent",
        "Crypto", "easy", 100,
        """You intercepted an RSA-encrypted message sent to three different recipients, all sharing the same public exponent <code>e = 3</code>.
        You have the three ciphertexts <code>c1, c2, c3</code> and their corresponding moduli <code>n1, n2, n3</code>.
        The plaintext is short enough that <code>m³ &lt; n1·n2·n3</code>.""",
        ["challenge.py", "output.txt"],
        [
            "Recognise the setup: same message, same <code>e=3</code>, three different moduli — this is Håstad's broadcast attack.",
            "Compute <code>C = CRT([c1,c2,c3], [n1,n2,n3])</code> using the Chinese Remainder Theorem in Python (<code>sympy.crt</code> or manual implementation).",
            "Take the integer cube root of <code>C</code>: <code>m = iroot(C, 3)</code>.",
            "Convert the integer <code>m</code> to bytes: <code>long_to_bytes(m)</code> from the <code>Crypto.Util.number</code> module.",
        ],
        "FLAG{h4st4d_br04dc4st_3=3}"
    ),
    official=[
        ("NIST Cryptographic Standards (CSRC)", "https://csrc.nist.gov",
         "Official NIST guidance on block ciphers, hash functions, digital signatures, and key derivation.", ["Standards", "NIST"]),
        ("IACR Cryptology ePrint Archive", "https://eprint.iacr.org",
         "Free repository of cryptography research papers including attack proofs and new algorithm designs.", ["Research", "Papers"]),
        ("RFC Editor — Crypto RFCs", "https://www.rfc-editor.org/search/rfc_search_detail.php?title=crypto",
         "IETF standards for TLS, AES-GCM, RSA, and other deployed cryptographic protocols.", ["Standards"]),
        ("SageMath", "https://www.sagemath.org",
         "Open-source mathematics system essential for attacking number-theory-based problems (RSA, ECC, DLP).", ["Tool", "Open Source"]),
    ],
    training=[
        ("CryptoPals", "https://cryptopals.com",
         "The classic set of 48 practical crypto challenges — attacks on real algorithms from Set 1 (basics) to Set 8 (ECDH).", ["Free", "Challenges", "Highly Recommended"]),
        ("CryptoHack", "https://cryptohack.org",
         "Interactive platform with challenges covering AES, RSA, elliptic curves, hash functions, and more.", ["Free", "Challenges", "Community"]),
        ("Dan Boneh — Cryptography I (Coursera)", "https://www.coursera.org/learn/crypto",
         "Stanford professor Dan Boneh's rigorous free-audit course covering stream ciphers through authenticated encryption.", ["Free Audit", "Course", "Stanford"]),
        ("Khan Academy — Cryptography", "https://www.khanacademy.org/computing/computer-science/cryptography",
         "Gentle introduction to ancient ciphers, modular arithmetic, Diffie-Hellman, and RSA.", ["Free", "Beginner"]),
        ("Practical Cryptography for Developers", "https://cryptobook.nakov.com",
         "Free online textbook covering hashes, MACs, symmetric & asymmetric encryption, and digital signatures.", ["Free", "Book"]),
        ("Mystery Twister C3", "https://www.mysterytwister.org",
         "Puzzle-style crypto challenges from level 1 (classical ciphers) to level 4 (cutting-edge attacks).", ["Free", "Challenges"]),
        ("id0-rsa.pub CTF Crypto Write-ups", "https://id0-rsa.pub",
         "Curated crypto CTF problems with structured difficulty levels — excellent for RSA practice.", ["Free", "Challenges"]),
    ],
    tools=[
        ("SageMath", "https://www.sagemath.org",
         "Open-source maths system for number theory, polynomial rings, and abstract algebra.", ["Free", "Open Source"]),
        ("RsaCtfTool", "https://github.com/RsaCtfTool/RsaCtfTool",
         "Automated RSA attack tool that tries dozens of known weaknesses against a given public key.", ["Free", "Open Source"]),
        ("CyberChef", "https://gchq.github.io/CyberChef/",
         "GCHQ's 'Cyber Swiss Army Knife' — encode/decode/encrypt/decrypt in the browser.", ["Free", "Browser"]),
        ("dcode.fr", "https://www.dcode.fr/en",
         "Identifies and decodes hundreds of classical and modern cipher schemes automatically.", ["Free", "Browser"]),
    ],
    tips=[
        "If the challenge gives you ciphertext and a key, identify the algorithm first. CyberChef's 'Magic' tool can detect many schemes automatically.",
        "For RSA: always check for small exponent (e=3), common factor attacks, LSB oracle, Wiener's attack, or unpadded textbook RSA.",
        "CryptoPals sets 1–4 are universally recommended even if you are experienced — they build essential attack intuition.",
        "Learn basic Python number theory: Modular inverse (pow(a,-1,n) in Python 3.8+), GCD (math.gcd), and factor via sympy.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  3. REVERSE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

REVERSE = _page(
    icon="🔬",
    title="Reverse Engineering",
    lead="RE challenges ask you to understand programs without access to source code. You'll read assembly, decompile binaries, trace execution, defeat anti-debugging, and ultimately extract flags hidden in logic.",
    overview=(
        """<p>Reverse engineering (RE) is the process of analysing a compiled program — without its source code — to understand what it does. Security engineers use RE to analyse malware, audit closed-source software, and find vulnerabilities in firmware.</p>
<p>It requires knowledge of CPU architectures (x86, ARM), calling conventions, compilation artifacts, and common obfuscation techniques. The goal is to reconstruct intent from raw bytes and machine instructions.</p>""",
        """<p>In a CTF, you receive a compiled binary (ELF, PE, APK, or firmware image) and must figure out the correct input that causes it to print the flag, or locate a hard-coded secret inside it. No source code is provided.</p>
<p>Common workflow: run <code>file</code> + <code>strings</code> + <code>checksec</code> → open in Ghidra/IDA → identify the validation function → trace the logic → derive the required input or patch the binary.</p>""",
        ["Find the hardcoded flag in strings", "Keygen / serial crackme",
         "Obfuscated logic (XOR decode loop)", "Anti-debug bypass (ptrace check)",
         "Packed binary (UPX unpack)", "Custom bytecode VM interpreter",
         "License key validation reversal", "Go / Rust binary decompilation",
         "ARM firmware flag extraction", "Dynamic analysis with GDB",
         "Self-modifying code", "C++ vtable tracing"]
    ),
    sample=(
        "KeyCheck",
        "Reverse Engineering", "easy", 150,
        """You are given a Linux ELF binary that asks for a password and prints <em>"Access granted — here is your flag"</em> if correct, otherwise <em>"Wrong!"</em>.
        The binary is stripped (no function names) and was compiled with <code>-O2</code>.""",
        ["keychecker"],
        [
            "Run <code>strings keychecker | grep -i flag</code> — nothing obvious. Run <code>file</code> and <code>checksec</code> to understand the binary.",
            "Open in Ghidra. Find <code>main</code> via the entry-point symbol. Decompile it.",
            "Identify a <code>strcmp()</code> call comparing your input to a hard-coded string — Ghidra shows the string in the decompilation view.",
            "The comparison string is the password. Run the binary and enter it to confirm the flag is printed.",
        ],
        "FLAG{gh1dra_str1ng_1s_all_u_n33d}"
    ),
    official=[
        ("Ghidra", "https://ghidra-sre.org",
         "Free, open-source reverse engineering suite from the NSA. Disassembles and decompiles most architectures.", ["Free", "NSA", "Open Source"]),
        ("IDA Free", "https://hex-rays.com/ida-free/",
         "The free version of the industry-standard IDA Pro disassembler — supports x86/x64 and ARM.", ["Free", "Disassembler"]),
        ("radare2", "https://radare.org",
         "Powerful open-source RE framework with disassembly, debugging, scripting, and binary patching.", ["Free", "Open Source"]),
        ("Binary Ninja Cloud", "https://cloud.binary.ninja",
         "Free cloud-based binary analysis with a modern decompiler. No install required.", ["Free", "Browser"]),
        ("x64dbg", "https://x64dbg.com",
         "Open-source, user-friendly debugger for Windows x64/x32 executables.", ["Free", "Debugger", "Windows"]),
    ],
    training=[
        ("Crackmes.one", "https://crackmes.one",
         "Large library of user-submitted crackme binaries rated by difficulty. Perfect daily practice.", ["Free", "Challenges"]),
        ("OpenSecurityTraining2", "https://p.ost2.fyi",
         "Free, in-depth university-style courses on x86-64 assembly, RE fundamentals, and malware analysis.", ["Free", "Courses"]),
        ("MalwareUnicorn Workshops", "https://malwareunicorn.org/#/workshops",
         "Free hands-on practical RE workshops by Amanda Rousseau covering Windows internals and malware.", ["Free", "Workshop"]),
        ("challenges.re", "https://challenges.re",
         "Collection of RE exercises with step-by-step hints and solutions from Dennis Yurichev.", ["Free", "Challenges"]),
        ("Azeria Labs — ARM Assembly", "https://azeria-labs.com/writing-arm-assembly-part-1/",
         "Excellent free series on ARM32/64 assembly for RE on mobile and embedded targets.", ["Free", "ARM"]),
        ("picoCTF — Reverse Engineering", "https://picoctf.org",
         "Beginner-friendly RE problems with guided hints. Great entry point.", ["Free", "Beginner"]),
        ("HackTheBox Academy — Reverse Engineering", "https://academy.hackthebox.com",
         "Structured modules covering disassembly, decompilation, anti-analysis, and crackmes.", ["Free Tier", "Labs"]),
    ],
    tools=[
        ("Ghidra", "https://ghidra-sre.org",
         "NSA decompiler/disassembler — most commonly used free tool for CTF RE.", ["Free", "Decompiler"]),
        ("GDB + pwndbg", "https://pwndbg.com",
         "Enhanced GDB with smart layouts, heap visualization, and one-command search.", ["Free", "Debugger"]),
        ("strace / ltrace", "https://man7.org/linux/man-pages/man1/strace.1.html",
         "Trace system calls (strace) and library calls (ltrace) to understand binary behavior live.", ["Free", "Linux"]),
        ("Detect-It-Easy (DIE)", "https://github.com/horsicq/Detect-It-Easy",
         "Detects compilers, packers, and obfuscators used on a binary — useful first step.", ["Free", "Open Source"]),
    ],
    tips=[
        "String search first — run `strings -n 8` on the binary and look for flag fragments, function names, or hard-coded URLs.",
        "Use `file` and `checksec` to know what you are dealing with before opening a disassembler.",
        "In Ghidra, rename variables and functions as you understand them. A well-labelled decompile view saves hours.",
        "For packed binaries, let the program unpack itself: set a breakpoint just before entry point and dump the memory after the unpacking loop.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  4. FORENSICS
# ─────────────────────────────────────────────────────────────────────────────

FORENSICS = _page(
    icon="🔍",
    title="Forensics",
    lead="Forensics challenges involve recovering evidence from disk images, memory dumps, packet captures, and log files. Skills include file carving, steganography, timeline analysis, and artifact interpretation.",
    overview=(
        """<p>Digital forensics is the process of acquiring, preserving, and analysing digital evidence. Investigators examine hard drives, memory snapshots, network captures, and logs to reconstruct what happened, when, and by whom.</p>
<p>It is crucial for incident response, legal proceedings, and malware analysis. The discipline blends operating-system internals knowledge with investigative methodology and a strict chain-of-custody mindset.</p>""",
        """<p>In a CTF, you receive a file (PCAP, disk image, memory dump, photograph, archive) and must uncover a hidden flag or answer questions about an attack. The flag may be deleted, buried in metadata, encoded in an image, or hidden inside encrypted network traffic.</p>
<p>Common workflow: identify the artefact type → use the appropriate tool (Wireshark, Volatility, Autopsy, ExifTool) → search for patterns or anomalies → extract and decode the flag.</p>""",
        ["Recover deleted file from disk image", "Extract flag from PCAP (follow TCP stream)",
         "Steganography (LSB in PNG)", "Memory dump — find running process secrets",
         "Metadata extraction (GPS in photo)", "NTFS alternate data streams",
         "Browser history / SQLite artefacts", "File carving (no filesystem)",
         "Log analysis (find attacker IP)", "Email header analysis",
         "Encoded payload in DNS queries", "Corrupted ZIP / PNG header repair"]
    ),
    sample=(
        "Late Night Packet",
        "Forensics", "easy", 100,
        """The SOC team captured network traffic during a suspected data exfiltration. You receive a <code>.pcap</code> file.
        Your goal is to find what was stolen and recover the flag hidden inside the transferred data.""",
        ["capture.pcap"],
        [
            "Open <code>capture.pcap</code> in Wireshark. Go to <em>Statistics → Protocol Hierarchy</em> — notice an unusually large amount of HTTP traffic.",
            "Filter to <code>http</code> and look for <em>POST</em> requests to an external IP. Right-click → Follow → HTTP Stream.",
            "The POST body is Base64-encoded. Copy the encoded blob.",
            "Decode it: <code>echo '&lt;blob&gt;' | base64 -d</code> — the output is a PNG image.",
            "Open the image to reveal the flag printed on it.",
        ],
        "FLAG{pcap_foll0w_the_str34m}"
    ),
    official=[
        ("Autopsy / The Sleuth Kit", "https://www.sleuthkit.org/autopsy/",
         "Free, open-source digital forensics platform for analysing disk images and file systems.", ["Free", "Disk Forensics", "Open Source"]),
        ("Volatility Foundation", "https://volatilityfoundation.org",
         "The leading open-source memory forensics framework — extract processes, network connections, and artefacts from RAM.", ["Free", "Memory Forensics", "Open Source"]),
        ("Wireshark", "https://www.wireshark.org",
         "Industry-standard network protocol analyser for dissecting PCAP files.", ["Free", "Network Forensics", "Open Source"]),
        ("NetworkMiner", "https://www.netresec.com/?page=NetworkMiner",
         "Passive network forensics tool that reassembles files transferred over a captured network session.", ["Free Tier", "Network Forensics"]),
    ],
    training=[
        ("CyberDefenders", "https://cyberdefenders.org",
         "Blue-team focused platform with real-world DFIR labs — memory, disk, PCAP, and log analysis.", ["Free", "Labs", "Blue Team"]),
        ("Blue Team Labs Online", "https://blueteamlabs.online",
         "Free forensics and incident response challenges covering memory, log, and network analysis.", ["Free", "Labs"]),
        ("13Cubed YouTube Channel", "https://www.youtube.com/@13Cubed",
         "High-quality free tutorials on DFIR, Volatility, filesystem artefacts, and incident response.", ["Free", "Videos"]),
        ("Digital Forensics Lab (GitHub)", "https://github.com/frankwxu/digital-forensics-lab",
         "Open-source university course with 30 labs covering disk, memory, and mobile forensics.", ["Free", "Labs", "Academic"]),
        ("Magnet Forensics CTF", "https://www.magnetforensics.com/blog/tag/ctf/",
         "Annual free forensics CTF from the AXIOM vendor, focuses on real-world artefact analysis.", ["Free", "CTF"]),
        ("picoCTF — Forensics", "https://picoctf.org",
         "Beginner-friendly forensics problems covering steganography, file analysis, and PCAP puzzles.", ["Free", "Beginner"]),
    ],
    tools=[
        ("Volatility 3", "https://github.com/volatilityfoundation/volatility3",
         "Python 3 rewrite of the memory forensics framework — handles Windows, Linux, and macOS images.", ["Free", "Open Source"]),
        ("Wireshark", "https://www.wireshark.org",
         "Dissect PCAP files, follow TCP streams, and carve HTTP objects.", ["Free", "Open Source"]),
        ("Binwalk", "https://github.com/ReFirmLabs/binwalk",
         "Firmware/file entropy analysis and embedded file extraction — great for steganography too.", ["Free", "Open Source"]),
        ("ExifTool", "https://exiftool.org",
         "Read, write, and edit metadata in images, audio, video, and document files.", ["Free", "Open Source"]),
    ],
    tips=[
        "Always run `file` and `exiftool` on every artefact first — metadata often contains the flag or a direct hint.",
        "For PCAP challenges, use Wireshark's Statistics > Protocol Hierarchy to understand traffic composition, then Follow TCP/HTTP Streams for content.",
        "Memory dumps: start with `windows.pslist`, `windows.netscan`, and `windows.cmdline` to map the incident before digging deeper.",
        "Steganography tools to try in order: `strings`, `exiftool`, `steghide`, `zsteg` (for PNGs), and `binwalk` for embedded files.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  5. BINARY EXPLOITATION (PWN)
# ─────────────────────────────────────────────────────────────────────────────

PWN = _page(
    icon="💥",
    title="Binary Exploitation (Pwn)",
    lead="Pwn challenges require you to exploit memory corruption vulnerabilities — buffer overflows, format strings, heap mismanagement, and more — to hijack program execution, spawn a shell, or read protected memory.",
    overview=(
        """<p>Binary exploitation ("pwn") is the art of taking control of a running process by abusing memory-safety bugs. When a program fails to validate input size or type, an attacker can overwrite memory structures — redirecting execution to arbitrary code or leaking sensitive data.</p>
<p>It requires a deep understanding of process memory layout (stack, heap, BSS), CPU calling conventions, OS protections (ASLR, NX, stack canaries, PIE, RELRO), and low-level C/assembly behaviour.</p>""",
        """<p>In a CTF, you are given a compiled binary and (usually) a remote service running it. Your goal is to provide crafted input that hijacks execution and reads a flag from a privileged file or environment variable on the server.</p>
<p>Common workflow: check protections with <code>checksec</code> → find the vulnerability (overflow, format string, use-after-free) → calculate offsets → build the exploit payload with pwntools → leak a libc address if needed → get a shell and <code>cat flag.txt</code>.</p>""",
        ["Stack buffer overflow (ret2win)", "ROP chain (bypass NX)",
         "Format string leak + overwrite", "ret2libc / ret2plt",
         "Heap overflow (fastbin dup)", "Use-after-free (UAF)",
         "Stack canary brute-force (forking server)", "SROP (sigreturn-oriented programming)",
         "GOT overwrite", "Off-by-one overflow",
         "Tcache poisoning (glibc 2.29+)", "Shellcode injection (NX disabled)"]
    ),
    sample=(
        "ret2win",
        "Pwn", "easy", 150,
        """A 64-bit Linux ELF service reads your name with <code>gets()</code> into a 64-byte stack buffer and then calls <code>greet()</code>.
        There is also a function called <code>win()</code> that runs <code>/bin/sh</code> — it is never called by the program. NX is enabled; PIE is disabled.""",
        ["vuln", "libc.so.6"],
        [
            "Run <code>checksec vuln</code>: NX=on, PIE=off, no canary — confirms a ret-to-win approach.",
            "Find the <code>win()</code> address: <code>objdump -d vuln | grep win</code> (e.g. <code>0x401196</code>).",
            "Calculate the offset to the return address: <code>python3 -c \"import pwn; pwn.cyclic(200)\"</code>, crash the binary, read <code>rsp</code> in GDB, run <code>pwn.cyclic_find()</code>.",
            "Build the exploit: <code>payload = b'A'*offset + p64(win_addr)</code>.",
            "Send with pwntools: <code>p = process('./vuln'); p.sendline(payload); p.interactive()</code> — drops you to a shell.",
        ],
        "FLAG{sm4shed_the_st4ck_g0t_sh3ll}"
    ),
    official=[
        ("pwntools", "https://pwntools.com",
         "The essential Python library for writing CTF exploits — process control, ROP, packing, shellcode, and remote connections.", ["Tool", "Open Source"]),
        ("GDB (GNU Debugger)", "https://sourceware.org/gdb/",
         "The standard Linux debugger. Used with plugins like pwndbg for exploit development.", ["Tool", "Open Source"]),
        ("ROPgadget", "https://github.com/JonathanSalwan/ROPgadget",
         "Searches binaries for usable ROP gadgets and builds chains automatically.", ["Tool", "Open Source"]),
        ("one_gadget", "https://github.com/david942j/one_gadget",
         "Finds magic one-gadget execve('/bin/sh') gadgets in libc for quick shell.", ["Tool", "Open Source"]),
    ],
    training=[
        ("pwn.college", "https://pwn.college",
         "ASU's free, world-class course on binary exploitation — from shellcode to heap and kernel exploits. The best free resource available.", ["Free", "Courses", "Highly Recommended"]),
        ("ROPEmporium", "https://ropemporium.com",
         "Eight focused challenges that teach Return-Oriented Programming technique by technique.", ["Free", "Challenges", "ROP"]),
        ("ir0nstone — Binary Exploitation Notes", "https://ir0nstone.gitbook.io/notes",
         "Comprehensive free notes covering stack, format strings, ROP, SROP, heap, and kernel topics.", ["Free", "Reference"]),
        ("exploit.education", "https://exploit.education",
         "Provides vulnerable VMs (Phoenix, Nebula, Protostar, Fusion) designed for learning exploitation.", ["Free", "VMs"]),
        ("LiveOverflow YouTube", "https://www.youtube.com/@LiveOverflow",
         "In-depth binary exploitation series and real CTF walkthroughs — explains the 'why' behind techniques.", ["Free", "Videos"]),
        ("HackTheBox Academy — Stack-Based Buffer Overflows", "https://academy.hackthebox.com",
         "Guided exploitation labs from basic stack smashing to modern bypass techniques.", ["Free Tier", "Labs"]),
        ("picoCTF — Binary Exploitation", "https://picoctf.org",
         "Beginner binary exploitation challenges with hints. Good for first-timers learning gdb.", ["Free", "Beginner"]),
    ],
    tools=[
        ("pwndbg", "https://pwndbg.com",
         "GDB plugin with colour-coded context, heap inspection, and one-command GOT/PLT lookup.", ["Free", "Debugger"]),
        ("pwntools", "https://pwntools.com",
         "Python exploit framework — write, test, and script exploits in minutes.", ["Free", "Open Source"]),
        ("checksec", "https://github.com/slimm609/checksec.sh",
         "Quickly check which mitigations (ASLR, PIE, stack canary, NX, RELRO) are enabled.", ["Free", "Open Source"]),
        ("libc-database", "https://github.com/niklasb/libc-database",
         "Search for a libc version by function offsets — critical for ret2libc attacks.", ["Free", "Open Source"]),
    ],
    tips=[
        "Run `checksec` first — knowing whether PIE / canary / NX are enabled immediately narrows your attack surface.",
        "pwn.college is the single best resource, even for experienced players. Start from the beginning; the early modules build crucial fundamentals.",
        "Use pwntools' `cyclic` / `cyclic_find` to determine the offset to the return address quickly — avoid manual counting.",
        "When stuck on a heap challenge, read the allocator source (glibc malloc/free) and draw the bin structure by hand.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  6. MISCELLANEOUS
# ─────────────────────────────────────────────────────────────────────────────

MISC = _page(
    icon="🎲",
    title="Miscellaneous",
    lead="Misc challenges don't fit neatly into other categories. Expect steganography, encoding/decoding puzzles, scripting tasks, jail escapes, trivia, and creative problems that reward lateral thinking.",
    overview=(
        """<p>Miscellaneous is the catch-all category for challenges that don't cleanly belong elsewhere. It rewards breadth: a solver may need knowledge from programming, maths, linguistics, pop culture, networking, or any other field depending on the challenge author's imagination.</p>
<p>Misc challenges are often the most creative and unconventional problems in a CTF. Their unpredictability makes strong general technical skills and lateral thinking essential.</p>""",
        """<p>In a CTF, a misc challenge might give you an encoded blob, a strange image, a broken file, a Python jail, a game, or even a social engineering puzzle. The goal varies, but always ends with extracting a flag.</p>
<p>Common workflow: identify what format or encoding is in use → apply CyberChef / dcode.fr → if it's a script jail, enumerate allowed builtins → if it's steg, try steghide / zsteg / binwalk → iterate until the flag appears.</p>""",
        ["CyberChef multi-step recipe", "Python/Bash jail escape",
         "Steganography (LSB, DCT, F5)", "QR code repair",
         "Base-N / ROT / XOR encoding chain", "Morse / Braille / semaphore decode",
         "Scripting to automate 1000 steps", "DTMF / audio decoding",
         "Git history recovery (git log)", "Zip / archive bomb analysis",
         "Regex golf / code golf", "Game hacking (netcat protocol)"]
    ),
    sample=(
        "Invisible Ink",
        "Misc", "easy", 75,
        """You receive a <code>.png</code> image of a plain white-on-black company logo. The challenge description says:
        <em>"Sometimes the best hiding spot is the one nobody looks at."</em>""",
        ["logo.png"],
        [
            "Run <code>strings logo.png</code> — no obvious flag.",
            "Run <code>exiftool logo.png</code> — nothing hidden in metadata.",
            "Try <code>steghide extract -sf logo.png -p ''</code> — extracts <code>secret.txt</code> with an empty passphrase.",
            "Read <code>secret.txt</code> to get the flag.",
            "<em>(Alternative path)</em>: run <code>zsteg logo.png</code> — it would have found the LSB-embedded data automatically.",
        ],
        "FLAG{st3gh1d3_empty_p4ssw0rd}"
    ),
    official=[
        ("CTFtime", "https://ctftime.org",
         "The authoritative calendar of CTF events worldwide, with team rankings and historical writeups.", ["Resource", "Community"]),
        ("CTF101", "https://ctf101.org",
         "Beginner guide to CTF categories, tools, and competition strategy maintained by OSIRIS Lab.", ["Guide", "Beginner"]),
        ("Unicode Character Table", "https://www.compart.com/en/unicode/",
         "Essential reference for encoding challenges involving Unicode, homoglyphs, or invisible characters.", ["Reference"]),
        ("Base Encoding Reference", "https://base64.guru",
         "Encoder/decoder for Base16 through Base128 variants with format identification.", ["Reference", "Browser"]),
    ],
    training=[
        ("picoCTF — General Skills", "https://picoctf.org",
         "Covers command-line basics, Bash scripting, encoding, and misc puzzle types. Ideal starting point.", ["Free", "Beginner"]),
        ("Google CTF Beginners Quest", "https://capturetheflag.withgoogle.com",
         "Google's annual CTF includes accessible misc challenges across unique, inventive themes.", ["Free", "CTF"]),
        ("OverTheWire: Bandit", "https://overthewire.org/wargames/bandit/",
         "Linux command-line wargame — teaches Bash, file manipulation, and basic scripting through play.", ["Free", "Wargame"]),
        ("HackTheBox — Misc Challenges", "https://app.hackthebox.com/challenges",
         "Diverse misc category including jail escapes, scripting tasks, and creative puzzles.", ["Free Tier", "Challenges"]),
        ("Advent of Code", "https://adventofcode.com",
         "Annual coding challenges (December) — builds scripting skills critical for automating CTF solves.", ["Free", "Coding"]),
    ],
    tools=[
        ("CyberChef", "https://gchq.github.io/CyberChef/",
         "Magic encoding/decoding tool — pipes operations and auto-detects many formats.", ["Free", "Browser"]),
        ("dcode.fr", "https://www.dcode.fr/en",
         "Identifies and solves hundreds of classical ciphers, codes, and encodings.", ["Free", "Browser"]),
        ("Stegsolve", "https://github.com/zardus/ctf-tools/blob/master/stegsolve/install",
         "Image steganography analyser — view bit planes, colour channels, and apply filters.", ["Free", "Steg"]),
        ("steghide", "https://steghide.sourceforge.net",
         "Embeds/extracts hidden data in JPEG and BMP files.", ["Free", "Steg"]),
    ],
    tips=[
        "CyberChef's 'Magic' recipe is your first move on any unknown blob of data — it tries hundreds of operations automatically.",
        "For steg challenges: run `strings`, `binwalk`, `exiftool`, `file`, then try steghide with an empty password, then zsteg (for PNGs) or stegsolve.",
        "Misc jail escapes frequently exploit Python/Bash builtins — study the `__import__` / `os` access patterns and common sandbox escapes.",
        "Build a personal '`toolkit`' of one-liners: base64 decode, hex dump, URL decode — you'll use them in every competition.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  7. OSINT
# ─────────────────────────────────────────────────────────────────────────────

OSINT = _page(
    icon="👁️",
    title="OSINT",
    lead="Open-Source Intelligence challenges require you to find information about targets using only publicly available data: social media, image metadata, domain records, satellite imagery, and public databases.",
    overview=(
        """<p>OSINT (Open-Source Intelligence) is the collection and analysis of information from publicly available sources — websites, social media, public records, satellite imagery, domain registrations, job postings, and more.</p>
<p>It is used by law enforcement, journalists, penetration testers, and threat intelligence analysts to build profiles of individuals, organisations, and infrastructure without any direct interaction with the target.</p>""",
        """<p>In a CTF, OSINT challenges give you a starting point (a username, a photo, a company name, a tweet) and ask you to discover a specific fact — a real-world location, an email address, a date, or a connection between entities. No hacking tools are needed; only research skills and patience.</p>
<p>Common workflow: identify all data points in the brief → reverse image search → check social media profiles → inspect WHOIS / Shodan / Certificate Transparency logs → cross-reference findings → geolocate if needed.</p>""",
        ["Geolocate a photo (street signs, landmarks)", "Find a person's employer from LinkedIn",
         "Identify a building from satellite view", "Username pivot across platforms",
         "WHOIS / DNS history lookup", "Find deleted tweet (Wayback Machine)",
         "Decode GPS EXIF from image", "Shodan search for exposed service",
         "Certificate Transparency subdomain enum", "Identify ship/aircraft from AIS/ADS-B",
         "Reverse email → real name", "Find source code from a screenshot"]
    ),
    sample=(
        "Gone Offline",
        "OSINT", "medium", 200,
        """A threat actor posted a photo on a now-deleted Twitter account and claimed it was taken "somewhere in the capital".
        The only artefact you have is a screenshot of the tweet including the image.
        Find the exact street address of where the photo was taken.""",
        ["tweet_screenshot.png"],
        [
            "Crop the embedded image from the screenshot. Reverse-image search with Google, TinEye, and Yandex — Yandex finds a match on a local tourism blog.",
            "The blog post names the city district. Cross-reference with Google Street View to identify the visible building facade and street signage.",
            "Check the Wayback Machine for the original tweet URL (extracted from the screenshot URL bar) — the archived version still has the original image with GPS EXIF intact.",
            "Run <code>exiftool original.jpg</code> — GPS coordinates appear. Convert DMS to decimal and look up in Google Maps.",
            "The pin drops on a specific cafe. The street address is the flag.",
        ],
        "FLAG{47.6062_N_122.3321_W_pike_place_market}"
    ),
    official=[
        ("OSINT Framework", "https://osintframework.com",
         "Visual tree of categorised OSINT tools and data sources maintained by the community.", ["Reference", "Tool Directory"]),
        ("Shodan", "https://www.shodan.io",
         "Search engine for internet-connected devices — banners, certificates, open ports, and more.", ["Tool", "Search Engine"]),
        ("WHOIS (ICANN)", "https://lookup.icann.org",
         "Official ICANN WHOIS service for domain registration and registrant data.", ["Reference", "DNS"]),
        ("OSINT Techniques", "https://www.osinttechniques.com",
         "Community resource listing tools and techniques organised by target type.", ["Reference"]),
    ],
    training=[
        ("Bellingcat", "https://www.bellingcat.com",
         "World-renowned open-source investigative journalism outlet — their guides teach real-world OSINT methodology.", ["Free", "Guide", "Highly Recommended"]),
        ("Trace Labs OSINT CTF", "https://www.tracelabs.org",
         "Crowd-sourced CTF that uses real missing persons cases — ethical real-world OSINT practice.", ["Free", "CTF", "Real-World"]),
        ("OSINT Curious", "https://osintcurio.us",
         "Practitioner-led blog and webcast series on investigation techniques and tool usage.", ["Free", "Blog", "Videos"]),
        ("OSINT Dojo", "https://www.osintdojo.com",
         "Beginner OSINT challenges that progress from basic recon to image geolocation.", ["Free", "Challenges", "Beginner"]),
        ("Sofia Santos' OSINT Analysis", "https://gralhix.com",
         "Detailed walkthroughs of geolocation and imagery analysis challenges.", ["Free", "Writeups"]),
        ("GeoHints", "https://geohints.com",
         "Visual reference for identifying countries and regions in GeoGuessr/photo-based CTF challenges.", ["Free", "Geolocation"]),
        ("IntelTechniques", "https://inteltechniques.com",
         "Michael Bazzell's OSINT resources — free tools, workbooks, and podcast on investigation technique.", ["Free", "Reference"]),
    ],
    tools=[
        ("Shodan", "https://www.shodan.io",
         "Find exposed devices, services, and certificates by IP, organisation, or banner.", ["Free Tier"]),
        ("theHarvester", "https://github.com/laramies/theHarvester",
         "Passive recon tool for gathering emails, subdomains, IPs, and names from public sources.", ["Free", "Open Source"]),
        ("Maltego CE", "https://www.maltego.com/maltego-community/",
         "Link-analysis tool for mapping relationships between people, companies, and infrastructure.", ["Free Tier"]),
        ("ExifTool", "https://exiftool.org",
         "Extract embedded GPS, camera model, and timestamp metadata from images.", ["Free", "Open Source"]),
    ],
    tips=[
        "Develop a structured workflow: Identify → Collect → Analyse → Report. Don't jump to conclusions before gathering sufficient data.",
        "Reverse image search with Google, TinEye, AND Yandex — Yandex frequently finds matches the others miss, especially for buildings and landscapes.",
        "For geolocation challenges: look for text (signs, licence plates), vegetation, infrastructure (power lines, road markings), and sun angle.",
        "Check the Wayback Machine (web.archive.org) and Google Cache for deleted content — OSINT challenges often reference historical pages.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  8. CLOUD / DEVOPS
# ─────────────────────────────────────────────────────────────────────────────

CLOUD = _page(
    icon="☁️",
    title="Cloud / DevOps",
    lead="Cloud challenges cover misconfigurations and vulnerabilities in AWS, Azure, GCP, Docker, and Kubernetes — from exposed S3 buckets and leaked credentials to container escapes and IAM privilege escalation.",
    overview=(
        """<p>Cloud / DevOps security focuses on vulnerabilities specific to modern infrastructure: cloud platforms (AWS, Azure, GCP), container orchestration (Kubernetes, Docker), Infrastructure-as-Code (Terraform, CloudFormation), and CI/CD pipelines.</p>
<p>Unlike traditional security, the attack surface here is largely configuration-driven. A single IAM policy with excessive permissions or a publicly accessible S3 bucket can expose an entire organisation's data without any code vulnerability involved.</p>""",
        """<p>In a CTF, cloud challenges give you credentials, a running cloud environment, a Docker image, or a Kubernetes config and ask you to escalate privileges, read a protected secret, or escape a container to reach the flag.</p>
<p>Common workflow: enumerate accessible resources (S3, EC2, IAM policies) → query the metadata service (169.254.169.254) → find misconfigured permissions → escalate → read the flag from a secrets manager or root volume.</p>""",
        ["S3 bucket public read (list + download)", "EC2 instance metadata credential theft",
         "IAM privilege escalation (PassRole)", "Lambda function code leak",
         "Docker socket escape to host", "Kubernetes RBAC misconfiguration",
         "Exposed .env in public repository", "SSM Parameter Store secret read",
         "ECS task role abuse", "Terraform state file leak (S3)",
         "GitHub Actions secret exfiltration", "Container image layer secret extraction"]
    ),
    sample=(
        "BucketList",
        "Cloud", "easy", 125,
        """You have been given the domain name of a small startup: <code>startup-assets.s3.amazonaws.com</code>.
        The security team suspects the S3 bucket has a misconfigured ACL. Investigate and retrieve the flag.""",
        [],
        [
            "List the bucket without credentials: <code>aws s3 ls s3://startup-assets --no-sign-request</code> — it succeeds, confirming public-read ACL.",
            "Browse the listing — spot an interesting file: <code>internal/config_backup.json</code>.",
            "Download it: <code>aws s3 cp s3://startup-assets/internal/config_backup.json . --no-sign-request</code>.",
            "Open the JSON — it contains an <code>aws_secret_access_key</code> and a <code>flag</code> field.",
            "Read the <code>flag</code> value directly from the file.",
        ],
        "FLAG{publ1c_s3_1s_n0t_priv4te}"
    ),
    official=[
        ("AWS Security Documentation", "https://aws.amazon.com/security/",
         "Official AWS security best practices, IAM policy docs, and the Well-Architected Security Pillar.", ["Official", "AWS"]),
        ("Azure Security Center", "https://azure.microsoft.com/en-us/products/security-center",
         "Microsoft's security posture management platform — also the source of misconfig guidance.", ["Official", "Azure"]),
        ("GCP Security Command Center", "https://cloud.google.com/security-command-center",
         "Google Cloud's security and risk platform with documentation on common cloud vulnerabilities.", ["Official", "GCP"]),
        ("CNCF TAG Security", "https://tag-security.cncf.io",
         "Cloud Native Computing Foundation security working group — Kubernetes and container security papers.", ["Official", "Kubernetes"]),
    ],
    training=[
        ("flaws.cloud", "http://flaws.cloud",
         "Level-by-level challenges teaching real AWS S3, metadata service, and IAM misconfigurations through play.", ["Free", "AWS", "Highly Recommended"]),
        ("flaws2.cloud", "http://flaws2.cloud",
         "Sequel to flaws.cloud — attacker AND defender paths for AWS Lambda, ECS, and ECR misconfigs.", ["Free", "AWS"]),
        ("CloudGoat (Rhino Security)", "https://github.com/RhinoSecurityLabs/cloudgoat",
         "Intentionally vulnerable AWS environment with multi-step attack scenarios for privilege escalation.", ["Free", "AWS", "Lab App"]),
        ("TerraGoat (Bridgecrew)", "https://github.com/bridgecrewio/terragoat",
         "Vulnerable Terraform infrastructure across AWS, Azure, and GCP for IaC security learning.", ["Free", "Multi-cloud", "IaC"]),
        ("KubeGoat", "https://github.com/ksoclabs/kube-goat",
         "Intentionally vulnerable Kubernetes cluster for learning container and cluster security.", ["Free", "Kubernetes", "Lab App"]),
        ("HackTheBox Cloud Challenges", "https://app.hackthebox.com/challenges",
         "Dedicated cloud category with realistic AWS/GCP/Azure misconfiguration and exploitation scenarios.", ["Free Tier", "Challenges"]),
        ("TryHackMe Cloud Rooms", "https://tryhackme.com/hacktivities?tab=search&searchTxt=cloud",
         "Guided AWS and Azure security rooms covering IAM, S3, Lambda, and common attack vectors.", ["Free Tier", "Guided"]),
    ],
    tools=[
        ("AWS CLI", "https://aws.amazon.com/cli/",
         "Essential tool for interacting with AWS services — enumerate, test, and exploit from the command line.", ["Free", "Official"]),
        ("CloudSploit", "https://github.com/aquasecurity/cloudsploit",
         "Open-source cloud security scanner that detects misconfigurations across AWS, Azure, and GCP.", ["Free", "Open Source"]),
        ("Pacu", "https://github.com/RhinoSecurityLabs/pacu",
         "AWS exploitation framework for post-compromise enumeration and privilege escalation.", ["Free", "Open Source"]),
        ("ScoutSuite", "https://github.com/nccgroup/ScoutSuite",
         "Multi-cloud security auditing tool that generates HTML reports of misconfigurations.", ["Free", "Open Source"]),
    ],
    tips=[
        "The EC2 instance metadata service (169.254.169.254) is your first move after gaining any foothold — it often leaks IAM credentials.",
        "Always check for public S3 buckets: `aws s3 ls s3://target-bucket --no-sign-request` works without credentials.",
        "flaws.cloud is the best starting point — work through all six levels before tackling CTF cloud challenges.",
        "For Kubernetes: check for open API servers (port 6443/8080), misconfigured RBAC, and secrets mounted as environment variables in pods.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  9. MOBILE
# ─────────────────────────────────────────────────────────────────────────────

MOBILE = _page(
    icon="📱",
    title="Mobile Security",
    lead="Mobile challenges involve reverse engineering and exploiting Android APKs and iOS IPAs — from decompiling Java bytecode and patching apps to hooking runtime methods with Frida and bypassing certificate pinning.",
    overview=(
        """<p>Mobile security is the field of finding and exploiting vulnerabilities in Android and iOS applications. Unlike desktop software, mobile apps run in sandboxed environments but are regularly undermined by insecure data storage, weak authentication, certificate pinning mistakes, and exported activity/intent misuse.</p>
<p>The OWASP Mobile Top 10 defines the most common mobile weaknesses, and both Android (Java/Kotlin/NDK) and iOS (Swift/Objective-C) have distinct attack surfaces that security researchers must understand.</p>""",
        """<p>In a CTF, you receive an APK or IPA file and must extract a flag hidden inside the app's logic, resources, or network communication. Some challenges require only static analysis; others need you to run the app on an emulator, hook functions with Frida, or patch the binary to bypass checks.</p>
<p>Common workflow: unpack with APKTool/jadx → inspect <code>AndroidManifest.xml</code> → search strings/resources → decompile Java → hook with Frida if dynamic analysis is needed → intercept HTTPS traffic with Burp + SSL unpin.</p>""",
        ["Hardcoded API key in APK resources", "Reverse Java validation logic",
         "Bypass root/emulator detection (Frida)", "SSL pinning bypass",
         "Exported Activity access (ADB intent)", "Shared preferences plain-text secret",
         "Native library (JNI) reverse engineering", "Firebase misconfiguration (public DB)",
         "Deep-link parameter injection", "iOS Keychain extraction",
         "Frida hook to dump decrypted payload", "APK repack and re-sign"]
    ),
    sample=(
        "UnlockMe",
        "Mobile", "medium", 200,
        """You receive an Android APK that shows a PIN entry screen.
        Entering the correct 6-digit PIN displays the flag. The app performs root and emulator detection before proceeding.""",
        ["unlockme.apk"],
        [
            "Decompile with <code>jadx-gui unlockme.apk</code>. Search for <code>onCheckPin</code> — find a method that compares user input against a SHA-256 hash.",
            "The hash <code>8d969eef6...&lt;snip&gt;</code> matches the SHA-256 of <code>123456</code> (identify with <code>hashcat --example-hashes</code> or CrackStation).",
            "The app crashes on emulator. Bypass using Frida: hook <code>isEmulator()</code> to return <code>false</code>.",
            "Run the patched check: <code>frida -U -f com.ctf.unlockme --no-pause -l bypass.js</code>.",
            "Enter PIN <code>123456</code> in the app — the flag is displayed on screen.",
        ],
        "FLAG{fr1d4_byp4ss_em_d3t3ct10n}"
    ),
    official=[
        ("OWASP Mobile Application Security", "https://mas.owasp.org",
         "The OWASP MAS project — MASVS (testing standard) and MASTG (testing guide) with hundreds of test cases.", ["Official", "Standard", "OWASP"]),
        ("Android Developer Security", "https://developer.android.com/topic/security",
         "Google's official documentation on Android security model, permissions, sandboxing, and secure coding.", ["Official", "Android"]),
        ("Apple Platform Security Guide", "https://support.apple.com/guide/security/welcome/web",
         "Apple's comprehensive technical reference for iOS/macOS security architecture and features.", ["Official", "iOS"]),
        ("Frida", "https://frida.re",
         "Dynamic instrumentation framework that lets you inject JavaScript to hook and modify running app behaviour.", ["Tool", "Open Source"]),
    ],
    training=[
        ("OWASP MASTG Crackmes", "https://mas.owasp.org/crackmes/",
         "Official OWASP Mobile challenge apps — Android and iOS — ranging from beginner to expert.", ["Free", "Challenges", "OWASP"]),
        ("DVIA-v2 (iOS)", "https://damnvulnerableiosapp.com",
         "Damn Vulnerable iOS App — intentionally insecure iOS app covering OWASP Mobile Top 10.", ["Free", "iOS", "Lab App"]),
        ("hpAndro Vulnerable Bank", "https://github.com/HackWithPiyush/hpAndro1337",
         "Vulnerable Android banking app specifically designed for OWASP-aligned CTF-style challenges.", ["Free", "Android", "Lab App"]),
        ("NowSecure Academy", "https://academy.nowsecure.com",
         "Free courses on Android and iOS security testing methodology from an industry leader.", ["Free", "Course"]),
        ("HackTricks — Mobile", "https://book.hacktricks.xyz/mobile-pentesting",
         "Comprehensive wiki-style reference for Android and iOS pentesting techniques.", ["Free", "Reference"]),
        ("HackTheBox Mobile Challenges", "https://app.hackthebox.com/challenges",
         "Android and iOS challenge apps covering reversing, hooking, and runtime manipulation.", ["Free Tier", "Challenges"]),
    ],
    tools=[
        ("MobSF", "https://mobsf.github.io/Mobile-Security-Framework-MobSF/",
         "Mobile Security Framework — automated static and dynamic analysis for Android/iOS apps.", ["Free", "Open Source"]),
        ("APKTool", "https://apktool.org",
         "Decompile and recompile Android APKs. Decode resources and smali bytecode.", ["Free", "Android", "Open Source"]),
        ("jadx", "https://github.com/skylot/jadx",
         "Dex to Java decompiler — produces readable Java source from APK/DEX files.", ["Free", "Android", "Open Source"]),
        ("Frida", "https://frida.re",
         "Hook any function at runtime on Android or iOS — bypass security checks, dump secrets, trace calls.", ["Free", "Open Source"]),
    ],
    tips=[
        "Start every APK challenge with MobSF static analysis — it automatically flags hardcoded secrets, insecure components, and dangerous permissions.",
        "Use `jadx-gui` for readable Java decompilation, then Ghidra for native (.so) library RE if needed.",
        "For Frida: use the objection framework (`pip install objection`) to automate common tasks like SSL unpinning with a single command.",
        "Check AndroidManifest.xml for exported activities, content providers, and broadcast receivers — they're common attack entry points.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  10. HARDWARE / IOT
# ─────────────────────────────────────────────────────────────────────────────

HARDWARE = _page(
    icon="🔧",
    title="Hardware / IoT",
    lead="Hardware and IoT challenges involve extracting, analysing, and exploiting firmware from embedded devices — reading debug interfaces like UART and JTAG, reversing proprietary protocols, and manipulating signals with logic analysers.",
    overview=(
        """<p>Hardware and IoT security deals with the security of physical devices — routers, smart home gadgets, industrial controllers, medical devices, and custom embedded systems. Attackers target these devices through debug ports left enabled, unencrypted firmware update mechanisms, insecure bootloaders, and hard-coded credentials.</p>
<p>It blends electronics knowledge (serial protocols, PCB reading, soldering) with software RE (firmware extraction, MIPS/ARM binary analysis) and network security (exposing management APIs).</p>""",
        """<p>In a CTF, hardware challenges usually provide a firmware image (.bin file), a logic analyser capture (.sal, .csv), or a description of a physical setup. Your goal is to extract a flag by analysing the firmware filesystem, reversing a binary, decoding a captured serial conversation, or exploiting a hardcoded credential.</p>
<p>Common workflow: run <code>binwalk -e firmware.bin</code> → explore the extracted filesystem → search for credentials and keys → reverse interesting binaries with Ghidra → or decode protocol capture with Sigrok.</p>""",
        ["Binwalk extract filesystem from .bin", "Hard-coded root password in /etc/shadow",
         "UART console gives root shell", "Decrypt firmware update (AES key in binary)",
         "Logic analyser capture decode (UART/I²C/SPI)", "JTAG debug port code execution",
         "Web interface command injection (router)", "Private key in firmware filesystem",
         "Insecure bootloader bypass", "MQTT broker unauthenticated subscribe",
         "OTA update replay attack", "Exposed JTAG test pads on PCB"]
    ),
    sample=(
        "FirmwareFrenzy",
        "Hardware", "medium", 250,
        """You receive a 4 MB binary dump from a consumer IoT router: <code>router_fw.bin</code>.
        The vendor claims the firmware is encrypted, but the security team suspects the flag is stored in plain text inside the filesystem.""",
        ["router_fw.bin"],
        [
            "Run <code>binwalk router_fw.bin</code> — it detects a SquashFS filesystem at offset <code>0x50000</code> and a LZMA-compressed kernel.",
            "Extract: <code>binwalk -e router_fw.bin</code> — a directory <code>_router_fw.bin.extracted/</code> appears.",
            "Run <code>firmwalker _router_fw.bin.extracted/</code> — it highlights <code>/etc/config/system</code> as containing a password.",
            "Open the file — it contains: <code>option flag 'FLAG{b1nwalk_squashfs_4_th3_w1n}'</code>.",
        ],
        "FLAG{b1nwalk_squashfs_4_th3_w1n}"
    ),
    official=[
        ("OWASP IoT Project", "https://owasp.org/www-project-internet-of-things/",
         "OWASP's attack surface areas, testing guide, and security considerations for IoT devices.", ["Official", "OWASP"]),
        ("IoTGoat", "https://github.com/OWASP/IoTGoat",
         "OWASP's intentionally insecure firmware based on OpenWrt — includes a ready-to-run QEMU image.", ["Official", "OWASP", "Lab Firmware"]),
        ("OpenOCD", "https://openocd.org",
         "Open-source on-chip debugger supporting JTAG and SWD — used to attach GDB to hardware targets.", ["Tool", "Open Source"]),
        ("Sigrok / PulseView", "https://sigrok.org",
         "Free logic analyser software supporting 50+ hardware devices for protocol decoding.", ["Tool", "Open Source"]),
    ],
    training=[
        ("Embedded Security CTF (GitHub)", "https://github.com/nicowillis/embedded-security-ctf",
         "Collection of hardware/firmware CTF challenges with setup guides and Docker environments.", ["Free", "Challenges"]),
        ("DVID — Damn Vulnerable IoT Device", "https://github.com/Vulcainreo/DVID",
         "Training board firmware with intentional vulnerabilities covering UART, debug ports, and auth bypass.", ["Free", "Lab Firmware"]),
        ("HackTheBox Hardware Challenges", "https://app.hackthebox.com/challenges",
         "Firmware images, logic captures, and RF challenges covering UART, I²C, and custom protocols.", ["Free Tier", "Challenges"]),
        ("Exploit.ST — Intro to Hardware Hacking", "https://www.youtube.com/playlist?list=PLz26m7KAnNB3TSmELLlT-5UANEqAPkFjw",
         "Free YouTube series covering hardware hacking fundamentals — UART, JTAG, and SPI.", ["Free", "Videos"]),
        ("Firmware Security Testing Methodology", "https://github.com/scriptingxss/owasp-fstm",
         "OWASP's structured 9-step methodology for extracting and analysing IoT firmware.", ["Free", "Reference"]),
        ("Practical IoT Hacking (Fotios Chantzis)", "https://nostarch.com/practical-iot-hacking",
         "Comprehensive book on IoT exploitation — Chapter 1 freely available from No Starch.", ["Book", "Partial Free"]),
    ],
    tools=[
        ("Binwalk", "https://github.com/ReFirmLabs/binwalk",
         "Firmware entropy analysis and recursive extraction — first tool to run on any firmware image.", ["Free", "Open Source"]),
        ("Firmwalker", "https://github.com/craigz28/firmwalker",
         "Script to search extracted firmware for credentials, keys, and interesting files.", ["Free", "Open Source"]),
        ("Ghidra", "https://ghidra-sre.org",
         "RE firmware binaries (MIPS, ARM, PowerPC) with the built-in disassembler and decompiler.", ["Free", "Open Source"]),
        ("minicom / screen", "https://wiki.debian.org/minicom",
         "Connect to UART serial consoles on embedded devices — often yields a root shell.", ["Free", "Open Source"]),
    ],
    tips=[
        "First step with any firmware: run `binwalk -e firmware.bin` to extract the filesystem, then `firmwalker` on the extracted path.",
        "Look for UART test points on PCBs — they frequently give an unauthenticated root shell. A USB-TTL adapter costs ~$3.",
        "Check for default credentials in `/etc/passwd`, `/etc/shadow`, and init scripts before attempting anything more complex.",
        "Emulate firmware with QEMU (`qemu-mips-static`) when you don't have physical hardware — most Linux-based IoT firmware runs under QEMU.",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
#  CTF CHEATSHEET  (quick-reference: encoding/cipher ID + full tool directory)
#  Content adapted from the public cheatsheet at
#  https://neerajlovecyber.com/ctf-cheatsheet
# ─────────────────────────────────────────────────────────────────────────────

CHEATSHEET_STYLE = """
<style>
/* ── Cheatsheet checklist ─────────────────────────────────────────────────── */
.dp-check-group{margin-bottom:2rem;}
.dp-check-group-title{
  font-size:.95rem;font-weight:700;color:var(--dp-accent2);
  margin-bottom:.9rem;display:flex;align-items:center;gap:.5rem;
}
.dp-check-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:.85rem;
}
@media(max-width:720px){.dp-check-grid{grid-template-columns:1fr;}}
.dp-check{
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-left:3px solid rgba(var(--dp-accent-rgb),.55);
  border-radius:0 8px 8px 0;
  padding:.85rem 1rem;
}
.dp-check-head{
  display:flex;align-items:center;justify-content:space-between;gap:.5rem;
  margin-bottom:.35rem;
}
.dp-check-name{font-size:.86rem;font-weight:700;color:var(--dp-accent);}
.dp-check-decoder{
  font-size:.68rem;font-weight:600;text-decoration:none;
  color:var(--dp-accent2);white-space:nowrap;
}
.dp-check-decoder:hover{text-decoration:underline;}
.dp-check-pattern{font-size:.78rem;color:var(--dp-muted);line-height:1.55;}
.dp-check-code{
  margin:.55rem 0 0;padding:.5rem .7rem;
  background:var(--dp-bg);border:1px solid var(--dp-border);border-radius:6px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.72rem;color:var(--dp-text);
  white-space:pre-wrap;word-break:break-all;overflow-x:auto;
}
/* ── FAQ ──────────────────────────────────────────────────────────────────── */
.dp-faq{
  background:var(--dp-surface);
  border:1px solid var(--dp-border);
  border-radius:10px;
  padding:1rem 1.25rem;
  margin-bottom:.75rem;
}
.dp-faq-q{font-size:.88rem;font-weight:700;color:var(--dp-accent);margin-bottom:.4rem;}
.dp-faq-a{font-size:.83rem;color:var(--dp-text);line-height:1.65;}
.dp-credit{
  text-align:center;font-size:.78rem;color:var(--dp-muted);
  margin-top:2.5rem;padding-top:1.4rem;border-top:1px solid var(--dp-border);
}
.dp-credit a{color:var(--dp-accent);text-decoration:none;font-weight:600;}
.dp-credit a:hover{text-decoration:underline;}
/* ── Jump nav ─────────────────────────────────────────────────────────────── */
.dp-toc{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 2.2rem;}
.dp-toc a{
  font-size:.73rem;font-weight:600;text-decoration:none;
  padding:.3rem .7rem;border-radius:999px;
  background:rgba(var(--dp-accent-rgb),.1);color:var(--dp-accent);
  border:1px solid rgba(var(--dp-accent-rgb),.22);
}
.dp-toc a:hover{background:rgba(var(--dp-accent-rgb),.2);}
.dp-anchor{scroll-margin-top:84px;}
/* ── Beginner: start-here callout ─────────────────────────────────────────── */
.dp-start{
  background:linear-gradient(135deg,rgba(var(--dp-accent-rgb),.12),rgba(var(--dp-accent-rgb),.03));
  border:1px solid rgba(var(--dp-accent-rgb),.28);
  border-radius:14px;padding:1.5rem 1.6rem;margin-bottom:1.6rem;
}
.dp-start h3{font-size:1rem;font-weight:700;color:var(--dp-accent);margin:0 0 .6rem;display:flex;align-items:center;gap:.5rem;}
.dp-start p{font-size:.86rem;color:var(--dp-text);line-height:1.7;margin:0 0 .6rem;}
.dp-start p:last-child{margin-bottom:0;}
.dp-start code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8rem;background:var(--dp-bg);border:1px solid var(--dp-border);border-radius:5px;padding:.08rem .35rem;color:var(--dp-accent2);}
/* ── Numbered steps ───────────────────────────────────────────────────────── */
.dp-steps{list-style:none;counter-reset:dp-step;margin:0;padding:0;}
.dp-steps li{
  counter-increment:dp-step;position:relative;
  padding:.6rem 0 .6rem 2.5rem;font-size:.86rem;color:var(--dp-text);line-height:1.65;
  border-bottom:1px solid var(--dp-border);
}
.dp-steps li:last-child{border-bottom:none;}
.dp-steps li::before{
  content:counter(dp-step);position:absolute;left:0;top:.55rem;
  width:1.6rem;height:1.6rem;border-radius:50%;
  background:var(--dp-accent);color:#fff;font-size:.76rem;font-weight:700;
  display:flex;align-items:center;justify-content:center;
}
.dp-steps li strong{color:var(--dp-accent2);}
/* ── Approach / methodology cards ─────────────────────────────────────────── */
.dp-approach-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
@media(max-width:760px){.dp-approach-grid{grid-template-columns:1fr;}}
.dp-approach{
  background:var(--dp-surface);border:1px solid var(--dp-border);
  border-top:3px solid rgba(var(--dp-accent-rgb),.6);
  border-radius:0 0 10px 10px;padding:1.1rem 1.25rem;
}
.dp-approach h4{font-size:.9rem;font-weight:700;color:var(--dp-accent);margin:0 0 .35rem;display:flex;align-items:center;gap:.45rem;}
.dp-approach-intro{font-size:.78rem;color:var(--dp-muted);margin:0 0 .7rem;line-height:1.55;font-style:italic;}
.dp-approach ol{margin:0;padding-left:1.15rem;}
.dp-approach ol li{font-size:.81rem;color:var(--dp-text);line-height:1.55;margin-bottom:.34rem;}
.dp-approach ol li code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.74rem;background:var(--dp-bg);border:1px solid var(--dp-border);border-radius:5px;padding:.05rem .3rem;color:var(--dp-accent);}
/* ── Command table ────────────────────────────────────────────────────────── */
.dp-cmd-table{display:flex;flex-direction:column;gap:.5rem;}
.dp-cmd-row{
  display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:1rem;align-items:center;
  background:var(--dp-surface);border:1px solid var(--dp-border);border-radius:8px;padding:.6rem .85rem;
}
@media(max-width:640px){.dp-cmd-row{grid-template-columns:1fr;gap:.35rem;}}
.dp-cmd-row code{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.77rem;
  color:var(--dp-accent);background:var(--dp-bg);border:1px solid var(--dp-border);
  border-radius:6px;padding:.35rem .55rem;display:block;white-space:pre-wrap;word-break:break-all;
}
.dp-cmd-row span{font-size:.8rem;color:var(--dp-muted);line-height:1.5;}
/* ── Glossary ─────────────────────────────────────────────────────────────── */
.dp-gloss-grid{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;}
@media(max-width:760px){.dp-gloss-grid{grid-template-columns:1fr;}}
.dp-gloss{background:var(--dp-surface);border:1px solid var(--dp-border);border-radius:8px;padding:.75rem .9rem;}
.dp-gloss-term{font-size:.83rem;font-weight:700;color:var(--dp-accent);margin-bottom:.22rem;}
.dp-gloss-def{font-size:.79rem;color:var(--dp-muted);line-height:1.55;}
.dp-gloss-def code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.72rem;background:var(--dp-bg);border:1px solid var(--dp-border);border-radius:4px;padding:.04rem .28rem;color:var(--dp-accent2);}
</style>
"""


def _check(name, pattern, example=None, decoder=None):
    ex = f'<pre class="dp-check-code">{example}</pre>' if example else ""
    dec = (f'<a class="dp-check-decoder" href="{decoder}" target="_blank" '
           f'rel="noopener noreferrer">Decoder ↗</a>') if decoder else ""
    return f"""
      <div class="dp-check">
        <div class="dp-check-head">
          <span class="dp-check-name">{name}</span>
          {dec}
        </div>
        <div class="dp-check-pattern">{pattern}</div>
        {ex}
      </div>"""


def _check_group(title, checks):
    grid = "".join(_check(*c) for c in checks)
    return f"""
    <div class="dp-check-group">
      <h3 class="dp-check-group-title">{title}</h3>
      <div class="dp-check-grid">{grid}</div>
    </div>"""


def _faq(q, a):
    return f"""
    <div class="dp-faq">
      <div class="dp-faq-q">{q}</div>
      <div class="dp-faq-a">{a}</div>
    </div>"""


def _steps(items):
    lis = "".join(f"<li>{s}</li>" for s in items)
    return f'<ol class="dp-steps">{lis}</ol>'


def _approach(emoji, title, intro, steps):
    lis = "".join(f"<li>{s}</li>" for s in steps)
    return f"""
    <div class="dp-approach">
      <h4>{emoji} {title}</h4>
      <p class="dp-approach-intro">{intro}</p>
      <ol>{lis}</ol>
    </div>"""


def _cmd(command, desc):
    return f"""
    <div class="dp-cmd-row">
      <code>{command}</code>
      <span>{desc}</span>
    </div>"""


def _gloss(term, defn):
    return f"""
    <div class="dp-gloss">
      <div class="dp-gloss-term">{term}</div>
      <div class="dp-gloss-def">{defn}</div>
    </div>"""


def build_cheatsheet():
    # ── Encoding / cipher identification checklist ───────────────────────────
    id_groups = [
        ("📦 Base Encodings", [
            ("Base64", "Alphanumeric with <code>+</code> and <code>/</code>, often padded with <code>=</code>.",
             "dGhpc2lzYmFzZTY0Y2lwaGVyCg=="),
            ("Base32", "UPPERCASE letters A–Z and digits 2–7, may end with <code>=</code>.",
             "ORUGS43JONRGC43FGMZGG2LQNBSXE==="),
            ("Base85 / Ascii85", "Gibberish using a wide range of printable ASCII symbols.",
             "<+oueBld\\lF(I<gASu!rA8,po/lH7t"),
            ("Base16 (Hex)", "Only 0–9 and a–f. Two characters per byte.",
             "746869732069732068657821"),
        ]),
        ("🔁 ROT / Shift Ciphers", [
            ("ROT13 / ROT-n", "Caesar shift within the 26 letters. Letters only, no symbols changed.", None),
            ("ROT47", "Shifts across 94 printable ASCII characters — includes symbols.",
             "E9:D:DC@Ecf4:A96C"),
            ("Caesar", "Every letter shifted by a fixed amount. Try all 25 shifts.", None),
            ("Atbash", "Alphabet reversed (A↔Z, B↔Y). Self-inverse.", None),
        ]),
        ("🔑 Classical Ciphers", [
            ("Vigenère", "Polyalphabetic; repeating keyword. Bruteforce if key unknown.",
             "elmltwzbrrikpgmisivptxldpcpxpx   key: leet"),
            ("Substitution", "Each letter mapped to another fixed letter. Solve via frequency analysis.", None),
            ("Transposition", "Plaintext letters re-ordered, not substituted (columnar, route, etc.).", None),
            ("A1Z26", "Letters as their alphabet index (1–26), often dash/space separated.",
             "3-20-6 = CTF"),
            ("Rail Fence", "Zig-zag transposition across N rows.", None),
        ]),
        ("📻 Symbol-Based", [
            ("Morse Code", "Dots and dashes (dit-dah), space separated.",
             ".... .. ... .. ... -- --- .-. ... . -.-. --- -.. ."),
            ("Tap Code", "Groups of taps, Polybius-style pairs (1–5).",
             ".... .... .. ... .. .... .... ..."),
            ("Bacon Cipher", "Binary A/B pattern in groups of 5 encoding letters.",
             "BAABAAABBBABAAABAAABABAAAB"),
            ("Polybius Square", "Row/column coordinates into a 5×5 grid.", None),
        ]),
        ("🧬 Unusual Alphabets", [
            ("DNA Encoding", "Uses only A, T, G, C base characters.",
             "GAGTTGAAAATATTGCGGCCGCTGGTAATGAT"),
            ("Braille", "6-dot patterns; often rendered as ⠿ unicode.", None,
             "https://www.branah.com/braille-translator"),
            ("Keyboard Shift", "Text shifted by physical QWERTY key positions.", None),
            ("Binary / Decimal", "Streams of 0/1 in bytes, or decimal ASCII codes.",
             "01100011 01110100 01100110"),
        ]),
        ("🧠 Esoteric Languages", [
            ("Brainfuck", "Only <code>+ - &gt; &lt; [ ] . ,</code> characters.",
             "++++++++++[>+>+++>+++++++>++++++++++<<<<-]>>>>."),
            ("JSFuck", "JavaScript using only <code>[ ] ( ) ! +</code>.",
             "[][(![]+[])[+[]]+([![]]+[][[]])[+!+[]+[+[]]]..."),
            ("Malbolge", "Short gibberish string, notoriously hard to write.",
             "('&%:9]!~}|z2Vxwv-,POqponl$Hjig%eB@@>}=<M:9wv6"),
            ("Whitespace", "Program made only of spaces, tabs and newlines (0x20/0x09/0x0A).", None),
            ("Ook!", "Brainfuck variant using only <code>Ook.</code>, <code>Ook?</code>, <code>Ook!</code>.",
             "Ook. Ook? Ook. Ook. Ook! Ook."),
            ("PikaLang", "Pokémon-style tokens: <code>pi</code>, <code>pika</code>, <code>ka</code>, <code>pipi</code>.", None),
            ("COW", "Bovine-themed Brainfuck variant of <code>moo</code>/<code>MOO</code> tokens.", None),
            ("Piet", "Program IS an abstract image; colour blocks are instructions.", None),
            ("Rockstar", "Source written to read like power-ballad song lyrics.", None),
        ]),
    ]
    id_html = "".join(_check_group(title, checks) for title, checks in id_groups)

    # ── Symbol ciphers (with online decoders) ────────────────────────────────
    symbol_checks = [
        ("Pigpen Cipher", "Letters replaced by grid/“pigpen” shapes. Common in puzzles.", None,
         "https://www.dcode.fr/pigpen-cipher"),
        ("Dancing Men", "Stick-figure substitution cipher (Sherlock Holmes).", None,
         "https://www.dcode.fr/dancing-men-cipher"),
        ("Futurama Alien", "Alien glyph substitution from Futurama (two versions).", None,
         "https://www.dcode.fr/futurama-alien-alphabet"),
        ("Hylian (Twilight Princess)", "Zelda: Twilight Princess symbolic script.", None,
         "https://www.dcode.fr/hylian-language-twilight-princess"),
        ("Hylian (Skyward Sword)", "Zelda: Skyward Sword — maps symbols to English letters.", None,
         "https://www.dcode.fr/hylian-language-skyward-sword"),
        ("Hylian (BOTW)", "Zelda: Breath of the Wild symbol script.", None,
         "https://www.dcode.fr/hylian-language-breath-of-the-wild"),
        ("Daggers Alphabet", "Fantasy substitution glyphs.", None,
         "https://www.dcode.fr/daggers-alphabet"),
        ("Gravity Falls", "Mix of Caesar, Atbash, A1Z26 & symbol substitution from the show.", None,
         "https://www.dcode.fr/gravity-falls-bill-cipher"),
        ("Wingdings / Symbols", "Font-based glyph substitution; map back to letters.", None,
         "https://lingojam.com/WingdingsTranslator"),
    ]
    symbol_html = _check_group("🧩 Symbol Ciphers (visual)", symbol_checks)

    # ── RSA attack picker ────────────────────────────────────────────────────
    rsa_checks = [
        ("Classic RSA", "Given n, e, c — decrypt by factoring n into p·q.", None),
        ("Small e (e=3) / Cube Root", "Low exponent + small message where m³ &lt; n → integer cube root of c.", None),
        ("Håstad Broadcast", "Same m sent to many recipients with e=3 → CRT then cube root.", None),
        ("Wiener's Attack", "Public e is large / private d is small → continued fractions recover d.", None),
        ("Common Modulus", "Same n, two coprime exponents e1,e2 → Bézout combine c1,c2.", None),
        ("Chinese Remainder (CRT)", "Given p, q, dp, dq, c → reconstruct the private key and decrypt.", None),
        ("Fermat Factoring", "p and q are close together → factor n quickly.", None),
        ("Twin-Prime RSA", "Moduli n1, n2 from twin primes → their closeness makes factoring easy.", None),
        ("Multi-Prime", "n has more than two prime factors → easier to factor.", None),
    ]
    rsa_html = _check_group("🔐 RSA — pick your attack", rsa_checks)

    # ── Tool directory (by category) ─────────────────────────────────────────
    crypto_tools = [
        ("CyberChef", "https://gchq.github.io/CyberChef/", "Web app for encryption, encoding, compression and data analysis.", ["Browser"]),
        ("dCode.fr", "https://www.dcode.fr/tools-list#cryptography", "Solvers for crypto, maths and encodings online.", ["Browser"]),
        ("Ciphey", "https://github.com/Ciphey/Ciphey", "Automatically decrypt encryptions, decode encodings and crack hashes.", ["Auto"]),
        ("Cryptii", "https://cryptii.com/", "Modular conversion, encoding and encryption online.", ["Browser"]),
        ("Decodify", "https://github.com/s0md3v/Decodify", "Detect and decode encoded strings, recursively.", ["Auto"]),
        ("Rumkin Cipher Tools", "http://rumkin.com/tools/cipher/", "Collection of cipher / encoder tools.", ["Browser"]),
        ("Base65536", "https://github.com/qntm/base65536", "Unicode's answer to Base64.", ["Encoding"]),
        ("Braille Translator", "https://www.branah.com/braille-translator", "Translate braille to text.", ["Encoding"]),
        ("Enigma Machine", "https://summersidemakerspace.ca/projects/enigma-machine/", "Universal Enigma machine simulator.", ["Classical"]),
        ("Vigenère Solver", "https://www.guballa.de/vigenere-solver", "Break Vigenère ciphers without the key.", ["Classical"]),
        ("Quipqiup", "https://quipqiup.com/", "Automated cryptogram / substitution solver.", ["Classical"]),
        ("Polybius Square", "https://www.braingle.com/brainteasers/codes/polybius.php", "Translate letters to grid coordinates.", ["Classical"]),
        ("RsaCtfTool", "https://github.com/RsaCtfTool/RsaCtfTool", "RSA multi-attack tool for common weaknesses.", ["RSA"]),
        ("RSATool", "https://github.com/ius/rsatool", "Calculate RSA and RSA-CRT parameters.", ["RSA"]),
        ("yafu", "https://sourceforge.net/projects/yafu/", "Automated integer factorization.", ["RSA"]),
        ("FeatherDuster", "https://github.com/nccgroup/featherduster", "Automated, modular cryptanalysis tool.", ["Auto"]),
        ("Galois", "http://web.eecs.utk.edu/~jplank/plank/papers/CS-07-593/", "Fast galois field arithmetic library/toolkit.", ["Library"]),
        ("XORTool", "https://github.com/hellman/xortool", "Analyse multi-byte XOR ciphers.", ["XOR"]),
        ("XOR Cracker", "https://wiremask.eu/tools/xor-cracker/", "Guess XOR key length and key to decrypt.", ["XOR"]),
        ("HashExtender", "https://github.com/iagox86/hash_extender", "Perform hash length-extension attacks.", ["Attack"]),
        ("hash-identifier", "https://gitlab.com/kalilinux/packages/hash-identifier", "Simple hash algorithm identifier.", ["Hashes"]),
        ("padding-oracle-attacker", "https://github.com/KishanBagaria/padding-oracle-attacker", "CLI/library to execute padding-oracle attacks.", ["Attack"]),
        ("PadBuster", "https://github.com/AonCyberLabs/PadBuster", "Automated padding-oracle attack script.", ["Attack"]),
        ("PEMCrack", "https://github.com/robertdavidgraham/pemcrack", "Crack SSL PEM files with encrypted private keys.", ["Crack"]),
        ("PKCrack", "https://www.unix-ag.uni-kl.de/~conrad/krypto/pkcrack.html", "PkZip encryption cracker.", ["Crack"]),
        ("Crackstation", "https://crackstation.net/", "Hash cracker backed by a huge lookup database.", ["Hashes"]),
        ("OEIS", "https://oeis.org/", "On-Line Encyclopedia of Integer Sequences.", ["Reference"]),
    ]
    pwn_tools = [
        ("Pwntools", "https://github.com/Gallopsled/pwntools", "CTF framework for writing exploits.", ["Framework"]),
        ("ROPgadget", "https://github.com/JonathanSalwan/ROPgadget", "Framework for ROP exploitation.", ["ROP"]),
        ("Ropper", "https://github.com/sashs/Ropper", "Find gadgets and build ROP chains across architectures.", ["ROP"]),
        ("one_gadget", "https://github.com/david942j/one_gadget", "Find one-gadget execve('/bin/sh') RCE in libc.", ["libc"]),
        ("libformatstr", "https://github.com/hellman/libformatstr", "Simplify format-string exploitation.", ["Fmt"]),
        ("afl", "https://lcamtuf.coredump.cx/afl/", "Security-oriented coverage-guided fuzzer.", ["Fuzzing"]),
        ("honggfuzz", "https://github.com/google/honggfuzz", "Evolutionary, feedback-driven security fuzzer.", ["Fuzzing"]),
        ("Shellcodes Database", "http://shell-storm.org/shellcode/", "Massive database of ready-made shellcode.", ["Shellcode"]),
    ]
    forensics_tools = [
        ("A-Packets", "https://apackets.com/", "Effortless PCAP analysis in the browser.", ["Browser"]),
        ("Autopsy", "https://www.autopsy.com/", "End-to-end open-source digital forensics platform.", ["Disk"]),
        ("Binwalk", "https://github.com/ReFirmLabs/binwalk", "Firmware analysis & embedded extraction tool.", ["Carving"]),
        ("Bulk-extractor", "https://github.com/simsong/bulk_extractor", "High-performance artefact extraction.", ["Artefacts"]),
        ("Bkhive & samdump2", "https://www.kali.org/tools/samdump2/", "Dump SYSTEM and SAM files.", ["Windows"]),
        ("ChromeCacheView", "https://www.nirsoft.net/utils/chrome_cache_view.html", "Read the Chrome browser cache folder.", ["Cache"]),
        ("Creddump", "https://github.com/moyix/creddump", "Dump Windows credentials.", ["Windows"]),
        ("Exiftool", "https://exiftool.org/", "Read, write and edit file metadata.", ["Metadata"]),
        ("Extundelete", "http://extundelete.sourceforge.net/", "Recover deleted files from ext3/ext4.", ["Recovery"]),
        ("firmware-mod-kit", "https://code.google.com/archive/p/firmware-mod-kit/", "Modify firmware images without recompiling.", ["Firmware"]),
        ("Foremost", "http://foremost.sourceforge.net/", "Recover files by headers/footers & structures.", ["Carving"]),
        ("Forensic Toolkit (FTK)", "https://www.exterro.com/forensic-toolkit", "Scan a drive for artefacts, deleted emails & strings.", ["Suite"]),
        ("Forensically", "https://29a.ch/photo-forensics/#forensic-magnifier", "Free online image analysis with many features.", ["Images"]),
        ("MZCacheView", "https://www.nirsoft.net/utils/mozilla_cache_viewer.html", "Read the Firefox/Mozilla cache folder.", ["Cache"]),
        ("NetworkMiner", "https://www.netresec.com/index.ashx?page=NetworkMiner", "Network Forensic Analysis Tool (NFAT).", ["Network"]),
        ("OfflineRegistryView", "https://www.nirsoft.net/utils/offline_registry_view.html", "Read offline Windows registry files.", ["Windows"]),
        ("PhotoRec", "https://www.cgsecurity.org/wiki/PhotoRec", "Recover lost files from disks and media.", ["Recovery"]),
        ("Registry Viewer", "https://accessdata.com/product-download/registry-viewer-2-0-0", "View Windows registry hives.", ["Windows"]),
        ("Scalpel", "https://github.com/sleuthkit/scalpel", "Open-source data carving tool.", ["Carving"]),
        ("The Sleuth Kit", "https://www.sleuthkit.org/", "CLI tools & C library to analyse disk images.", ["Disk"]),
        ("USBRip", "https://github.com/snovvcrash/usbrip", "Track USB device artefacts on Linux.", ["Artefacts"]),
        ("Volatility", "https://github.com/volatilityfoundation/volatility3", "Advanced memory forensics framework.", ["Memory"]),
        ("Wireshark", "https://www.wireshark.org/", "Analyse pcap / pcapng network captures.", ["Network"]),
        ("X-Ways", "https://www.x-ways.net/forensics/index-m.html", "Advanced computer-forensics work environment.", ["Suite"]),
    ]
    stego_tools = [
        ("AperiSolve", "https://aperisolve.fr/", "Runs layered stego analysis on images online.", ["Browser"]),
        ("BPStegano", "https://github.com/TapanSoni/BPStegano", "Python3 LSB steganography.", ["Embed"]),
        ("DeepSound", "https://github.com/Jpinsoft/DeepSound", "Hide secret data inside audio files.", ["Audio"]),
        ("DTMF Detection", "https://unframework.github.io/dtmf-detect/", "Detect phone-button audio frequencies.", ["Audio"]),
        ("DTMF Tones", "http://dialabc.com/sound/detect/index.html", "Decode phone-button (DTMF) tones.", ["Audio"]),
        ("Exif", "http://manpages.ubuntu.com/manpages/trusty/man1/exif.1.html", "Show EXIF information in JPEG files.", ["Metadata"]),
        ("Exiv2", "https://www.exiv2.org/manpage.html", "Image metadata manipulation tool.", ["Metadata"]),
        ("FotoForensics", "https://fotoforensics.com/", "Web-based digital photo forensics (ELA).", ["Images"]),
        ("hipshot", "https://bitbucket.org/eliteraspberries/hipshot/src/master/", "Turn video/photos into a long-exposure image.", ["Images"]),
        ("Image Error Level Analyzer", "https://29a.ch/sandbox/2012/imageerrorlevelanalysis/", "ELA, clone detection & more, web based.", ["Images"]),
        ("Image Steganography", "https://incoherency.co.uk/image-steganography/", "Client-side JS tool to hide/unhide images in LSBs.", ["Embed"]),
        ("ImageMagick", "http://www.imagemagick.org/script/index.php", "Tool for manipulating images.", ["Images"]),
        ("jsteg", "https://github.com/lukechampine/jsteg", "CLI stego tool for JPEG images.", ["JPEG"]),
        ("Magic Eye Solver", "http://magiceye.ecksdee.co.uk/", "Reveal hidden info in Magic-Eye images.", ["Images"]),
        ("Outguess", "https://github.com/resurrecting-open-source-projects/outguess", "Universal steganographic tool.", ["Embed"]),
        ("Pngcheck", "http://www.libpng.org/pub/png/apps/pngcheck.html", "Verify PNG integrity & dump chunk info.", ["PNG"]),
        ("Pngtools", "https://packages.debian.org/sid/pngtools", "Various analysis tools for PNGs.", ["PNG"]),
        ("sigBits", "https://github.com/Pulho/sigBits", "Significant-bits image stego decoder.", ["Images"]),
        ("SmartDeblur", "https://github.com/Y-Vladimir/SmartDeblur", "Restore defocused and blurred images.", ["Images"]),
        ("Snow", "https://darkside.com.au/snow/", "Whitespace steganography tool.", ["Whitespace"]),
        ("Sonic Visualiser", "https://www.sonicvisualiser.org/", "Audio file spectrogram visualisation.", ["Audio"]),
        ("Steganography Online", "https://stylesuxx.github.io/steganography/", "Online stego encoder and decoder.", ["Browser"]),
        ("Stegbreak", "https://linux.die.net/man/1/stegbreak", "Dictionary attacks on JPG stego.", ["Crack"]),
        ("StegCracker", "https://github.com/Paradoxis/StegCracker", "Brute-force hidden data inside files.", ["Crack"]),
        ("stegextract", "https://github.com/evyatarmeged/stegextract", "Detect hidden files and text in images.", ["Extract"]),
        ("Steghide", "https://steghide.sourceforge.net/", "Hide data in image and audio files.", ["Embed"]),
        ("StegOnline", "https://stegonline.georgeom.net/", "Wide range of image stego operations.", ["Browser"]),
        ("Stegosaurus", "https://github.com/AngelKitty/stegosaurus", "Embed payloads within Python bytecode.", ["Embed"]),
        ("StegoVeritas", "https://github.com/bannsec/stegoVeritas", "Yet another all-in-one stego tool.", ["Auto"]),
        ("Stegpy", "https://github.com/dhsdshdhk/stegpy", "Simple LSB-based steganography program.", ["Embed"]),
        ("stegseek", "https://github.com/RickdeJager/stegseek", "Lightning-fast steghide passphrase cracker.", ["Crack"]),
        ("stegsnow", "https://manpages.ubuntu.com/manpages/trusty/man1/stegsnow.1.html", "Whitespace steganography program.", ["Whitespace"]),
        ("Stegsolve", "https://github.com/zardus/ctf-tools/tree/master/stegsolve", "View bit planes & apply stego filters.", ["Images"]),
        ("Zsteg", "https://github.com/zed-0xff/zsteg/", "PNG/BMP LSB stego analysis.", ["PNG"]),
    ]
    reversing_tools = [
        ("Ghidra", "https://ghidra-sre.org/", "NSA software reverse-engineering suite.", ["Decompiler"]),
        ("IDA Pro", "https://hex-rays.com/ida-pro/", "The most-used reversing / disassembly software.", ["Disassembler"]),
        ("radare2", "https://github.com/radareorg/radare2", "UNIX-like RE framework & CLI toolset.", ["Framework"]),
        ("Rizin", "https://github.com/rizinorg/rizin", "Usability-focused fork of radare2.", ["Framework"]),
        ("Binary Ninja", "https://binary.ninja/", "Modern binary-analysis framework.", ["Framework"]),
        ("Hopper", "https://www.hopperapp.com/", "Disassembler/decompiler for macOS & Linux.", ["Disassembler"]),
        ("GDB", "https://www.gnu.org/software/gdb/", "The GNU Project debugger.", ["Debugger"]),
        ("GEF", "https://github.com/hugsy/gef", "GDB Enhanced Features for exploit devs & RE.", ["Debugger"]),
        ("PEDA", "https://github.com/longld/peda", "Python Exploit Development Assistance for GDB.", ["Debugger"]),
        ("Pwndbg", "https://github.com/pwndbg/pwndbg", "Exploit-dev & RE made easy in GDB.", ["Debugger"]),
        ("WinDBG", "http://www.windbg.org/", "Windows debugger distributed by Microsoft.", ["Debugger"]),
        ("angr", "https://github.com/angr/angr", "Powerful binary analysis & symbolic execution.", ["Symbolic"]),
        ("Z3", "https://github.com/Z3Prover/z3", "Theorem prover from Microsoft Research.", ["Solver"]),
        ("miasm", "https://github.com/cea-sec/miasm", "Reverse-engineering framework in Python.", ["Framework"]),
        ("Frida", "https://github.com/frida/", "Dynamic instrumentation toolkit.", ["Dynamic"]),
        ("Objection", "https://github.com/sensepost/objection", "Runtime mobile exploration.", ["Mobile"]),
        ("Androguard", "https://github.com/androguard/androguard", "Full Python tool to play with Android files.", ["Android"]),
        ("ApkTool", "https://ibotpeaches.github.io/Apktool/", "Reverse-engineer closed Android apps.", ["Android"]),
        ("Apk2gold", "https://github.com/lxdvs/apk2gold", "Decompile Android apps to Java.", ["Android"]),
        ("Jadx", "https://github.com/skylot/jadx", "Produce Java source from Android DEX/APK.", ["Android"]),
        ("Java Decompilers", "http://www.javadecompilers.com/", "Online decompiler for Java and APKs.", ["Java"]),
        ("dnSpy", "https://github.com/dnSpy/dnSpy", ".NET debugger and assembly editor.", [".NET"]),
        ("JSDetox", "https://github.com/svent/jsdetox", "JavaScript malware analysis tool.", ["JS"]),
        ("EasyPythonDecompiler", "https://sourceforge.net/projects/easypythondecompiler/", "Decompile Python .pyc bytecode.", ["Python"]),
        ("Uncompyle", "https://github.com/gstarnberger/uncompyle", "Python 2.7 byte-code decompiler.", ["Python"]),
        ("PEfile", "https://github.com/erocarrera/pefile", "Python module to read PE files.", ["PE"]),
        ("BinUtils", "https://www.gnu.org/software/binutils/binutils.html", "Collection of binary tools.", ["Toolkit"]),
        ("CTF_import", "https://github.com/sciencemanx/ctf_import", "Run functions from stripped binaries.", ["Toolkit"]),
        ("CWE_checker", "https://github.com/fkie-cad/cwe_checker", "Find vulnerable patterns in binaries.", ["Analysis"]),
        ("Demovfuscator", "https://github.com/kirschju/demovfuscator", "Deobfuscator for movfuscated binaries.", ["Deobf"]),
        ("Disassembler.io", "https://onlinedisassembler.com/static/home/index.html", "Disassemble on demand, online.", ["Browser"]),
        ("Online Asm/Disasm", "http://shell-storm.org/online/Online-Assembler-and-Disassembler/", "Keystone/Capstone online wrappers.", ["Browser"]),
        ("Compiler Explorer", "https://godbolt.org/", "See source ↔ assembly side by side.", ["Browser"]),
    ]
    web_tools = [
        ("BurpSuite", "https://portswigger.net/burp", "Graphical proxy for testing website security.", ["Proxy"]),
        ("OWASP Zap", "https://owasp.org/www-project-zap/", "Intercepting proxy to replay, debug and fuzz HTTP.", ["Proxy"]),
        ("SQLMap", "https://github.com/sqlmapproject/sqlmap", "Automatic SQL injection & DB takeover.", ["SQLi"]),
        ("Commix", "https://github.com/commixproject/commix", "Automated OS command-injection tool.", ["CmdInj"]),
        ("XSSer", "https://xsser.03c8.net/", "Automated XSS tester.", ["XSS"]),
        ("Arachni", "https://www.arachni-scanner.com/", "Web-application security scanner framework.", ["Scanner"]),
        ("W3af", "https://github.com/andresriancho/w3af", "Web-app attack and audit framework.", ["Scanner"]),
        ("ffuf", "https://github.com/ffuf/ffuf", "Fast web fuzzer written in Go.", ["Fuzzing"]),
        ("dirsearch", "https://github.com/maurosoria/dirsearch", "Web path scanner.", ["Discovery"]),
        ("Dirhunt", "https://github.com/Nekmo/dirhunt", "Find web directories without bruteforce.", ["Discovery"]),
        ("debugHunter", "https://github.com/devploit/debugHunter", "Discover hidden debug parameters & secrets.", ["Discovery"]),
        ("nomore403", "https://github.com/devploit/nomore403", "Bypass 40x access-control responses.", ["Bypass"]),
        ("git-dumper", "https://github.com/arthaud/git-dumper", "Dump an exposed .git repo from a site.", ["Recon"]),
        ("Gopherus", "https://github.com/tarunkant/Gopherus", "Generate gopher payloads for SSRF→RCE.", ["SSRF"]),
        ("Smuggler", "https://github.com/defparam/smuggler", "HTTP request-smuggling / desync testing.", ["Desync"]),
        ("PHPGGC", "https://github.com/ambionics/phpggc", "PHP unserialize() gadget-chain payloads.", ["Deser"]),
        ("ysoserial", "https://github.com/frohoff/ysoserial", "Java deserialization payload generator.", ["Deser"]),
        ("Revelo", "http://www.kahusecurity.com/posts/revelo_javascript_deobfuscator.html", "Analyse obfuscated JavaScript.", ["Deobf"]),
        ("Beautifier.io", "https://beautifier.io/", "Online JavaScript beautifier.", ["JS"]),
        ("ngrok", "https://ngrok.com/", "Secure introspectable tunnels to localhost.", ["Tunnel"]),
        ("Hookbin", "https://hookbin.com/", "Collect, parse and view HTTP requests.", ["Callback"]),
        ("Request Bin", "https://requestbin.com/", "Inspect any event / HTTP request.", ["Callback"]),
        ("REQBIN", "https://reqbin.com/", "Online REST & SOAP API testing tool.", ["API"]),
        ("Postman", "https://www.postman.com/", "Build, debug and test API requests.", ["API"]),
        ("JSFiddle", "https://jsfiddle.net/", "Test JS/CSS/HTML online.", ["Sandbox"]),
    ]
    osint_tools = [
        ("Shodan", "https://www.shodan.io/", "Search engine for internet-connected devices.", ["Recon"]),
        ("BinaryEdge", "https://www.binaryedge.io/", "Scan, acquire & classify public internet data.", ["Recon"]),
        ("theHarvester", "https://github.com/laramies/theHarvester", "Gather emails, names, subdomains, IPs, URLs.", ["Recon"]),
        ("haveibeenpwned", "https://haveibeenpwned.com/", "Check emails/usernames against breaches.", ["Breach"]),
        ("snusbase", "https://snusbase.com/", "Search leaked databases for creds.", ["Breach"]),
        ("dehashed", "https://www.dehashed.com/", "Search engine for hacked databases.", ["Breach"]),
        ("leakcheck", "https://leakcheck.io/", "Check for leaked credentials.", ["Breach"]),
        ("whopostedwhat", "https://whopostedwhat.com/", "Find accounts posting about a topic/event.", ["Social"]),
        ("Graph.tips", "https://graph.tips/", "Search public Facebook data.", ["Social"]),
        ("instant-username-search", "https://instantusername.com/", "Check a username across 100+ sites.", ["Pivot"]),
        ("Social Mapper", "https://github.com/Greenwolf/social_mapper", "Correlate profiles via facial recognition.", ["Social"]),
        ("Creepy", "https://github.com/ilektrojohn/creepy", "Geolocation OSINT from social networks.", ["Geo"]),
        ("WiGLE", "https://wigle.net/", "Worldwide wireless-hotspot database.", ["Wireless"]),
        ("ExifTool", "https://exiftool.org/", "Read/write metadata in files.", ["Metadata"]),
        ("TinEye", "https://tineye.com/", "Reverse image search engine.", ["Images"]),
        ("YandexImages", "https://yandex.com/images/", "Reverse image search engine.", ["Images"]),
    ]
    misc_tools = [
        ("boofuzz", "https://github.com/jtpereyda/boofuzz", "Network protocol fuzzing for humans.", ["Fuzzing"]),
        ("Veles", "https://codisec.com/veles/", "Binary data analysis and visualisation.", ["Analysis"]),
        ("changeme", "https://github.com/ztgrace/changeme", "Default-credential scanner.", ["Creds"]),
        ("Hashcat", "https://hashcat.net/hashcat/", "Advanced GPU password recovery.", ["Cracking"]),
        ("Hydra", "https://www.kali.org/tools/hydra/", "Parallelised network login cracker.", ["Bruteforce"]),
        ("John the Ripper", "https://www.openwall.com/john/", "Open-source password cracker.", ["Cracking"]),
        ("jwt_tool", "https://github.com/ticarpi/jwt_tool", "Test, tweak and crack JSON Web Tokens.", ["JWT"]),
        ("Ophcrack", "https://ophcrack.sourceforge.io/", "Windows password cracker (rainbow tables).", ["Cracking"]),
        ("Patator", "https://github.com/lanjelot/patator", "Multi-purpose modular brute-forcer.", ["Bruteforce"]),
        ("Turbo Intruder", "https://portswigger.net/bappstore/9abaa233088242e8be252cd4ff534988", "Send huge numbers of HTTP requests (Burp).", ["Bruteforce"]),
        ("Brainfuck IDE", "https://copy.sh/brainfuck/", "Brainfuck esoteric language IDE.", ["Esolang"]),
        ("COW", "https://frank-buss.de/cow.html", "Bovine-themed Brainfuck variant.", ["Esolang"]),
        ("Malbolge", "http://www.malbolge.doleczek.pl/", "Malbolge esoteric language solver.", ["Esolang"]),
        ("Ook!", "https://www.dcode.fr/ook-language", "Decode / encode in Ook!.", ["Esolang"]),
        ("Piet", "https://www.bertnase.de/npiet/npiet-execute.php", "Piet (image) language compiler.", ["Esolang"]),
        ("Rockstar", "https://codewithrockstar.com/online", "Language that looks like song lyrics.", ["Esolang"]),
        ("Try It Online", "https://tio.run/", "Interpreters for tons of esoteric languages.", ["Esolang"]),
        ("Any.run", "https://any.run/", "Interactive malware-hunting sandbox.", ["Sandbox"]),
        ("Intezer Analyze", "https://analyze.intezer.com/", "Malware analysis platform.", ["Sandbox"]),
        ("Triage", "https://tria.ge/", "State-of-the-art malware analysis sandbox.", ["Sandbox"]),
    ]
    hash_tools = [
        ("MD5Hashing.net", "https://md5hashing.net/", "Online hash cracker and tools.", ["Browser"]),
        ("CyberChef", "https://gchq.github.io/CyberChef/", "Encode/decode/hash & data analysis.", ["Browser"]),
        ("hash-identifier", "https://gitlab.com/kalilinux/packages/hash-identifier", "Identify different types of hashes.", ["Identify"]),
        ("hashID", "https://github.com/blackploit/hashid", "Identify hash types.", ["Identify"]),
        ("HashTag", "https://github.com/SmeegeSec/HashTag", "Parse and identify password hashes.", ["Identify"]),
        ("hashcat", "https://hashcat.net/hashcat/", "Fast advanced password-recovery utility.", ["Cracking"]),
        ("John the Ripper", "https://www.openwall.com/john/", "Fast password cracker.", ["Cracking"]),
        ("HashPump", "https://github.com/bwall/HashPump", "Exploit hash length-extension attacks.", ["Attack"]),
    ]
    privesc_tools = [
        ("linuxprivchecker", "https://github.com/sleventyeleven/linuxprivchecker", "Foundational Linux privesc guide & script.", ["Linux"]),
        ("Windows-Exploit-Suggester", "https://github.com/AonCyberLabs/Windows-Exploit-Suggester", "Suggest Windows privesc exploits.", ["Windows"]),
        ("linux-smart-enumeration", "https://github.com/diego-treitos/linux-smart-enumeration", "Show relevant Linux security info.", ["Linux"]),
        ("linux-exploit-suggester", "https://github.com/mzet-/linux-exploit-suggester", "Detect Linux kernel security gaps.", ["Linux"]),
        ("LinEnum", "https://github.com/rebootuser/LinEnum", "Scripted local Linux enumeration.", ["Linux"]),
        ("PEASS-ng (Lin/WinPEAS)", "https://github.com/carlospolop/PEASS-ng", "Privilege-escalation awesome scripts suite.", ["Both"]),
        ("GTFOBins", "https://gtfobins.github.io/", "Unix binaries abusable to bypass restrictions.", ["Reference"]),
        ("PowerUp", "https://github.com/PowerShellMafia/PowerSploit/tree/master/Privesc", "Common Windows privesc vectors.", ["Windows"]),
        ("JAWS", "https://github.com/411Hall/JAWS", "Windows privesc enumeration script.", ["Windows"]),
    ]
    net_tools = [
        ("nmap", "https://nmap.org/", "Discover hosts & services on a network.", ["Scanning"]),
        ("Netcat / Ncat", "https://nmap.org/ncat/", "Read/write TCP & UDP connections.", ["Networking"]),
        ("Wireshark", "https://www.wireshark.org/", "Network protocol analyser for captures.", ["Analysis"]),
    ]

    # ── Online practice platforms ────────────────────────────────────────────
    platforms = [
        ("TryHackMe", "https://tryhackme.com/", "Guided, beginner-friendly hands-on rooms.", ["Beginner"]),
        ("picoCTF", "https://picoctf.org/", "Beginner-friendly CTF platform by CMU.", ["Beginner"]),
        ("HackTheBox", "https://www.hackthebox.com/", "A massive hacking playground.", ["Labs"]),
        ("OverTheWire", "https://overthewire.org/wargames/", "Classic Linux/security wargames.", ["Wargame"]),
        ("Hacker101", "https://www.hacker101.com/", "CTF platform by HackerOne.", ["Web"]),
        ("HackThisSite", "https://www.hackthissite.org/", "Free, safe, legal hacker training ground.", ["Practice"]),
        ("CTFlearn", "https://ctflearn.com/", "Learn, practice and compete across categories.", ["Practice"]),
        ("Root-Me", "https://www.root-me.org/", "Hundreds of challenges across domains.", ["Practice"]),
        ("CryptoHack", "https://cryptohack.org/", "Interactive cryptography challenges.", ["Crypto"]),
        ("Cryptopals", "https://cryptopals.com/", "48 practical crypto attack challenges.", ["Crypto"]),
        ("pwn.college", "https://pwn.college/", "World-class free binary-exploitation course.", ["Pwn"]),
        ("Pwnable.kr", "http://pwnable.kr/", "Pwn / exploitation platform.", ["Pwn"]),
        ("Pwnable.tw", "https://pwnable.tw/", "Pwn / exploitation platform.", ["Pwn"]),
        ("Pwnable.xyz", "https://pwnable.xyz/", "Pwn / exploitation platform.", ["Pwn"]),
        ("Reversing.kr", "http://reversing.kr/", "Reverse-engineering platform.", ["Reversing"]),
        ("Crackmes.One", "https://crackmes.one/", "Reverse-engineering crackme library.", ["Reversing"]),
        ("MicroCorruption", "https://microcorruption.com/", "Embedded-security CTF.", ["Embedded"]),
        ("247CTF", "https://247ctf.com/", "Free capture-the-flag hacking environment.", ["Practice"]),
        ("Archive.ooo", "https://archive.ooo/", "Playable archive of DEF CON CTF challenges.", ["Archive"]),
        ("Atenea", "https://atenea.ccn-cert.cni.es/", "Spanish CCN-CERT CTF platform.", ["Practice"]),
        ("Defend the Web", "https://defendtheweb.net/", "Interactive cyber-security platform.", ["Web"]),
        ("Dreamhack.io", "https://dreamhack.io/wargame", "Online wargame.", ["Wargame"]),
        ("echoCTF.RED", "https://echoctf.red/", "Online hacking laboratories.", ["Labs"]),
        ("Flagyard", "https://flagyard.com/", "Hands-on cybersecurity challenge playground.", ["Practice"]),
        ("Hackropole", "https://hackropole.fr/en/", "Replay France Cybersecurity Challenge tasks.", ["Archive"]),
        ("VibloCTF", "https://ctf.viblo.asia/landing", "CTF training platform.", ["Practice"]),
        ("VulnHub", "https://www.vulnhub.com/", "Downloadable vulnerable VMs.", ["VMs"]),
        ("W3Challs", "https://w3challs.com/", "Hacking / CTF platform.", ["Practice"]),
        ("WebHacking", "https://webhacking.kr/", "Web challenges platform.", ["Web"]),
        ("Websec.fr", "http://websec.fr/", "Web challenges platform.", ["Web"]),
        ("WeChall", "https://www.wechall.net/active_sites", "Challenge-site directory & forum.", ["Directory"]),
        ("CTFtime", "https://ctftime.org/", "Calendar, rankings & writeups for events.", ["Calendar"]),
    ]

    # ── Self-hosted / deliberately-vulnerable apps ───────────────────────────
    vuln_apps = [
        ("Damn Vulnerable Web App", "https://dvwa.co.uk/", "Classic PHP/MySQL vulnerable web app.", ["Web"]),
        ("OWASP Juice Shop", "https://github.com/juice-shop/juice-shop-ctf", "Modern insecure app + CTF setup tools.", ["Web"]),
        ("AWSGoat", "https://github.com/ine-labs/AWSGoat", "Damn-vulnerable AWS infrastructure.", ["Cloud"]),
        ("GCPGoat", "https://github.com/ine-labs/GCPGoat", "Damn-vulnerable GCP infrastructure.", ["Cloud"]),
        ("CICD-goat", "https://github.com/cider-security-research/cicd-goat", "Deliberately vulnerable CI/CD environment.", ["DevOps"]),
    ]

    # ── Host your own CTF (frameworks) ───────────────────────────────────────
    create_platforms = [
        ("CTFd", "https://github.com/CTFd/CTFd", "Platform to host jeopardy-style CTFs (powers this site).", ["Jeopardy"]),
        ("FBCTF", "https://github.com/facebookarchive/fbctf", "Facebook CTF platform (Jeopardy & King-of-the-Hill).", ["Platform"]),
        ("HackTheArch", "https://github.com/mcpa-stlouis/hack-the-arch", "Scoring server for CTF competitions.", ["Scoring"]),
        ("kCTF", "https://github.com/google/kctf", "Kubernetes-based infrastructure for CTFs.", ["K8s"]),
        ("LibreCTF", "https://github.com/easyctf/librectf", "CTF platform from EasyCTF.", ["Platform"]),
        ("Mellivora", "https://github.com/Nakiami/mellivora", "CTF engine written in PHP.", ["Platform"]),
        ("NightShade", "https://github.com/UnrealAkama/NightShade", "Simple CTF framework.", ["Platform"]),
        ("picoCTF", "https://github.com/picoCTF/picoCTF", "Infrastructure used to run picoCTF.", ["Platform"]),
        ("rCTF", "https://github.com/redpwn/rctf", "CTF platform maintained by redpwn.", ["Platform"]),
        ("RootTheBox", "https://github.com/moloch--/RootTheBox", "CTF scoring engine for wargames.", ["Scoring"]),
        ("ImaginaryCTF", "https://github.com/Et3rnos/ImaginaryCTF", "Platform to host CTFs.", ["Platform"]),
    ]

    # ── Tools for building challenges ────────────────────────────────────────
    create_tools = [
        ("Belkasoft RAM Capturer", "https://belkasoft.com/ram-capturer", "Volatile memory acquisition (forensics challenges).", ["Forensics"]),
        ("Dnscat2", "https://github.com/iagox86/dnscat2", "Tunnel communication through DNS.", ["Forensics"]),
        ("Magnet AXIOM", "https://www.magnetforensics.com/resources/magnet-axiom-2-0-memory-analysis/", "Artifact-centric DFIR tool.", ["Forensics"]),
        ("Registry Dumper", "http://www.kahusecurity.com/posts/registry_dumper_find_and_dump_hidden_registry_keys.html", "Dump the Windows registry.", ["Forensics"]),
        ("MSF JS Obfuscator", "https://github.com/rapid7/metasploit-framework/wiki/How-to-obfuscate-JavaScript-in-Metasploit", "Obfuscate JavaScript in Metasploit (web challenges).", ["Web"]),
    ]

    # ── Writeups & courses ───────────────────────────────────────────────────
    writeups = [
        ("CTFtime Writeups", "https://ctftime.org/writeups", "Community writeups for past CTF events.", ["Writeups"]),
        ("github.com/ctfs", "https://github.com/ctfs", "Large collection of CTF writeups.", ["Writeups"]),
        ("Courgettes.Club", "https://ctf.courgettes.club/", "CTF writeup finder.", ["Writeups"]),
        ("Roppers CTF Bootcamp", "https://www.roppers.org/courses/ctf", "Free CTF bootcamp course.", ["Course"]),
    ]

    # ── Assemble page ────────────────────────────────────────────────────────
    faqs = [
        ("What is a flag in a CTF?",
         "A secret string hidden in a challenge that proves you solved it. Flags usually look like "
         "<code>CTF{example}</code>, <code>flag{...}</code> or <code>whatdahack{...}</code>."),
        ("Do I need to be a hacker or programmer to play?",
         "No. Many challenges are beginner-friendly. Programming and security knowledge help, but you can learn as you go."),
        ("Are CTFs legal?",
         "Yes. CTFs are legal competitions built for learning in a safe, controlled environment."),
        ("Can I play solo or do I need a team?",
         "Both work. Many CTFs allow solo play, but teaming up helps you solve harder challenges and learn faster."),
        ("Where do I find writeups?",
         "Check <a href='https://ctftime.org/writeups' target='_blank' rel='noopener noreferrer'>CTFtime</a> and "
         "<a href='https://github.com/ctfs' target='_blank' rel='noopener noreferrer'>github.com/ctfs</a> for past-challenge writeups."),
    ]
    faq_html = "".join(_faq(q, a) for q, a in faqs)

    # ── Beginner onboarding: the universal workflow ──────────────────────────
    workflow_steps = [
        "<strong>Read the prompt.</strong> Note the category, any hint, and the flag format. "
        "Download every attached file before you start.",
        "<strong>Recon &amp; identify.</strong> Work out <em>what you're looking at</em> — a file type, "
        "an encoding, a running service, or a web technology — before reaching for a tool.",
        "<strong>Research the technique.</strong> Search the challenge keywords plus "
        "<code>CTF writeup</code>. Someone has almost certainly solved something similar.",
        "<strong>Pick the right tool.</strong> Jump to the matching category below and grab the tool "
        "built for that job.",
        "<strong>Solve &amp; extract the flag.</strong> Apply the decode/attack. The flag is usually "
        "text like <code>whatdahack{...}</code>.",
        "<strong>Submit &amp; take notes.</strong> Paste the flag to score, then jot down what worked "
        "so you recognise the pattern next time.",
    ]
    workflow_html = _steps(workflow_steps)

    # ── First moves on any file (recon commands) ─────────────────────────────
    first_moves = [
        ("file mystery", "What kind of file is it <em>really</em>? Ignores the extension."),
        ("strings -n 8 mystery", "Dump readable text — skim it for the flag straight away."),
        ("strings mystery | grep -i flag", "Shortcut: jump directly to a plaintext flag."),
        ("exiftool mystery", "Hidden info in metadata: author, comments, GPS, software."),
        ("binwalk mystery", "Spot files hidden <em>inside</em> the file."),
        ("binwalk -e mystery", "Extract those embedded / appended files."),
        ("xxd mystery | head", "Inspect the first bytes and the magic number."),
        ("unzip -l mystery", "Many formats (docx, apk, jar, pptx) are just ZIP archives."),
    ]
    first_moves_html = f'<div class="dp-cmd-table">{"".join(_cmd(c, d) for c, d in first_moves)}</div>'

    # ── How to approach each category ────────────────────────────────────────
    approaches = [
        ("🔐", "Cryptography", "You're given ciphertext or keys and must recover the plaintext.", [
            "Identify the scheme with the checklist above.",
            "Throw it at <code>CyberChef</code> / <code>dCode</code> first.",
            "For RSA, collect <code>n, e, c</code> and match an attack.",
            "Watch for layered encodings — decode repeatedly until it's text.",
        ]),
        ("🌐", "Web", "Attack a website to reach data or actions you shouldn't have.", [
            "View the page source and <code>/robots.txt</code>.",
            "Open DevTools → check Network, Cookies and Storage.",
            "Try SQLi, XSS, IDOR and path traversal.",
            "Fuzz for hidden paths with <code>ffuf</code> / <code>dirsearch</code>.",
            "Intercept and tamper requests with <code>Burp Suite</code>.",
        ]),
        ("🔍", "Forensics", "Dig a flag out of a file, network capture, or disk image.", [
            "Run <code>file</code>, <code>strings</code>, <code>exiftool</code>, <code>binwalk</code>.",
            "For <code>.pcap</code>, open in Wireshark and follow TCP streams.",
            "Carve deleted or embedded files with <code>foremost</code>.",
            "Analyse memory dumps with <code>Volatility</code>.",
        ]),
        ("🔬", "Reverse Engineering", "Understand a compiled program to find the secret.", [
            "Run <code>file</code> and <code>strings</code> first.",
            "Decompile in <code>Ghidra</code> and read <code>main</code>.",
            "Find the check that validates your input.",
            "Trace the logic, or brute it with <code>angr</code>.",
            "Debug / patch with <code>GDB</code> + <code>pwndbg</code>.",
        ]),
        ("💥", "Binary Exploitation (Pwn)", "Abuse a memory bug in a running binary for a shell.", [
            "Run <code>checksec</code> to see the binary's protections.",
            "Find the bug: overflow, format string, use-after-free.",
            "Craft input with <code>pwntools</code>.",
            "Redirect execution: ret2win, ROP chain, or shellcode.",
            "Pop a shell and <code>cat flag.txt</code>.",
        ]),
        ("🖼️", "Steganography", "Data hidden inside images, audio, or other files.", [
            "Start with <code>AperiSolve</code> / <code>StegOnline</code>.",
            "Run <code>strings</code> and <code>binwalk</code> on the file.",
            "Inspect the bit planes in <code>Stegsolve</code>.",
            "For audio, view the spectrogram in Sonic Visualiser.",
            "Try <code>steghide</code> / <code>zsteg</code> (crack the passphrase).",
        ]),
        ("👁️", "OSINT", "Find the answer using only public information.", [
            "Note every name, handle, image and coordinate.",
            "Reverse-image search with <code>TinEye</code> / Yandex.",
            "Pivot usernames across sites.",
            "Read EXIF for GPS and timestamps.",
            "Cross-check social media, maps and Street View.",
        ]),
        ("🎲", "Misc", "Everything else — scripting, esolangs, and jails.", [
            "Read the prompt for the real puzzle.",
            "Identify weird languages with the checklist above.",
            "If it says <code>nc host port</code>, just connect and read.",
            "Automate repetitive input with <code>pwntools</code> / Python.",
        ]),
    ]
    approach_html = f'<div class="dp-approach-grid">{"".join(_approach(*a) for a in approaches)}</div>'

    # ── Essential commands ───────────────────────────────────────────────────
    commands = [
        ("nc &lt;host&gt; &lt;port&gt;", "Connect to a remote challenge service."),
        ('grep -rInso "flag{.*}" .', "Recursively hunt a flag across files."),
        ("echo &lt;b64&gt; | base64 -d", "Decode a Base64 string."),
        ("xxd -r -p &lt;&lt;&lt; &lt;hex&gt;", "Turn a hex string back into raw bytes."),
        ("python3 -m http.server 8000", "Serve files or catch a callback."),
        ("chmod +x ./chall &amp;&amp; ./chall", "Make a downloaded binary runnable."),
        ("curl -s &lt;url&gt;", "Fetch a page or API without a browser."),
        ("ssh user@&lt;host&gt;", "Log into a remote machine."),
    ]
    commands_html = f'<div class="dp-cmd-table">{"".join(_cmd(c, d) for c, d in commands)}</div>'

    # ── Glossary ─────────────────────────────────────────────────────────────
    glossary = [
        ("Flag", "The secret string that proves you solved a challenge, e.g. <code>whatdahack{...}</code>."),
        ("Jeopardy", "The common CTF format: pick standalone challenges off a board for points."),
        ("Payload", "The crafted input or data you send to trigger a bug."),
        ("Shell", "Command-line access to a machine — the usual goal of pwn/web challenges."),
        ("Reverse shell", "A shell that connects back to <em>you</em>, slipping past firewalls."),
        ("Enumeration", "Systematically listing everything about a target: files, ports, parameters."),
        ("Fuzzing", "Throwing lots of automated inputs to uncover hidden paths or crashes."),
        ("Encoding vs Encryption", "Encoding (Base64/hex) is reversible with no key; encryption needs a key."),
        ("Hash", "A one-way fingerprint of data — you crack it by guessing, not decrypting."),
        ("Rabbit hole", "A tempting dead-end path. If you're stuck for ages, step back and re-read the prompt."),
        ("Endianness", "Byte order (little / big) that matters when building pwn payloads."),
        ("checksec", "A quick look at which security protections a binary was compiled with."),
    ]
    glossary_html = f'<div class="dp-gloss-grid">{"".join(_gloss(t, d) for t, d in glossary)}</div>'

    return CHEATSHEET_STYLE + SHARED_STYLE + f"""
<div class="dp-wrap">

  <div class="dp-hero">
    <span class="dp-hero-icon">🚩</span>
    <h1>CTF Cheatsheet</h1>
    <p class="dp-hero-lead">
      A fast, printable-style checklist for Capture-The-Flag competitions: identify unknown
      encodings and ciphers at a glance, pick the right RSA attack, and jump straight to the
      right tool for every challenge category.
    </p>
  </div>

  <div class="dp-toc">
    <a href="#start">🚀 Start Here</a>
    <a href="#firstmoves">🧭 First Moves</a>
    <a href="#approach">🗺️ Approach</a>
    <a href="#commands">⌨️ Commands</a>
    <a href="#identify">🔎 Identify</a>
    <a href="#crypto">🔐 Crypto</a>
    <a href="#pwn">💥 Pwn</a>
    <a href="#forensics">🔍 Forensics</a>
    <a href="#stego">🖼️ Stego</a>
    <a href="#reversing">🔬 Reversing</a>
    <a href="#web">🌐 Web</a>
    <a href="#osint">👁️ OSINT</a>
    <a href="#misc">🎲 Misc</a>
    <a href="#privesc">🛡️ PrivEsc</a>
    <a href="#hashes">#️⃣ Hashes</a>
    <a href="#network">📡 Network</a>
    <a href="#platforms">🎮 Practice</a>
    <a href="#labs">🧪 Vuln Apps</a>
    <a href="#host">🏗️ Host a CTF</a>
    <a href="#build">🧰 Build</a>
    <a href="#writeups">📝 Writeups</a>
    <a href="#glossary">📖 Glossary</a>
    <a href="#faq">❓ FAQ</a>
  </div>

  <div class="dp-section dp-anchor" id="start">
    <h2 class="dp-section-title"><i class="fas fa-flag-checkered"></i> New to CTFs? Start Here</h2>
    <div class="dp-start">
      <h3>👋 What is a CTF?</h3>
      <p>
        A <strong>Capture-The-Flag</strong> is a friendly hacking competition. You solve puzzles across
        categories like web, crypto and forensics; each one hides a secret <strong>flag</strong> — a string
        such as <code>whatdahack{{y0u_g0t_1t}}</code>. Find it, submit it, score points. You don't need to be
        an expert: many challenges are beginner-friendly and you learn by doing.
      </p>
      <p>
        Stuck? That's normal. Search the challenge topic with the words <code>CTF writeup</code>, read how
        others approached similar problems, and keep notes. Every solve makes the next one faster.
      </p>
    </div>
    <h3 class="dp-check-group-title" style="margin-top:.4rem;">🔁 The universal workflow — repeat for every challenge</h3>
    {workflow_html}
  </div>

  <div class="dp-section dp-anchor" id="firstmoves">
    <h2 class="dp-section-title"><i class="fas fa-terminal"></i> First Moves on Any File</h2>
    <p style="font-size:.85rem;color:var(--dp-muted);margin-bottom:1.4rem;line-height:1.6;">
      Downloaded a mystery file and don't know where to start? Run these first — one of them often reveals
      the flag outright. Replace <code>mystery</code> with your filename.
    </p>
    {first_moves_html}
  </div>

  <div class="dp-section dp-anchor" id="approach">
    <h2 class="dp-section-title"><i class="fas fa-map-signs"></i> How to Approach Each Category</h2>
    <p style="font-size:.85rem;color:var(--dp-muted);margin-bottom:1.4rem;line-height:1.6;">
      Not sure where to begin for a given challenge type? Follow the first few steps for its category,
      then grab the matching tools further down the page.
    </p>
    {approach_html}
  </div>

  <div class="dp-section dp-anchor" id="commands">
    <h2 class="dp-section-title"><i class="fas fa-keyboard"></i> Essential Commands</h2>
    <p style="font-size:.85rem;color:var(--dp-muted);margin-bottom:1.4rem;line-height:1.6;">
      A handful of commands you'll reach for constantly. Copy, tweak the placeholders, and go.
    </p>
    {commands_html}
  </div>

  <div class="dp-section dp-anchor" id="identify">
    <h2 class="dp-section-title"><i class="fas fa-fingerprint"></i> Identify the Encoding / Cipher</h2>
    <p style="font-size:.85rem;color:var(--dp-muted);margin-bottom:1.4rem;line-height:1.6;">
      Got a blob of unknown data? Match its shape against the patterns below, then decode it with
      <a href="https://gchq.github.io/CyberChef/" target="_blank" rel="noopener noreferrer">CyberChef</a> or
      <a href="https://www.dcode.fr/en" target="_blank" rel="noopener noreferrer">dCode</a>.
    </p>
    {id_html}
    {symbol_html}
    {rsa_html}
  </div>

  <div class="dp-anchor" id="crypto">{_section("fas fa-lock", "Cryptography Tools", "".join(_card(*r) for r in crypto_tools))}</div>
  <div class="dp-anchor" id="pwn">{_section("fas fa-bomb", "Binary Exploitation (Pwn) Tools", "".join(_card(*r) for r in pwn_tools))}</div>
  <div class="dp-anchor" id="forensics">{_section("fas fa-search", "Forensics Tools", "".join(_card(*r) for r in forensics_tools))}</div>
  <div class="dp-anchor" id="stego">{_section("fas fa-image", "Steganography Tools", "".join(_card(*r) for r in stego_tools))}</div>
  <div class="dp-anchor" id="reversing">{_section("fas fa-microchip", "Reverse Engineering Tools", "".join(_card(*r) for r in reversing_tools))}</div>
  <div class="dp-anchor" id="web">{_section("fas fa-globe", "Web Tools", "".join(_card(*r) for r in web_tools))}</div>
  <div class="dp-anchor" id="osint">{_section("fas fa-user-secret", "OSINT Tools", "".join(_card(*r) for r in osint_tools))}</div>
  <div class="dp-anchor" id="misc">{_section("fas fa-random", "Misc &amp; Esoteric Tools", "".join(_card(*r) for r in misc_tools))}</div>
  <div class="dp-anchor" id="privesc">{_section("fas fa-user-shield", "Privilege Escalation", "".join(_card(*r) for r in privesc_tools))}</div>
  <div class="dp-anchor" id="hashes">{_section("fas fa-hashtag", "Hash Cracking", "".join(_card(*r) for r in hash_tools))}</div>
  <div class="dp-anchor" id="network">{_section("fas fa-network-wired", "Network Utilities", "".join(_card(*r) for r in net_tools))}</div>
  <div class="dp-anchor" id="platforms">{_section("fas fa-gamepad", "Online Practice Platforms", "".join(_card(*r) for r in platforms))}</div>
  <div class="dp-anchor" id="labs">{_section("fas fa-flask", "Vulnerable Apps &amp; Labs", "".join(_card(*r) for r in vuln_apps))}</div>
  <div class="dp-anchor" id="host">{_section("fas fa-server", "Host Your Own CTF", "".join(_card(*r) for r in create_platforms))}</div>
  <div class="dp-anchor" id="build">{_section("fas fa-tools", "Challenge-Creation Tools", "".join(_card(*r) for r in create_tools))}</div>
  <div class="dp-anchor" id="writeups">{_section("fas fa-book", "Writeups &amp; Courses", "".join(_card(*r) for r in writeups))}</div>

  <div class="dp-section dp-anchor" id="glossary">
    <h2 class="dp-section-title"><i class="fas fa-spell-check"></i> Glossary — Words You'll Hear</h2>
    <p style="font-size:.85rem;color:var(--dp-muted);margin-bottom:1.4rem;line-height:1.6;">
      New terms come thick and fast in CTFs. Here are the ones worth knowing on day one.
    </p>
    {glossary_html}
  </div>

  <div class="dp-section dp-anchor" id="faq">
    <h2 class="dp-section-title"><i class="fas fa-question-circle"></i> Frequently Asked Questions</h2>
    {faq_html}
  </div>

  <div class="dp-credit">
    Cheatsheet content adapted from the public
    <a href="https://neerajlovecyber.com/ctf-cheatsheet" target="_blank" rel="noopener noreferrer">CTF Cheatsheet by neerajlovecyber</a>,
    curated and re-styled for Whatdahack.
  </div>

</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Page registry
# ─────────────────────────────────────────────────────────────────────────────

PAGES = [
    {"title": "CTF Resources",                "route": "resources",                "content": build_landing()},
    {"title": "CTF Cheatsheet",               "route": "resources/cheatsheet",     "content": build_cheatsheet()},
    {"title": "Web Security",                 "route": "resources/web",            "content": WEB},
    {"title": "Cryptography",                 "route": "resources/crypto",         "content": CRYPTO},
    {"title": "Reverse Engineering",          "route": "resources/reverse-engineering", "content": REVERSE},
    {"title": "Forensics",                    "route": "resources/forensics",      "content": FORENSICS},
    {"title": "Binary Exploitation (Pwn)",    "route": "resources/pwn",            "content": PWN},
    {"title": "Miscellaneous",                "route": "resources/misc",           "content": MISC},
    {"title": "OSINT",                        "route": "resources/osint",          "content": OSINT},
    {"title": "Cloud / DevOps",               "route": "resources/cloud",          "content": CLOUD},
    {"title": "Mobile Security",              "route": "resources/mobile",         "content": MOBILE},
    {"title": "Hardware / IoT",               "route": "resources/hardware",       "content": HARDWARE},
]


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

with app.app_context():
    for data in PAGES:
        existing = Pages.query.filter_by(route=data["route"]).first()
        if existing:
            existing.title   = data["title"]
            existing.content = data["content"]
            existing.format  = "html"
            existing.draft   = False
            existing.hidden  = True   # hide from auto nav bar; accessible via URL
            print(f"  Updated : /{data['route']}")
        else:
            page = Pages(
                title        = data["title"],
                route        = data["route"],
                content      = data["content"],
                format       = "html",
                draft        = False,
                hidden       = True,   # hide from auto nav bar; accessible via URL
                auth_required= False,
            )
            db.session.add(page)
            print(f"  Created : /{data['route']}")
    db.session.commit()
    print("\nAll done — 12 pages written.")
