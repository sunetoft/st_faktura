"""
Tool_SearchOldInvoices.py

Search old invoice PDFs for free-text matches.

Features:
  * Scans all .pdf files under the 'Fakturaer' folder (relative to project root). If that
    folder does not exist, it falls back to 'invoices'.
  * Free text search (case-insensitive by default; optional --case for case-sensitive).
  * Accepts a search query via command-line argument or interactive prompt loop.
  * Outputs: file path, page number, and a context snippet with matches highlighted.
  * Optional --regex to treat the query as a regular expression.
  * Graceful handling of unreadable PDFs or missing dependencies.

Dependencies:
  * Uses PyPDF2 (already common). If not installed, instruct user to install.

Usage examples:
  python Tool_SearchOldInvoices.py "kunde navnet"
  python Tool_SearchOldInvoices.py --case "Faktura 801"
  python Tool_SearchOldInvoices.py --regex "Faktura\\s+#?80[1-5]"
  python Tool_SearchOldInvoices.py   (then enter queries interactively, blank line to exit)

Exit codes:
  0 - success
  1 - unrecoverable error (e.g., dependency missing and user did not install)

"""
from __future__ import annotations

import os
import sys
import re
import argparse
from typing import Iterable, List, Tuple

try:
    from PyPDF2 import PdfReader  # type: ignore
except ImportError:
    print("PyPDF2 not installed. Install with: pip install PyPDF2", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.abspath(os.path.dirname(__file__))
PRIMARY_FOLDER = os.path.join(ROOT, 'Fakturaer')
FALLBACK_FOLDER = os.path.join(ROOT, 'invoices')

HIGHLIGHT_START = '\x1b[43;30m'  # Yellow background, black text
HIGHLIGHT_END = '\x1b[0m'

# Some terminals (modern Windows Terminal, VS Code, iTerm2, etc.) support OSC 8 hyperlinks.
# We provide optional clickable links unless user disables via --no-links.
OSC8_START = '\x1b]8;;{url}\x1b\\'
OSC8_END = '\x1b]8;;\x1b\\'


def find_invoice_folder() -> str:
    if os.path.isdir(PRIMARY_FOLDER):
        return PRIMARY_FOLDER
    if os.path.isdir(FALLBACK_FOLDER):
        return FALLBACK_FOLDER
    return PRIMARY_FOLDER  # default (may not exist)


def list_pdfs(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    files: List[str] = []
    for entry in os.scandir(folder):
        if entry.is_file() and entry.name.lower().endswith('.pdf'):
            files.append(entry.path)
    return sorted(files)


def extract_pages(pdf_path: str) -> Iterable[Tuple[int, str]]:
    try:
        reader = PdfReader(pdf_path)
        for idx, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ''
            except Exception:
                text = ''
            yield idx + 1, text
    except Exception:
        return  # yield nothing on failure


def compile_pattern(query: str, regex: bool, case_sensitive: bool):
    flags = 0 if case_sensitive else re.IGNORECASE
    if regex:
        return re.compile(query, flags)
    # escape for literal search
    return re.compile(re.escape(query), flags)


def highlight_matches(text: str, pattern: re.Pattern, max_snippets: int = 3, context: int = 40) -> List[str]:
    snippets: List[str] = []
    for i, match in enumerate(pattern.finditer(text)):
        if i >= max_snippets:
            break
        start, end = match.start(), match.end()
        left = max(0, start - context)
        right = min(len(text), end + context)
        segment = text[left:start] + HIGHLIGHT_START + text[start:end] + HIGHLIGHT_END + text[end:right]
        # Replace newlines to keep snippet single-line for readability
        segment = segment.replace('\n', ' ')
        snippets.append(segment)
    return snippets


def apply_full_highlight(text: str, pattern: re.Pattern) -> str:
    # Highlight all non-overlapping matches in full text view.
    # To avoid nested escapes, rebuild string manually.
    out = []
    last = 0
    for m in pattern.finditer(text):
        out.append(text[last:m.start()])
        out.append(f"{HIGHLIGHT_START}{text[m.start():m.end()]}{HIGHLIGHT_END}")
        last = m.end()
    out.append(text[last:])
    return ''.join(out).replace('\n', ' ')


def search_pdf(pdf_path: str, pattern: re.Pattern, full: bool) -> List[Tuple[int, List[str]]]:
    hits: List[Tuple[int, List[str]]] = []
    for page_no, text in extract_pages(pdf_path):
        if not text:
            continue
        if pattern.search(text):
            if full:
                snippets = [apply_full_highlight(text, pattern)]
            else:
                snippets = highlight_matches(text, pattern)
            hits.append((page_no, snippets))
    return hits


def make_hyperlink(path: str, enable: bool) -> str:
    if not enable:
        return path
    # Use file URI; on Windows need forward slashes. Replace backslashes.
    uri = path.replace('\\', '/')
    if not uri.startswith('file://'):
        uri = 'file://' + uri
    return f"{OSC8_START.format(url=uri)}{path}{OSC8_END}"


def perform_search(query: str, regex: bool, case_sensitive: bool, links: bool, full: bool) -> int:
    folder = find_invoice_folder()
    pdfs = list_pdfs(folder)
    if not pdfs:
        print(f"No PDF files found in folder: {folder}")
        return 0
    pattern = compile_pattern(query, regex, case_sensitive)
    total_hits = 0
    for pdf in pdfs:
        rel = os.path.relpath(pdf, ROOT)  # kept for potential future filtering
        results = search_pdf(pdf, pattern, full)
        if not results:
            continue
        display_name = make_hyperlink(os.path.abspath(pdf), links)
        print(f"\n==> {display_name}")
        for page_no, snippets in results:
            total_hits += 1
            if snippets:
                for snip in snippets:
                    print(f"  Page {page_no}: {snip}")
            else:
                print(f"  Page {page_no}: (match)")
    if total_hits == 0:
        print("No matches found.")
    else:
        print(f"\nTotal matching pages: {total_hits}")
    return total_hits


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search old invoice PDFs.")
    parser.add_argument('query', nargs='?', help='Search text (omit for interactive mode)')
    parser.add_argument('--regex', action='store_true', help='Treat query as regular expression')
    parser.add_argument('--case', action='store_true', help='Case-sensitive search (default insensitive)')
    parser.add_argument('--no-links', action='store_true', help='Disable clickable hyperlink output')
    parser.add_argument('--full', action='store_true', help='Show full page text for each matching page (slower, noisy)')
    return parser.parse_args(argv)


def interactive_loop(regex: bool, case_sensitive: bool, links: bool, full: bool) -> None:
    print("Entering interactive search mode. Press Enter on empty line to exit.")
    while True:
        try:
            q = input("Search> ").strip()
            if not q:
                print("Exiting.")
                break
            perform_search(q, regex, case_sensitive, links, full)
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
            break


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    links = not args.no_links
    full = args.full
    if args.query:
        perform_search(args.query, args.regex, args.case, links, full)
    else:
        interactive_loop(args.regex, args.case, links, full)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
