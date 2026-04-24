# Tutorial: Building a Terminal Sutta Reader with SuttaCentral API

In this tutorial, we'll walk through the process of fixing a Python script designed to read suttas from the SuttaCentral API and display them beautifully in the terminal using the `rich` library.

## The Goal
Create a CLI tool that:
1.  Fetches sutta metadata (titles, translations).
2.  Retrieves side-by-side Pali and English (or other language) text.
3.  Displays the content in an aligned, readable table.

---

## Step 1: Solving Environment and Dependency Issues

### The "Permission Denied" Problem
When working with virtual environments (`.venv`), you might encounter a "Permission denied" error when trying to run `pip` directly. This happens if the script in `bin/` lacks execute permissions.

**The Fix:**
Instead of calling `./.venv/bin/pip`, use the Python interpreter to run the module:
```bash
./.venv/bin/python3 -m pip install requests rich
```
This bypasses permission issues and ensures you are installing packages into the correct environment.

### Silencing Warnings
The `requests` library sometimes throws a `RequestsDependencyWarning` if specific character detection libraries (`chardet` or `charset_normalizer`) aren't perfectly aligned with its expectations.

**The Fix:**
Add this to the top of your script to keep the output clean for the user:
```python
import warnings
from requests.packages.urllib3.exceptions import DependencyWarning
warnings.filterwarnings("ignore", category=DependencyWarning)
```

---

## Step 2: Navigating the SuttaCentral API

The SuttaCentral API is powerful but has specific structures for different types of data.

### 1. Metadata Lookup
To find available translations, we use the `/api/suttas/{id}` endpoint.
- **Old way:** Looked for a top-level `translations` key.
- **Correct way:** The translations are nested inside the `suttaplex` object.

```python
info_url = f"https://suttacentral.net/api/suttas/{sutta_id}"
data = requests.get(info_url).json()
translations = data.get("suttaplex", {}).get("translations", [])
```

### 2. Fetching Segmented Text
SuttaCentral uses "segmented" data (Bilara) to allow perfect alignment between Pali and translations.
- **Initial attempt:** Tried `/api/suttas/{id}/{author}`. This returned metadata but no actual text segments.
- **The Solution:** Use the `/api/bilarasuttas/` endpoint.

**Endpoint Structure:**
`https://suttacentral.net/api/bilarasuttas/{id}/{author}?lang={lang}`

This returns a JSON object with:
- `root_text`: A dictionary of Pali segments.
- `translation_text`: A dictionary of translated segments.
- `keys_order`: A list ensuring the segments stay in the correct order.

---

## Step 3: Beautiful Terminal Rendering with `Rich`

The `rich` library allows us to create panels and tables. The key is to iterate through the `keys_order` to match the Pali segment with its translation.

```python
from rich.table import Table

table = Table(show_header=True, header_style="bold magenta", box=None)
table.add_column("Pali (Root)", width=50)
table.add_column("Translation", width=60)

root_segments = data.get("root_text", {})
trans_segments = data.get("translation_text", {})
keys = data.get("keys_order", [])

for key in keys:
    table.add_row(root_segments.get(key, ""), trans_segments.get(key, ""))
```

---

## Conclusion
By understanding the specific API endpoints (moving from `/suttas/` to `/bilarasuttas/`) and using `python -m pip` for environment stability, we transformed a failing script into a robust research tool.

**Usage:**
```bash
python sutta-read.py sn56.11 --lang en
```
This will now correctly pull the "Wheel of Dhamma" sutta with side-by-side Pali and English!
