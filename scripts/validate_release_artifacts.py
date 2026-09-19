#!/usr/bin/env python3
"""
scripts/validate_release_artifacts.py

F08 Release Artifact and Source Contract Validator
- Strictly distinguishes Source/Package Contract Validation from Actual Release Artifact Validation.
- Does NOT silently pass via generator fallback when actual artifacts are missing.
- When --pdf-path is provided: performs direct physical validation of PDF (SHA256, page count, text, scores).
- When --zip-path is provided: performs direct physical validation of ZIP (SHA256, testzip, structure, exclusions).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_source_contract() -> Dict[str, Any]:
    """Validate project contracts without requiring built release artifacts."""
    manifest_path = ROOT / "submission_manifest.json"
    if not manifest_path.is_file():
        return {"status": "FAIL", "reason": "submission_manifest.json missing"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pdf_contract = manifest.get("proposal_pdf_submission", {})
    gen_path = ROOT / "scripts/build_phase22_proposal_pdf.py"
    pkg_path = ROOT / "scripts/package_phase22.py"

    checks = {
        "manifest_exists": True,
        "pdf_contract_mode": pdf_contract.get("mode") == "separate_file",
        "pdf_contract_pages": pdf_contract.get("verified_pages") == 5,
        "generator_script_exists": gen_path.is_file(),
        "packaging_script_exists": pkg_path.is_file(),
    }
    all_ok = all(checks.values())
    return {
        "status": "PASS" if all_ok else "FAIL",
        "checks": checks,
    }


def validate_actual_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Validate an actual physical proposal PDF release artifact."""
    if not pdf_path.is_file():
        return {"status": "FAIL", "error": f"PDF file not found: {pdf_path}"}

    sha = digest(pdf_path)
    size = pdf_path.stat().st_size
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)

    if page_count != 5:
        return {
            "status": "FAIL",
            "sha256": sha,
            "page_count": page_count,
            "error": f"Expected exactly 5 pages, got {page_count}",
        }

    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    required_phrases = [
        "말괄량이코물이",
        "신암4동",
        "77.75",
        "상인1동",
        "77.47",
        "범어1동",
        "84.40",
    ]
    missing = [p for p in required_phrases if p not in full_text]
    if missing:
        return {
            "status": "FAIL",
            "sha256": sha,
            "page_count": page_count,
            "missing_evidence": missing,
            "error": f"Missing required text evidence in PDF: {missing}",
        }

    return {
        "status": "PASS",
        "sha256": sha,
        "size_bytes": size,
        "page_count": page_count,
        "team_verified": "말괄량이코물이" in full_text,
        "demo_scores_verified": True,
    }


def validate_actual_zip(zip_path: Path) -> Dict[str, Any]:
    """Validate an actual physical submission ZIP release artifact."""
    if not zip_path.is_file():
        return {"status": "FAIL", "error": f"ZIP file not found: {zip_path}"}

    sha = digest(zip_path)
    size = zip_path.stat().st_size

    with ZipFile(zip_path) as zf:
        corrupted = zf.testzip()
        if corrupted:
            return {"status": "FAIL", "sha256": sha, "error": f"Corrupted file inside ZIP: {corrupted}"}

        namelist = [n for n in zf.namelist() if not n.endswith("/")]
        total_files = len(namelist)

        # Exclusions check
        forbidden_extensions = (".pdf", ".pyc", ".DS_Store")
        for name in namelist:
            if any(name.lower().endswith(ext.lower()) for ext in forbidden_extensions):
                return {
                    "status": "FAIL",
                    "sha256": sha,
                    "error": f"Forbidden file type in submission ZIP: {name}",
                }
            if "__pycache__" in name or ".git/" in name:
                return {
                    "status": "FAIL",
                    "sha256": sha,
                    "error": f"Cache or version control directory found in ZIP: {name}",
                }

        has_manifest = any(n.endswith("submission_manifest.json") for n in namelist)
        has_checksums = any(n.endswith("CHECKSUMS.sha256") for n in namelist)

        if not (has_manifest and has_checksums):
            return {
                "status": "FAIL",
                "sha256": sha,
                "error": "Missing submission_manifest.json or CHECKSUMS.sha256 inside ZIP",
            }

    return {
        "status": "PASS",
        "sha256": sha,
        "size_bytes": size,
        "total_files": total_files,
        "clean_room_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="F08 Artifact Validator")
    parser.add_argument("--pdf-path", type=Path, default=None, help="Path to actual submission PDF")
    parser.add_argument("--zip-path", type=Path, default=None, help="Path to actual submission ZIP")
    args = parser.parse_args()

    print("==================================================")
    print("F08 Release Artifact & Contract Validation")
    print("==================================================")

    # 1. Source Contract Validation
    src_result = validate_source_contract()
    print(f"[CONTRACT] Source Contract: {src_result['status']}")

    # 2. PDF Validation
    if args.pdf_path:
        pdf_res = validate_actual_pdf(args.pdf_path)
        print(f"[PDF ARTIFACT] {args.pdf_path}: {pdf_res['status']}")
        if pdf_res["status"] == "PASS":
            print(f"  SHA-256: {pdf_res['sha256']}")
            print(f"  Pages: {pdf_res['page_count']}")
        else:
            print(f"  Error: {pdf_res.get('error')}")
            sys.exit(1)
    else:
        print("[PDF ARTIFACT] NOT VERIFIED (no --pdf-path provided)")

    # 3. ZIP Validation
    if args.zip_path:
        zip_res = validate_actual_zip(args.zip_path)
        print(f"[ZIP ARTIFACT] {args.zip_path}: {zip_res['status']}")
        if zip_res["status"] == "PASS":
            print(f"  SHA-256: {zip_res['sha256']}")
            print(f"  Files: {zip_res['total_files']}")
        else:
            print(f"  Error: {zip_res.get('error')}")
            sys.exit(1)
    else:
        print("[ZIP ARTIFACT] NOT VERIFIED (no --zip-path provided)")

    print("==================================================")


if __name__ == "__main__":
    main()
