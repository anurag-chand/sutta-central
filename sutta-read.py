import requests
import sys
import argparse
import warnings
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Suppress the RequestsDependencyWarning
from requests.packages.urllib3.exceptions import DependencyWarning
warnings.filterwarnings("ignore", category=DependencyWarning)

# Also suppress the specific warning from requests itself if possible
try:
    from requests import RequestsDependencyWarning
    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    pass

console = Console()

def fetch_sutta(sutta_id, lang="en", author=None, vertical=False, devnagri=False):
    """Fetch sutta data from SuttaCentral API."""
    # 1. Get info about translations
    info_url = f"https://suttacentral.net/api/suttas/{sutta_id}"
    try:
        response = requests.get(info_url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        console.print(f"[red]Error fetching sutta info: {e}[/red]")
        return

    suttaplex = data.get("suttaplex", {})
    translations = suttaplex.get("translations", [])

    # Find the translation
    translation = None
    if author:
        translation = next((t for t in translations if t["author_uid"] == author), None)
    else:
        # Try to find segmented translation first
        translation = next((t for t in translations if t["lang"] == lang and t.get("segmented")), None)
        if not translation:
            translation = next((t for t in translations if t["lang"] == lang), None)

    if not translation:
        console.print(f"[yellow]No translation found for {sutta_id} in {lang}[/yellow]")
        return

    author_uid = translation["author_uid"]
    author_name = translation.get("author", "Unknown")
    title = translation.get("title", suttaplex.get("translated_title", "Untitled"))
    root_title = suttaplex.get("original_title", "Untitled")
    
    # 2. Fetch the actual content using bilarasuttas endpoint for segmented text
    content_url = f"https://suttacentral.net/api/bilarasuttas/{sutta_id}/{author_uid}?lang={lang}"
    try:
        content_res = requests.get(content_url)
        content_res.raise_for_status()
        sutta_data = content_res.json()
    except Exception as e:
        # Fallback to older method if bilarasuttas fails
        console.print(f"[yellow]Segmented content not found at new endpoint, trying fallback...[/yellow]")
        content_url = f"https://suttacentral.net/api/suttas/{sutta_id}/{author_uid}?lang={lang}"
        try:
            content_res = requests.get(content_url)
            content_res.raise_for_status()
            sutta_data = content_res.json()
        except Exception as e2:
            console.print(f"[red]Error fetching content: {e2}[/red]")
            return

    display_sutta(sutta_id, sutta_data, title, root_title, author_name, lang, vertical, devnagri)

def pali_to_devnagri(text):
    """Simple Pāli IAST to Devanagari transliteration."""
    if not text: return ""
    import re
    v = {'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ', 'e': 'ए', 'o': 'ओ'}
    vs = {'a': '', 'ā': 'ा', 'i': 'ि', 'ī': 'ी', 'u': 'ु', 'ū': 'ू', 'e': 'े', 'o': 'ो'}
    c = {
        'kh': 'ख', 'gh': 'घ', 'ch': 'छ', 'jh': 'झ', 'ṭh': 'ठ', 'ḍh': 'ढ', 'th': 'थ', 'dh': 'ध', 'ph': 'फ', 'bh': 'भ',
        'k': 'क', 'g': 'ग', 'ṅ': 'ङ', 'c': 'च', 'j': 'ज', 'ñ': 'ञ',
        'ṭ': 'ट', 'ḍ': 'ड', 'ṇ': 'ण', 't': 'त', 'd': 'द', 'n': 'न',
        'p': 'प', 'b': 'ब', 'm': 'म', 'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व', 's': 'स', 'h': 'ह', 'ḷ': 'ळ'
    }
    
    res = ""
    i = 0
    text = text.lower()
    while i < len(text):
        found_c = False
        for clen in [2, 1]:
            if i + clen <= len(text) and text[i:i+clen] in c:
                base = c[text[i:i+clen]]
                i += clen
                found_v = False
                if i < len(text) and text[i] in vs:
                    res += base + vs[text[i]]
                    i += 1
                    found_v = True
                if not found_v:
                    res += base + '्'
                found_c = True
                break
        
        if found_c: continue
        
        if text[i] in v:
            res += v[text[i]]
            i += 1
        elif text[i] in ['ṃ', 'ṁ']:
            res += 'ं'
            i += 1
        else:
            res += text[i]
            i += 1
            
    res = re.sub(r'्(?=[ ,।\.\!\?])', '', res)
    return res

def display_sutta(uid, data, title, root_title, author, lang, vertical=False, devnagri=False):
    """Format and display the sutta using Rich."""
    
    # Get segments
    root_segments = data.get("root_text", {})
    trans_segments = data.get("translation_text", {})
    
    # If using fallback /api/suttas/ structure
    if not trans_segments and "translation" in data:
        trans_segments = data.get("translation", {}).get("text", {})
        root_segments = data.get("root_text", {}).get("text", {})

    if devnagri:
        root_title = pali_to_devnagri(root_title)
        # We need to copy or modify root_segments
        root_segments = {k: pali_to_devnagri(v) for k, v in root_segments.items()}

    # Header Panel
    console.print(Panel(
        Text.assemble(
            (f"{title}\n", "bold cyan"),
            (f"({root_title})\n", "italic"),
            (f"Translated by {author}", "dim")
        ),
        title=f"SuttaCentral - {uid.upper()}",
        expand=False
    ))

    # Use keys_order if available for correct sequence
    keys = data.get("keys_order", sorted(trans_segments.keys()))

    if vertical:
        for key in keys:
            pali = root_segments.get(key, "")
            trans = trans_segments.get(key, "")
            if pali:
                console.print(Text(pali, style="dim"))
            if trans:
                console.print(Text(trans))
            if pali or trans:
                console.print()
    else:
        # Create Aligned Table
        table = Table(show_header=True, header_style="bold magenta", box=None, padding=(1, 2))
        table.add_column("Pali (Root)", style="dim", width=50)
        table.add_column(f"Translation ({lang.upper()})", width=60)

        for key in keys:
            pali = root_segments.get(key, "")
            trans = trans_segments.get(key, "")
            if pali or trans:
                table.add_row(pali, trans)

        console.print(table)

if __name__ == "__main__":
    description = """
    Read SuttaCentral suttas in the terminal.
    
    Collection IDs (Semantic):
    dn  - Digha Nikaya (Long)        mn  - Majjhima Nikaya (Middle)
    sn  - Samyutta Nikaya (Linked)   an  - Anguttara Nikaya (Numbered)
    kp  - Khuddakapatha              dhp - Dhammapada
    ud  - Udana                      iti - Itivuttaka
    snp - Sutta Nipata               thig- Therigatha
    thag- Theragatha                 vv  - Vimanavatthu
    pv  - Petavatthu                 da  - Dirgha Agama (Chinese)
    ma  - Madhyama Agama (Chinese)   sa  - Samyukta Agama (Chinese)
    
    Referencing (from suttacentral.net/numbering):
    - Primary IDs are semantic (e.g., 'dn1').
    - Segment IDs for precise sections (e.g., 'dn1:10.1').
    - Pali Nikayas follow Mahasangiti numbering.
    """
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", help="Sutta ID (e.g., dn1, mn10, sn56.11)")
    parser.add_argument("--lang", default="en", help="Language code (en, hi, etc.)")
    parser.add_argument("--author", help="Specific author UID (e.g., sujato, bodhi)")
    parser.add_argument("--vertical", action="store_true", help="Display translation below Pali text")
    parser.add_argument("--devnagri", action="store_true", help="Transliterate Pali to Devanagari")

    args = parser.parse_args()
    
    fetch_sutta(args.id.lower(), args.lang, args.author, args.vertical, args.devnagri)
