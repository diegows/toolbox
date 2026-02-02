#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
passport-watermark.sh — paranoid watermarking for passport/ID photos

Usage:
  ./passport-watermark.sh --in INPUT.jpg --recipient "Embassy of Spain" [options]

Required:
  --in FILE                 Input image file
  --recipient STRING        Recipient name (who you're sending it to)

Options:
  --name STRING             Your name (default: "COPY HOLDER")
  --purpose STRING          Purpose text (default: "VISA APPLICATION ONLY")
  --date YYYY-MM-DD         Date string (default: today's date)
  --out FILE                Output file (default: ./watermarked_<recipient>_<input>.jpg)
  --outdir DIR              Output directory (default: current directory)
  --maxsize N               Resize longest side down to N px (default: 1400)
  --quality N               JPEG quality (default: 88)
  --opacity N               Main watermark opacity 0..1 (default: 0.28)
  --micro_opacity N         Micro watermark opacity 0..1 (default: 0.15)
  --noise N                 Add Gaussian noise attenuate (0 disables) (default: 0)
  --strip                   Strip metadata at end (default: keep metadata + forensic tags)
  --help                    Show help

Examples:
  ./passport-watermark.sh --in passport.jpg --recipient "Consulate Madrid" --name "Diego W." --purpose "SPANISH VISA"
  ./passport-watermark.sh --in passport.jpg --recipient "Bank Santander" --purpose "KYC" --noise 0.12 --outdir ./out
EOF
}

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing dependency: $1" >&2; exit 1; }
}

sanitize() {
  # Lowercase-ish safe filename token from arbitrary string
  # keeps alnum, dash, underscore; converts spaces to underscores
  echo "$1" | tr ' ' '_' | tr -cd '[:alnum:]_-'
}

# Defaults
NAME="COPY HOLDER"
PURPOSE="VISA APPLICATION ONLY"
DATE="$(date +%F)"
OUT=""
OUTDIR="."
MAXSIZE="1400"
QUALITY="88"
OPACITY="0.28"
MICRO_OPACITY="0.15"
NOISE="0"
DO_STRIP="0"
IN=""
RECIPIENT=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in) IN="$2"; shift 2;;
    --recipient) RECIPIENT="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --purpose) PURPOSE="$2"; shift 2;;
    --date) DATE="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --outdir) OUTDIR="$2"; shift 2;;
    --maxsize) MAXSIZE="$2"; shift 2;;
    --quality) QUALITY="$2"; shift 2;;
    --opacity) OPACITY="$2"; shift 2;;
    --micro_opacity) MICRO_OPACITY="$2"; shift 2;;
    --noise) NOISE="$2"; shift 2;;
    --strip) DO_STRIP="1"; shift;;
    --help|-h) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "$IN" || -z "$RECIPIENT" ]]; then
  echo "ERROR: --in and --recipient are required." >&2
  usage
  exit 1
fi

if [[ ! -f "$IN" ]]; then
  echo "ERROR: input file not found: $IN" >&2
  exit 1
fi

need magick

mkdir -p "$OUTDIR"

in_base="$(basename "$IN")"
in_name="${in_base%.*}"
in_ext="${in_base##*.}"
rec_token="$(sanitize "$RECIPIENT")"

if [[ -z "$OUT" ]]; then
  OUT="${OUTDIR}/watermarked_${rec_token}_${in_name}.jpg"
fi

# Compose watermark text (recipient-specific)
MAIN_TEXT="COPY — ${PURPOSE} — ${NAME} — ${DATE} — FOR: ${RECIPIENT}"
ALT_TEXT="NOT VALID FOR IDENTIFICATION — FOR: ${RECIPIENT}"

# Build micro pattern text (short, repetitive, recipient-bound)
MICRO_TEXT="COPY|${rec_token}|${DATE}|${NAME}"

# Temp files
tmp1="$(mktemp -t passport_wm_1.XXXXXX).png"
tmp2="$(mktemp -t passport_wm_2.XXXXXX).png"
trap 'rm -f "$tmp1" "$tmp2"' EXIT

echo "Input:      $IN"
echo "Recipient:  $RECIPIENT"
echo "Output:     $OUT"

# 1) Normalize + limit size (keep image usable but reduce reuse quality)
# -auto-orient respects EXIF rotation
magick "$IN" -auto-orient -resize "${MAXSIZE}x${MAXSIZE}\>" "$tmp1"

# 2) Big diagonal watermarks (two angles)
magick "$tmp1" \
  -gravity center \
  -pointsize 72 \
  -fill "rgba(120,120,120,${OPACITY})" \
  -annotate 45 "$MAIN_TEXT" \
  -pointsize 50 \
  -fill "rgba(120,120,120,$(python3 - <<PY
o=float("$OPACITY")
print(max(0.05, min(1.0, o*0.8)))
PY
))" \
  -annotate -45 "$ALT_TEXT" \
  "$tmp2"

# 3) Tiled micro-watermark overlay (hard to remove / inpaint)
magick "$tmp2" \
  \( -size 420x220 xc:none \
     -gravity center \
     -pointsize 22 \
     -fill "rgba(150,150,150,${MICRO_OPACITY})" \
     -annotate 0 "$MICRO_TEXT" \
  \) \
  -write mpr:tile +delete \
  -size "$(magick identify -format "%wx%h" "$tmp2")" tile:mpr:tile \
  -compose over -composite \
  "$tmp2"

# 4) Embed forensic metadata tags (recipient-specific)
magick "$tmp2" \
  -set "exif:Artist" "$NAME" \
  -set "exif:Copyright" "COPY — ${PURPOSE} — ${DATE}" \
  -set "exif:UserComment" "Issued for: ${RECIPIENT}. Not valid as ID. Date: ${DATE}." \
  "$tmp2"

# 5) Optional noise (hostile to face-rec / AI enhancement). 0 disables.
if [[ "$NOISE" != "0" ]]; then
  magick "$tmp2" -attenuate "$NOISE" -noise Gaussian "$tmp2"
fi

# 6) Final export
# Keep metadata by default because we added forensic tags. If --strip, wipe everything at end.
if [[ "$DO_STRIP" == "1" ]]; then
  magick "$tmp2" -strip -colorspace sRGB -interlace Plane -quality "$QUALITY" "$OUT"
else
  magick "$tmp2" -colorspace sRGB -interlace Plane -quality "$QUALITY" "$OUT"
fi

echo "Done $OUT"
