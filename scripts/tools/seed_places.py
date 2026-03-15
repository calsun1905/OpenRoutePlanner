#!/usr/bin/env python3
"""
Seed place names and compute BERT embeddings for them.
Saves results to backend/data/place_names.json and backend/data/place_embeddings.npy

Usage:
  python scripts/tools/seed_places.py --static --local --dynamic --user --out-dir OpenRoutePlanner/backend/data
"""
import os
import sys
import time
import argparse
import json

parser = argparse.ArgumentParser(description="Seed place names and compute BERT embeddings")
parser.add_argument("--static", action="store_true", help="Seed static Turkey places (if available)")
parser.add_argument("--local", action="store_true", help="Seed local_places from app DB")
parser.add_argument("--dynamic", action="store_true", help="Enable OSM dynamic seeding (may call external APIs)")
parser.add_argument("--user", action="store_true", help="Seed user saved locations")
parser.add_argument("--out-dir", default=os.path.join("OpenRoutePlanner","backend","data"), help="Output directory")
args = parser.parse_args()

# Ensure backend is on PYTHONPATH
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, '..', '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

print(f"[seed_places] backend dir: {backend_dir}")

os.environ['ORP_BERT_SEED_STATIC'] = '1' if args.static else '0'
os.environ['ORP_BERT_SEED_LOCAL'] = '1' if args.local else '0'
os.environ['ORP_BERT_SEED_DYNAMIC'] = '1' if args.dynamic else '0'
os.environ['ORP_BERT_SEED_USER_LOCATIONS'] = '1' if args.user else '0'

print('[seed_places] ENV flags:')
print('  ORP_BERT_SEED_STATIC=', os.environ['ORP_BERT_SEED_STATIC'])
print('  ORP_BERT_SEED_LOCAL=', os.environ['ORP_BERT_SEED_LOCAL'])
print('  ORP_BERT_SEED_DYNAMIC=', os.environ['ORP_BERT_SEED_DYNAMIC'])
print('  ORP_BERT_SEED_USER_LOCATIONS=', os.environ['ORP_BERT_SEED_USER_LOCATIONS'])

# Lazy import and initialization
try:
    import importlib
    import bert_nlp_engine as bne

    # Reset singleton if exists (force re-init with new flags)
    try:
        bne._bert_nlp_engine = None
    except Exception:
        pass

    print('[seed_places] Initializing BERT NLP engine (this may download model if not present) ...')
    t0 = time.time()
    engine = bne.get_bert_nlp_engine()
    t1 = time.time()
    print(f'[seed_places] Engine initialized in {t1-t0:.2f}s')

    places = getattr(engine, 'places', None)
    if places is None:
        print('[seed_places] Engine has no places database; aborting')
        sys.exit(1)

    print('[seed_places] Computing embedding matrix (this may take time) ...')
    t2 = time.time()
    embeddings = places.get_embedding_matrix(engine.bert)
    t3 = time.time()
    place_names = places._place_names
    print(f'[seed_places] Computed embeddings for {len(place_names)} places in {t3-t2:.2f}s')

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    names_path = os.path.join(out_dir, 'place_names.json')
    emb_path = os.path.join(out_dir, 'place_embeddings.npy')

    print(f'[seed_places] Saving place names to {names_path}')
    with open(names_path, 'w', encoding='utf-8') as fh:
        json.dump(place_names, fh, ensure_ascii=False, indent=2)

    print(f'[seed_places] Saving embeddings to {emb_path} (numpy .npy)')
    import numpy as np
    np.save(emb_path, embeddings)

    print('[seed_places] Done.')
    print(f'[seed_places] place count: {len(place_names)}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print('[seed_places] ERROR:', e)
    sys.exit(2)
