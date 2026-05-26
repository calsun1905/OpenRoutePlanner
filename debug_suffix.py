"""Debug: Bert_nlp_engine span extraction'ını incele"""
import sys
sys.path.insert(0, 'backend')

from bert_nlp_engine import extract_candidate_spans, normalize_token_with_role

test_queries = [
    "Kadıköyde kafe Beşiktaşta kasap",
    "Küçükyalıda kafe",
    "Beşiktaşta",
]

print("=" * 70)
print("BERT_NLP_ENGINE SPAN DEBUG")
print("=" * 70)

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"SORGU: {query}")
    print(f"{'='*60}")
    
    spans = extract_candidate_spans(query, max_ngram=3)
    
    for i, span in enumerate(spans[:15]):  # İlk 15 span
        surface = span['surface']
        normalized = span['normalized']
        role_hint = span['role_hint']
        
        print(f"\n  Span {i+1}: surface=\"{surface}\" normalized=\"{normalized}\" role={role_hint}")
        
        # Bert_nlp_engine'in normalize_token_with_role'ı nasıl çalışıyor?
        stem, hint = normalize_token_with_role(surface)
        print(f"    → normalize_token_with_role: stem=\"{stem}\" hint={hint}")
        
        # Benim _extract_location_base
        from segment_extractor_v2 import _extract_location_base, _is_location_suffix_span
        base = _extract_location_base(surface.lower())
        is_loc = _is_location_suffix_span(span)
        print(f"    → _extract_location_base: \"{base}\"")
        print(f"    → _is_location_suffix_span: {is_loc}")