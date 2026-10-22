"""
IdolJapan.store — Unified Catalog Build Pipeline
Executes image normalization, summary generation, group landing pages, sitemap, feeds, schema, and cache versioning.
"""

import subprocess
import sys

STEPS = [
    ("Jacket Image Normalization", ["python", "fix_images.py"]),
    ("Summary Index", ["python", "build_summary.py"]),
    ("Group Landing Pages", ["python", "generate_group_pages.py"]),
    ("Validation Audit", ["python", "validate_catalog.py"]),
    ("XML Sitemap", ["python", "generate_sitemap.py"]),
    ("RSS Feed", ["python", "generate_feed.py"]),
    ("Schema.org Graph", ["python", "generate_schema.py"]),
    ("Offline Service Worker Stamp", ["python", "generate_offline_manifest.py"]),
]

def run_pipeline():
    print("Starting IdolJapan Complete Catalog Build Pipeline...\n")
    for name, cmd in STEPS:
        print(f"==> Running: {name} ({' '.join(cmd)})")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Pipeline stopped on step: {name}")
            sys.exit(result.returncode)
        print(f"Finished: {name}\n")
    print("All catalog assets successfully built and synchronized!")

if __name__ == "__main__":
    run_pipeline()
