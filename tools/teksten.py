# Maakt risico-teksten.md: alle zichtbare teksten van risico.html, per sectie (eerst de vaste tekst uit de HTML,
# dan de teksten uit de code met regelnummer, sleutel en item), om tekstaanpassingen in aan te leveren.
# De kop van het bestand noemt de commit waaruit het gemaakt is: daarmee vergelijk je later de aangepaste versie.
# Gebruik, in de map van de repo:  python tools/teksten.py risico.html risico-teksten.md

import re, sys, html, subprocess, os
from html.parser import HTMLParser

SRC = sys.argv[1]
OUT = sys.argv[2]
raw = open(SRC, encoding='utf-8').read()
lines = raw.split('\n')
commit = subprocess.run(['git', '-C', os.path.dirname(os.path.abspath(SRC)), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()

body_start = next(i for i, l in enumerate(lines) if l.startswith('<body'))
script_start = next(i for i, l in enumerate(lines) if l.strip() == '<script>')
script_end = next(i for i, l in enumerate(lines) if l.strip() == '</script>' and i > script_start)

# ── 1. Vaste tekst uit de HTML ──────────────────────────────────────────────
BLOCK = {'a', 'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'label', 'figcaption', 'summary', 'td', 'th', 'caption', 'section', 'aside', 'nav', 'footer', 'main', 'ol', 'ul', 'table', 'tr', 'figure', 'details', 'button'}
SKIP = {'svg', 'script', 'style'}
VOID = ('br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr')
OPS = {'maal', 'is'}

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = {}
        self.sec = 'algemeen'
        self.buf = ''
        self.prefix = ''
        self.skip = 0
        self.stack = []
        self.sr = 0
        self.srbuf = ''
        self.lists = []
        self.btn = 0
        self.btnbuf = ''
    def emit(self, text):
        self.out.setdefault(self.sec, []).append(text)
    def flush(self):
        t = re.sub(r'\s+', ' ', self.buf).strip()
        t = re.sub(r'\*\*\s*\*\*', '', t)
        if t and re.search(r'[A-Za-zÀ-ÿ0-9]', t):
            self.emit(self.prefix + t)
        self.buf = ''
        self.prefix = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '') or ''
        if self.skip:
            if tag not in VOID: self.skip += 1
            return
        if tag in SKIP:
            self.skip = 1
            return
        if tag == 'section' and a.get('id'):
            self.flush(); self.sec = a['id']
        if 'sr-only' in cls.split():
            self.sr += 1; self.srbuf = ''
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5'):
            self.flush(); self.prefix = {'h1': '## ', 'h2': '### ', 'h3': '#### ', 'h4': '##### ', 'h5': '###### '}[tag]
        elif tag == 'li':
            self.flush(); self.prefix = ('1. ' if self.lists and self.lists[-1] == 'ol' else '- ')
        elif tag in ('ol', 'ul'):
            self.flush(); self.lists.append(tag)
        elif tag == 'button':
            self.flush(); self.btn += 1; self.btnbuf = ''
        elif tag in BLOCK:
            self.flush()
        if a.get('data-label'):
            self.emit('[knop: ' + a['data-label'] + ']')
        if 'badge' in cls.split():
            self.prefix = '[label] '
        if tag in ('strong', 'b'): self.buf += '**'
        elif tag in ('em', 'i') and not cls: self.buf += '*'
        elif tag == 'br': self.buf += ' / '
        elif tag == 'img' and a.get('alt'): self.buf += '[afbeelding: ' + a['alt'] + '] '
        elif tag == 'canvas' and a.get('aria-label'):
            self.flush(); self.emit('[beschrijving voor schermlezers: ' + a['aria-label'] + ']')
        elif tag == 'output': self.buf += '…'
        if tag not in VOID:
            self.stack.append((tag, 'sr-only' in cls.split()))
    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if self.skip: return
        if tag == 'img' and a.get('alt'): self.buf += '[afbeelding: ' + a['alt'] + '] '
        if tag == 'br': self.buf += ' / '
    def handle_endtag(self, tag):
        if tag == 'section' and not self.skip:
            self.flush(); self.sec = 'algemeen'
        if self.skip:
            self.skip -= 1
            return
        while self.stack:
            t, was_sr = self.stack.pop()
            if was_sr:
                self.sr -= 1
                s = re.sub(r'\s+', ' ', self.srbuf).strip()
                if s and s not in OPS:
                    self.buf += ' [voor schermlezers: ' + s + '] '
            if t == tag: break
        if tag in ('strong', 'b'): self.buf += '**'
        elif tag in ('em', 'i'): self.buf += '*' if self.buf.count('*') % 2 else ''
        if tag == 'button':
            self.btn -= 1
            t = re.sub(r'\s+', ' ', self.btnbuf).strip()
            if t: self.emit('[knop: ' + t + ']')
            self.buf = ''
        elif tag in ('ol', 'ul'):
            self.flush(); self.lists and self.lists.pop()
        elif tag in BLOCK or tag in ('h1', 'h2', 'h3', 'h4', 'h5'):
            self.flush()
    def handle_data(self, d):
        if self.skip: return
        if self.sr: self.srbuf += d; return
        if self.btn: self.btnbuf += d; return
        self.buf += d

p = P()
p.feed('\n'.join(lines[body_start:script_start]))
p.flush()
static = p.out

# ── 2. Teksten in de code ───────────────────────────────────────────────────
TAGS = re.compile(r'<[^>]+>')

def clean(s):
    # stukken van HTML-tags aan het begin of einde van een literal ('" class="x">Tekst' of 'Tekst <span class="')
    if re.search(r'="[^"]*$|^[^<>]*="', s) and '>' not in s and '<' not in s: return ''
    s = re.sub(r'^[^<>]*?=\s*"[^<>]*?>', '', s)
    s = re.sub(r'^\s*"?\s*>', '', s)
    s = re.sub(r'^[^<>]*\)[^<>]*">', '', s)   # staart van een inline onclick="..." voor de knoptekst
    s = re.sub(r'<[a-zA-Z][^>]*$', '', s)
    s = s.replace("\\'", "'").replace('\\"', '"').replace('\\n', ' ').replace('\\u00AD', '').replace('­', '')
    s = re.sub(r'<(strong|b)\b[^>]*>', '**', s); s = re.sub(r'</(strong|b)>', '**', s)
    s = re.sub(r'<em\b[^>]*>', '*', s); s = re.sub(r'</em>', '*', s)
    s = re.sub(r'<br\s*/?>', ' / ', s)
    s = TAGS.sub(' ', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()

DENY = {'id', 'kind', 'side', 'meter', 'type', 'tag', 'owner', 'target', 'excludes', 's', 'kinds', 'f', 'answer', 'ask', 'add', 'remove', 'color', 'song', 'hit', 'surface', 'cls', 'zone', 'icon'}
def visible(rawlit, txt, data=False, key=''):
    if not re.search(r'[A-Za-zÀ-ÿ]', txt): return False
    if len(txt) < 2: return False
    if re.search(r'grid-|\]\s*\.\w|^[;:]\w|^"\]', txt): return False
    if re.fullmatch(r'[A-G#b0-9\.\-!\s,]+', txt): return False            # muziekpatronen
    if re.fullmatch(r'[\.a-z0-9#]{5,}', txt) and '.' in txt: return False  # pixelmaskers
    if ' ' not in txt:
        if not (txt[:1].isupper() or re.search(r'[!?:…]', txt) or (data and key not in DENY and re.fullmatch(r'[a-zà-ÿ\-]{3,}', txt))): return False
        if re.fullmatch(r'[A-Z][a-z]+[A-Z]\w*', txt): return False          # camelCase
        if txt in ('Escape', 'Enter', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab'): return False
    if re.search(r'(^|\s)(px|rem|rgba|var\(--|cubic-bezier|translate\(|rotate\(|https?://|\.png|repeating-|linear-gradient|scaleY|scaleX)', rawlit): return False
    if re.fullmatch(r'[\w\-]+(\s+[\w\-]+)*', txt) and txt == txt.lower() and len(txt.split()) <= 3 and (len(txt.split()) == 1 or re.search(r'[-_]', txt)) and not re.search(r'[àâéèëêïîôûüç]', txt) and rawlit.strip() == txt and not (data and key not in DENY):
        # gewone kleine woorden zonder leesteken: klassen, ids, sleutels
        return False
    return True

# literalen tokenizen, commentaar en regex-literalen overslaan
def literals(code, base):
    i, n, line = 0, len(code), base
    while i < n:
        c = code[i]
        if c == '\n': line += 1; i += 1; continue
        if code.startswith('//', i):
            j = code.find('\n', i); i = n if j < 0 else j; continue
        if code.startswith('/*', i):
            j = code.find('*/', i); line += code[i:j].count('\n'); i = j + 2; continue
        if c == '/':
            k = i - 1
            while k >= 0 and code[k] in ' \t': k -= 1
            if k < 0 or code[k] in '(,=:[!&|?{};+\n' or code[max(0, k - 5):k + 1].endswith('return'):
                j, cls = i + 1, False
                while j < n and code[j] != '\n':
                    if code[j] == '\\': j += 2; continue
                    if code[j] == '[': cls = True
                    elif code[j] == ']': cls = False
                    elif code[j] == '/' and not cls: break
                    j += 1
                i = j + 1; continue
        if c in '\'"`':
            q, j, start_line = c, i + 1, line
            while j < n and code[j] != q:
                if code[j] == '\\': j += 2; continue
                if code[j] == '\n': line += 1
                j += 1
            yield start_line, i, code[i + 1:j]
            i = j + 1; continue
        i += 1

code = '\n'.join(lines[script_start + 1:script_end])
base = script_start + 2   # 1-gebaseerde regelnummers
heads = [(i + 1, re.sub(r'[═─\s]+$', '', re.sub(r'^\s*//\s*[═─]+\s*', '', l)).strip()) for i, l in enumerate(lines) if re.match(r'^\s*//\s*[═─]{2}', l) and script_start < i < script_end]

def group_of(ln):
    g = None
    for h in heads:
        if h[0] <= ln: g = h
    return g

def decl_of(ln):
    for k in range(ln - 1, script_start, -1):
        m = re.match(r'^(var|function)\s+([A-Za-z_]\w*)', lines[k])
        if m: return ('functie ' if m.group(1) == 'function' else '') + m.group(2)
    return ''

def key_of(ln, pos):
    linestart = code.rfind('\n', 0, pos) + 1
    before = code[linestart:pos]
    m = re.search(r"([A-Za-z_]\w*)\s*:\s*\[?(?:\s*(?:'[^']*'|-?[\d.]+)\s*,)*\s*$", before)
    return m.group(1) if m else ''

def item_of(ln):
    for k in range(ln - 1, max(script_start, ln - 40), -1):
        l = lines[k]
        if re.match(r'^(var|function)\s', l): return ''
        m = re.search(r"\bid:\s*'([\w\-]+)'", l)
        if m: return m.group(1)
    return ''

SKIP_DECL = {'FROG_SONGS', 'NICO_TOP', 'NICO_LEGS_A', 'NICO_LEGS_B', 'DUO', 'FS_OVER_OST', 'FS_RAD_CH', 'FROG_TUNE', 'PP_ICONS', 'PP_BUG_SVG', 'FROG_KINDS', 'PROGRESS_SECTIONS', 'SB_LAYOUT', 'RAD_KEEP', 'VERDICT_ICON', 'miniWheel'}
code_texts = []
for ln, pos, lit in literals(code, base):
    txt = clean(lit)
    d = decl_of(ln)
    dn = d.replace('functie ', '')
    if dn in SKIP_DECL or dn.startswith(('FS_', 'DUO_', 'FROG_DISC')): continue
    k = key_of(ln, pos)
    isdata = bool(re.fullmatch(r'[A-Z][A-Z0-9_]+', d)) and (bool(k) or lines[ln - 1].startswith('var '))
    if isdata and k in DENY: continue
    if not visible(lit, txt, isdata, k): continue
    code_texts.append((ln, group_of(ln), d, k, item_of(ln), txt))

# ── 3. Indeling per paginasectie ────────────────────────────────────────────
SECTIONS = [
    ('algemeen', 'Algemeen: navigatie, welkom, meldingen, voettekst', None),
    ('kans-gevolg', 'Risico = Kans × Gevolg', '#kans-gevolg'),
    ('positief-negatief', "Positieve en negatieve risico's", '#positief-negatief'),
    ('product-project', "Product- en projectrisico's", '#product-project'),
    ('register', 'Risicomatrix en risicoregister', '#register'),
    ('meenemen', 'Wat neem je mee?', '#meenemen'),
]
def heads_line(prefix):
    return next(h[0] for h in heads if h[1].startswith(prefix))
nav_line = heads_line('Navigatie')
def sec_of_code(ln):
    if ln >= nav_line: return 'algemeen'
    g = group_of(ln)
    t = g[1] if g else ''
    if ln < heads_line('Pixel art') and ('Voortgang' in t or 'Gedeeld' in t): return 'algemeen'
    if ln >= heads_line('Nico aan de stoeprand'): return 'kans-gevolg'
    if ln >= heads_line('Risicomatrix en risicoregister'): return 'register'
    if ln >= heads_line("Product- en projectrisico's"): return 'product-project'
    if ln >= heads_line("Deel 1 (positieve"): return 'positief-negatief'
    return 'kans-gevolg'

out = []
w = out.append
w('# Nico neemt risico: alle teksten van de pagina')
w('')
w('Gegenereerd uit `risico.html` (commit `%s`). Per sectie staan eerst de **vaste teksten** (de HTML), daarna de **teksten in de code**: vragen, antwoorden, feedback, knoppen en meldingen die het script toont.' % commit)
w('')
w('Notatie: `**vet**`, `*cursief*`, `[knop: ...]` is een knop, `[label]` is het gouden label boven een sectietitel, `[voor schermlezers: ...]` hoor je enkel met een schermlezer, `[beschrijving voor schermlezers: ...]` beschrijft een animatie. Bij de teksten in de code staat `(regel N)`: het regelnummer in risico.html, en eventueel de naam van het gegeven (`title`, `why`, ...) en het item (`[gedrang]`). Laat die aanduidingen staan, dan vind ik de tekst terug. Een tekst die in stukken staat (bv. `Nico werd **` en `van de 100 keer** geraakt`) wordt in de code aangevuld met een getal of naam.')
w('')
w('## Zo lever je aanpassingen aan')
w('')
w('1. **Pas de tekst rechtstreeks in dit bestand aan** en bewaar het. Je hoeft niets apart te noteren: ik vergelijk het met de oorspronkelijke versie (commit `%s`) en zie zo precies wat je veranderde.' % commit)
w('2. **Laat de aanduidingen staan**: `(regel N)`, `` `sleutel` ``, `[item]`, `[knop: ...]`, de koppen en de lijsttekens. Verander enkel de tekst erachter.')
w('3. **Iets schrappen?** Vervang de tekst door `[weg]`. Wis de regel liever niet: dan weet ik niet zeker of je hem bewust verwijderde.')
w('4. **Iets toevoegen?** Zet een nieuwe regel die begint met `[nieuw]`, op de plaats waar de tekst moet komen.')
w('5. **Een vraag of een idee dat geen gewone tekstwijziging is** (een andere volgorde, een extra antwoordoptie, een ander voorbeeld, een andere score): zet er een regel onder die begint met `> Opmerking:`.')
w('6. **Zinnen in stukken** (bv. `Nico werd **` en `van de 100 keer** geraakt`): pas de stukken gerust aan. Wil je de zin helemaal anders opbouwen, schrijf dan de nieuwe zin in een `> Opmerking:`, dan zet ik hem om.')
w('7. **Huisregels**, die ik ook nakijk: geen gedachtestreepjes (—), en geen hij of zij voor Nico.')
w('')
w('Laat me weten wanneer je klaar bent ("risico-teksten.md is aangepast"). Ik verwerk dan elke wijziging in `risico.html`, kijk na of langere teksten nog passen (knoppen, kaartjes, de gsm, de matrix), en geef je een lijst van wat ik aanpaste en wat ik niet kon of anders deed.')
w('')
w('---')
for sid, title, anchor in SECTIONS:
    w('')
    w('# Sectie: %s%s' % (title, ' (`%s`)' % anchor if anchor else ''))
    w('')
    w('## Vaste tekst')
    w('')
    for t in static.get(sid, []):
        w(t)
        w('')
    items = [c for c in code_texts if sec_of_code(c[0]) == sid]
    if items:
        w('## Teksten in de code')
        last_g, last_d = None, None
        for ln, g, d, key, item, txt in items:
            if g != last_g:
                w(''); w('### %s' % (g[1] if g else 'Algemeen')); w('')
                last_g, last_d = g, None
            if d != last_d:
                if last_d is not None: w('')
                if d: w('*`%s`*' % d); w('')
                last_d = d
            label = ('`%s` ' % key if key else '') + ('[%s] ' % item if item and key else '')
            w('- (regel %d) %s%s' % (ln, label, txt))
    w('')
    w('---')
open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('vast', sum(len(v) for v in static.values()), 'code', len(code_texts), 'regels', len(out))
