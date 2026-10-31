"""Visual brand checking (Improvement 2): colours, dimensions, format."""

import io
from PIL import Image


def _hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


def _color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def dominant_colors(image, n=8):
    """Return list of (r,g,b) dominant colours using quantization."""
    img = image.convert("RGB")
    # resize for speed
    img = img.copy()
    img.thumbnail((200, 200))
    quantized = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()[: n * 3]
    counts = quantized.getcolors(maxcolors=256 * 256) or []
    # sort by count desc
    counts.sort(reverse=True, key=lambda x: x[0])
    result = []
    for count, idx in counts[:n]:
        i = idx * 3
        if i + 2 < len(palette):
            result.append((palette[i], palette[i+1], palette[i+2]))
    if not result:
        # fallback: most common pixel
        result = [img.getcolors(maxcolors=1000000)[0][1]] if img.getcolors(maxcolors=1000000) else [(0, 0, 0)]
    return result


def check_image(image_bytes, filename, profile_id, approved_colors, brand_assets):
    """Return list of finding dicts for visual issues."""
    findings = []
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return [{"original_text": filename, "issue_type": "visual", "severity": "high",
                 "explanation": "Could not read the image file. Ensure it is a valid image.",
                 "rule_reference": "Visual check: file format", "suggested_correction": "Upload a valid PNG/JPG/SVG image.",
                 "status": "Needs Review", "requires_evidence": False, "confidence": "high",
                 "citation": "Visual check"}]

    width, height = image.size
    fmt = (image.format or "").lower()

    # Format check
    allowed = set()
    for a in brand_assets:
        for f in (a.get("allowed_formats") or "").split(","):
            allowed.add(f.strip().lower())
    if allowed and fmt and fmt not in allowed:
        findings.append({
            "original_text": filename,
            "issue_type": "visual",
            "severity": "medium",
            "explanation": f"Image format '{fmt}' is not in the approved formats: {', '.join(sorted(allowed))}.",
            "rule_reference": "Visual brand rule: allowed formats",
            "suggested_correction": f"Convert to one of: {', '.join(sorted(allowed))}.",
            "status": "Needs Review", "requires_evidence": False, "confidence": "high",
            "citation": "Brand asset rules",
        })

    # Dimension checks
    for a in brand_assets:
        mw = a.get("min_width") or 0
        mh = a.get("min_height") or 0
        if mw and width < mw:
            findings.append({
                "original_text": f"{width}x{height}px",
                "issue_type": "visual",
                "severity": "medium",
                "explanation": f"Image width {width}px is below the minimum {mw}px for {a.get('asset_type', 'asset')}.",
                "rule_reference": f"Brand asset rule: min width {mw}px",
                "suggested_correction": f"Resize to at least {mw}x{mh}px.",
                "status": "Needs Review", "requires_evidence": False, "confidence": "high",
                "citation": "Brand asset rules",
            })
        if mh and height < mh:
            findings.append({
                "original_text": f"{width}x{height}px",
                "issue_type": "visual",
                "severity": "medium",
                "explanation": f"Image height {height}px is below the minimum {mh}px for {a.get('asset_type', 'asset')}.",
                "rule_reference": f"Brand asset rule: min height {mh}px",
                "suggested_correction": f"Resize to at least {mw}x{mh}px.",
                "status": "Needs Review", "requires_evidence": False, "confidence": "high",
                "citation": "Brand asset rules",
            })

    # Colour check
    if approved_colors:
        approved_rgb = [(_hex_to_rgb(c["hex_code"]), c) for c in approved_colors]
        doms = dominant_colors(image, n=6)
        for dc in doms:
            nearest_dist = min(_color_distance(dc, ar[0]) for ar in approved_rgb)
            if nearest_dist > 120:  # threshold: not close to any approved colour
                hexc = "#{:02X}{:02X}{:02X}".format(*dc)
                findings.append({
                    "original_text": hexc,
                    "issue_type": "visual",
                    "severity": "medium",
                    "explanation": f"Dominant colour {hexc} is not close to any approved brand colour.",
                    "rule_reference": "Visual brand rule: approved colour palette",
                    "suggested_correction": "Adjust the image to use approved brand colours: " + ", ".join(c["hex_code"] for c in approved_colors) + ".",
                    "status": "Needs Review", "requires_evidence": False, "confidence": "medium",
                    "citation": "Brand colour palette",
                })

    if not findings:
        findings.append({
            "original_text": filename,
            "issue_type": "visual",
            "severity": "low",
            "explanation": "No visual brand issues detected. Image format, dimensions, and colours are within approved guidelines.",
            "rule_reference": "Visual brand rules",
            "suggested_correction": "No changes needed.",
            "status": "Passed", "requires_evidence": False, "confidence": "high",
            "citation": "Visual brand check",
        })

    return findings