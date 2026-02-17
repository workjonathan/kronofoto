import re
import urllib.parse
from pathlib import Path

# Directory to save extracted SVGs
output_dir = Path("extracted_svgs")
output_dir.mkdir(exist_ok=True)

# Pattern to match plain SVG data URIs (no base64)
svg_pattern = re.compile(r'data:image/svg\+xml,([^"]+)')

total_extracted = 0

for scss_file in Path('static/assets').rglob('*.scss'):
    content = scss_file.read_text()
    matches = list(svg_pattern.finditer(content))

    if not matches:
        continue

    new_content = content  # We'll replace inline images here

    for i, match in enumerate(matches, 1):
        data_part = match.group(1)

        # URL-decode the SVG
        svg_bytes = urllib.parse.unquote_to_bytes(data_part)

        # Generate output filename
        out_file = output_dir / f"{scss_file.stem}_{i}.svg"
        out_file.write_bytes(svg_bytes)
        total_extracted += 1

        # Replace the inline data in SCSS with url(...)
        new_content = new_content.replace(
            match.group(0),
            f'../images/{output_dir}/{out_file.name}'
        )
        print(f"Extracted {out_file} ({len(svg_bytes)} bytes)")

    # Write the updated SCSS back
    scss_file.write_text(new_content)
    print(f"Updated SCSS file: {scss_file}")

print(f"\nDone! Extracted {total_extracted} SVGs and updated SCSS files.")
