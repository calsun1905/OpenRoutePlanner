import sys
import re
sys.path.insert(0, 'backend')
from bert_nlp_engine import get_bert_nlp_engine

engine = get_bert_nlp_engine()
query = "Kadıköy'den Beşiktaş'a rota"
words = re.findall(r'\b[\wğüşıöçĞÜŞİÖÇ]+\b', query)
print('Words:', words)

for word in words:
    emb = engine.bert.encode(word)
    match = engine.places.find_best_match(query=word, query_embedding=emb, threshold=0.50)
    print(f'Word: {word}, Match: {match}')
