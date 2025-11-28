#!/usr/bin/env bash
set -euo pipefail

# Root of the project
PROJECT_ROOT="/home/nop/CascadeProjects/freelance_api"
cd "$PROJECT_ROOT"

# Optional: adjust python executable if you use a venv, e.g.
# PYTHON="/home/nop/.virtualenvs/freelance_api/bin/python"
PYTHON="python3"

# --- Python / automation preset ---
$PYTHON search_jobs.py \
  --preset python_daily \
  --output-json data/python_daily_shortlist.json

$PYTHON analyze_jobs.py \
  --input-json data/python_daily_shortlist.json \
  --output-json data/analysis_python_daily_shortlist.json \
  --max-projects 20

$PYTHON generate_bids.py \
  --input-json data/analysis_python_daily_shortlist.json \
  --max-projects 3 \
  --min-score 60 \
  --notify-email

# --- Fullstack preset ---
$PYTHON search_jobs.py \
  --preset fullstack_daily \
  --output-json data/fullstack_daily_shortlist.json

$PYTHON analyze_jobs.py \
  --input-json data/fullstack_daily_shortlist.json \
  --output-json data/analysis_fullstack_daily_shortlist.json \
  --max-projects 20

$PYTHON generate_bids.py \
  --input-json data/analysis_fullstack_daily_shortlist.json \
  --max-projects 3 \
  --min-score 60 \
  --notify-email

# --- Mobile preset ---
$PYTHON search_jobs.py \
  --preset mobile_daily \
  --output-json data/mobile_daily_shortlist.json

$PYTHON analyze_jobs.py \
  --input-json data/mobile_daily_shortlist.json \
  --output-json data/analysis_mobile_daily_shortlist.json \
  --max-projects 20

$PYTHON generate_bids.py \
  --input-json data/analysis_mobile_daily_shortlist.json \
  --max-projects 3 \
  --min-score 60 \
  --notify-email
