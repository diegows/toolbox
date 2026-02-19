#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
passport-watermark.sh — paranoid watermarking for passport/ID photos (ImageMagick v7)
Auto-fits watermark text to image (wraps + scales).

Usage:
  ./passport-watermark.sh --recipient "Embassy of Spain - Madrid" --in passport.jpg
  ./passport-watermark.sh --recipient "Bank Santander - KYC" --in *.jpg

Options:
  --recipient STRING        Required. Recipient/org
  --in FILE...              Required. One or more files (supports globs after --in)

  --name STRING             Default: "COPY HOLDER"
  --purpose STRING          Default: "VISA APPLICATION ONLY"
  --date YYYY-MM-DD         Default: today
  --suffix STRING           Default: "_wm_<recipientToken>_<date>"

  --maxsize N               Resize longest side down to N px (default: 1400)
  --quality N               JPEG quality (default: 88)

  --opacity N               Main watermark opacity 0..1 (default: 0.35)
  --micro_opacity N         Micro watermark opacity 0..1 (default: 0.25)

  --noise N                 IM7: -statistic NonPeak amount (0 disables) (default: 0.08)
  --strip                   Strip metadata at end (default: keep + forensic tags)

  --font NAME               Optional font (default: system default)
  --help

Examples:
  ./passport-watermark.sh --recipient "Embassy" --name "Diego" --purpose "VISA" --in *.jpg
  ./passport-watermark.sh --recipient "Bank - KYC" --noise 0.05 --in passport.jpg
EOF
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing dependency: $1" >&2; exit 1; }; }

sanitize() { echo "$1" | tr ' ' '_' | tr -cd '[:alnum:]_-'; }

# Defaults
NAME="COPY HOLDER"
PURPOSE="VISA APPLICATION ONLY"
DATE="$(date +%F)"
MAXSIZE="1400"
QUALITY="88"
# Default profile: HARD BUT STILL USABLE
OPACITY="0.35"
MICRO_OPACITY="0.25"
NOISE="0.08"
DO_STRIP="0"
SUFFIX=""
RECIPIENT=""
FONT=""

declare -a INPUTS=()

# Parse args: --in accepts multiple files until next flag
while [[ $# -gt 0 ]]; do
  case "$1" in
    --recipient) RECIPIENT="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --purpose) PURPOSE="$2"; shift 2;;
    --date) DATE="$2"; shift 2;;
    --suffix) SUFFIX="$2"; shift 2;;
    --maxsize) MAXSIZE="$2"; shift 2;;
    --quality) QUALITY="$2"; shift 2;;
    --opacity) OPACITY="$2"; shift 2;;
    --micro_opacity) MICRO_OPACITY="$2"; shift 2;;
    --noise) NOISE="$2"; shift 2;;
    --strip) DO_STRIP="1"; shift;;
    --font) FONT="$2"; shift 2;;
    --in)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        INPUTS+=("$1")
        shift
      done
      ;;
    --help|-h) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "$RECIPIENT" ]]; then echo "ERROR: --recipient is required." >&2; usage; exit 1; fi
