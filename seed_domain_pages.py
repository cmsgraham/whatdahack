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


def _page(icon, title, lead, official, training, tips, tools=None):
    off_html = "".join(_card(*r) for r in official)
    train_html = "".join(_card(*r) for r in training)

    tool_section = ""
    if tools:
        tool_html = "".join(_card(*r) for r in tools)
        tool_section = _section("fas fa-tools", "Essential Tools", tool_html)

    return SHARED_STYLE + f"""
<div class="dp-wrap">

  <!-- Hero -->
  <div class="dp-hero">
    <span class="dp-hero-icon">{icon}</span>
    <h1>{title}</h1>
    <p class="dp-hero-lead">{lead}</p>
  </div>

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
#  Page registry
# ─────────────────────────────────────────────────────────────────────────────

PAGES = [
    {"title": "CTF Resources",                "route": "resources",                "content": build_landing()},
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
            existing.hidden  = False
            print(f"  Updated : /{data['route']}")
        else:
            page = Pages(
                title        = data["title"],
                route        = data["route"],
                content      = data["content"],
                format       = "html",
                draft        = False,
                hidden       = False,
                auth_required= False,
            )
            db.session.add(page)
            print(f"  Created : /{data['route']}")
    db.session.commit()
    print("\nAll done — 11 pages written.")
