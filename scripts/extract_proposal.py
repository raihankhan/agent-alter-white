#!/usr/bin/env python3
"""Locate the proposal document in a checkout and make it readable to the worker.

PDF is read natively by the Read tool. DOCX is a zip archive and cannot be read
directly, so its text is extracted to a sibling .txt file that the worker reads.
This script only reads from the checkout and only writes the extracted text next
to the proposal. It never executes repository content.
"""
import argparse, json, re, sys, zipfile
from pathlib import Path

# Priority order: first match wins.
CANDIDATES = ("project.pdf", "project.docx")
DOCX_PARTS = ("word/document.xml",)


def docx_text(path: Path) -> str:
    """Extract readable paragraph text from a DOCX using only the stdlib."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n in DOCX_PARTS]
        if not names:
            raise ValueError("no word/document.xml in archive")
        xml = z.read(names[0]).decode("utf-8", "replace")

    # Paragraph and line boundaries become newlines; tab and break become tabs.
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    # Drop every remaining tag, then unescape XML entities.
    text = re.sub(r"<[^>]+>", "", xml)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(entity, char)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="path to the checked-out repository")
    ap.add_argument("--output", help="optional path to write the proposal manifest to")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        raise SystemExit(f"Not a directory: {repo}")

    found = next((repo / name for name in CANDIDATES if (repo / name).is_file()), None)
    result = {"proposal_source": None, "readable_path": None, "format": None, "error": None}

    if found is None:
        result["error"] = "not_found"
    else:
        result["proposal_source"] = found.name
        if found.suffix.lower() == ".pdf":
            # PDFs are read directly by the worker with the Read tool.
            result["readable_path"] = str(found)
            result["format"] = "pdf"
        else:
            result["format"] = "docx"
            target = found.with_suffix(".proposal.txt")
            try:
                text = docx_text(found)
                target.write_text(text, encoding="utf-8")
                result["readable_path"] = str(target)
                if not text.strip():
                    result["error"] = "empty_document"
            except Exception as e:
                result["error"] = f"extraction_failed: {e}"

    payload = json.dumps(result, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n")
    print(payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"extract_proposal: {e}", file=sys.stderr)
        sys.exit(1)