if [[ ${#INPUTS[@]} -lt 1 ]]; then echo "ERROR: provide one or more inputs after --in" >&2; usage; exit 1; fi

need magick

rec_token="$(sanitize "$RECIPIENT")"
[[ -z "$SUFFIX" ]] && SUFFIX="_wm_${rec_token}_${DATE}"

MAIN_TEXT="COPY — ${PURPOSE} — ${NAME} — ${DATE} — FOR: ${RECIPIENT}"
ALT_TEXT="NOT VALID FOR IDENTIFICATION — FOR: ${RECIPIENT}"
MICRO_TEXT="COPY|${rec_token}|${DATE}|${NAME}"

# Builds a diagonal watermark layer that always fits:
# - Creates a text box sized as a % of image (caption wraps)
# - Rotates and composites it
apply_caption_watermark() {
  local base="$1" text="$2" angle="$3" rgba="$4" box_w="$5" box_h="$6" pointsize="$7" out="$8"
  # Always initialize as an array (safe under: set -u)
  local -a font_args=()
  if [[ -n "${FONT:-}" ]]; then
    font_args=( -font "$FONT" )
  fi

  magick "$base" \
    \( -background none \
       -fill "$rgba" \
       ${font_args[@]+"${font_args[@]}"} \
       -gravity center \
       -pointsize "$pointsize" \
       -size "${box_w}x${box_h}" \
       "caption:${text}" \
       -rotate "$angle" \
    \) \
    -gravity center -compose over -composite \
    "$out"
}

# Builds 4 vertical watermark lines spanning top to bottom
apply_vertical_watermarks() {
  local base="$1" text="$2" rgba="$3" img_w="$4" img_h="$5" pointsize="$6" out="$7"
  local -a font_args=()
  if [[ -n "${FONT:-}" ]]; then
    font_args=( -font "$FONT" )
  fi

  # Create a vertical text strip that spans the full height
  # We'll create text, rotate it 90 degrees to make it vertical
  # Text box: width = image height (will become vertical), height = reasonable for text
  local text_box_w text_box_h
  text_box_w="$img_h"
  text_box_h="$(awk -v w="$img_w" 'BEGIN{printf "%d", w*0.18}')"  # 18% of width for text height

  # Position offsets for the 4 lines (20%, 40%, 60%, 80% across width)
  local pos1 pos2 pos3 pos4
  pos1="$(awk -v w="$img_w" 'BEGIN{printf "%d", w*0.20}')"
  pos2="$(awk -v w="$img_w" 'BEGIN{printf "%d", w*0.40}')"
  pos3="$(awk -v w="$img_w" 'BEGIN{printf "%d", w*0.60}')"
  pos4="$(awk -v w="$img_w" 'BEGIN{printf "%d", w*0.80}')"

  magick "$base" \
    \( -background none \
       -fill "$rgba" \
       ${font_args[@]+"${font_args[@]}"} \
       -gravity center \
       -pointsize "$pointsize" \
       -size "${text_box_w}x${text_box_h}" \
       "caption:${text}" \
       -rotate 90 \
    \) -gravity Northwest -geometry "+${pos1}+0" -compose over -composite \
    \( -background none \
       -fill "$rgba" \
       ${font_args[@]+"${font_args[@]}"} \
       -gravity center \
       -pointsize "$pointsize" \
       -size "${text_box_w}x${text_box_h}" \
       "caption:${text}" \
       -rotate 90 \
    \) -gravity Northwest -geometry "+${pos2}+0" -compose over -composite \
    \( -background none \
       -fill "$rgba" \
       ${font_args[@]+"${font_args[@]}"} \
       -gravity center \
       -pointsize "$pointsize" \
       -size "${text_box_w}x${text_box_h}" \
       "caption:${text}" \
       -rotate 90 \
    \) -gravity Northwest -geometry "+${pos3}+0" -compose over -composite \
    \( -background none \
       -fill "$rgba" \
       ${font_args[@]+"${font_args[@]}"} \
       -gravity center \
       -pointsize "$pointsize" \
       -size "${text_box_w}x${text_box_h}" \
       "caption:${text}" \
       -rotate 90 \
    \) -gravity Northwest -geometry "+${pos4}+0" -compose over -composite \
    "$out"
}

process_one() {
  local in="$1"
  [[ -f "$in" ]] || { echo "WARN: skipping (not found): $in" >&2; return 0; }

  local base name out
  base="$(basename "$in")"
  name="${base%.*}"

  out="./${name}${SUFFIX}.jpg"
  if [[ -e "$out" ]]; then
    local i=2
    while [[ -e "./${name}${SUFFIX}_${i}.jpg" ]]; do i=$((i+1)); done
    out="./${name}${SUFFIX}_${i}.jpg"
  fi

  local tmp0 tmp1 tmp2
  tmp0="$(mktemp -t passport_wm_0.XXXXXX).png"
  tmp1="$(mktemp -t passport_wm_1.XXXXXX).png"
  tmp2="$(mktemp -t passport_wm_2.XXXXXX).png"
  trap 'rm -f "$tmp0" "$tmp1" "$tmp2"' RETURN

  echo "-> $in"
  echo "   out: $out"

  # Normalize + limit size (keeps it uploadable but reduces re-use quality)
  magick "$in" -auto-orient -resize "${MAXSIZE}x${MAXSIZE}\>" "$tmp0"

  # Read dimensions
  local W H
  W="$(magick identify -format "%w" "$tmp0")"
  H="$(magick identify -format "%h" "$tmp0")"

  # Point size scales with image height for vertical text, clamped to sane ranges
  local PS_VERT
  PS_VERT="$(awk -v h="$H" 'BEGIN{ps=h*0.021; if(ps<12)ps=12; if(ps>41)ps=41; printf "%d", ps}')"

  # 1) Apply 3 vertical watermark lines spanning top to bottom
  apply_vertical_watermarks "$tmp0" "$MAIN_TEXT" "rgba(120,120,120,${OPACITY})" "$W" "$H" "$PS_VERT" "$tmp2"

  # 3) Tiled micro-watermark overlay (light, repeated)
  local dims
  dims="${W}x${H}"
  magick "$tmp2" \
    \( -size 420x220 xc:none \
       -gravity center \
       -pointsize 22 \
       -fill "rgba(150,150,150,${MICRO_OPACITY})" \
       ${FONT:+-font "$FONT"} \
       -annotate 0 "$MICRO_TEXT" \
    \) \
    -write mpr:tile +delete \
    -size "$dims" tile:mpr:tile \
    -compose over -composite \
    "$tmp2"

  # 4) Forensic metadata (recipient-bound)
  magick "$tmp2" \
    -set "exif:Artist" "$NAME" \
    -set "exif:Copyright" "COPY — ${PURPOSE} — ${DATE}" \
    -set "exif:UserComment" "Issued for: ${RECIPIENT}. Not valid as ID. Date: ${DATE}." \
    "$tmp2"

  # 5) Optional IM7-safe noise (0 disables)
  if [[ "$NOISE" != "0" ]]; then
    magick "$tmp2" -statistic NonPeak "$NOISE" "$tmp2"
  fi

  # 6) Export
  if [[ "$DO_STRIP" == "1" ]]; then
    magick "$tmp2" -strip -colorspace sRGB -interlace Plane -quality "$QUALITY" "$out"
  else
    magick "$tmp2" -colorspace sRGB -interlace Plane -quality "$QUALITY" "$out"
  fi

  echo "   done"
}

for f in "${INPUTS[@]}"; do
  process_one "$f"
done

echo "All done."
