"""
GPU Monitoring Script - PyTorch ile BERT kullanımını izler
"""
import time
import subprocess
import torch

def get_gpu_memory():
    """GPU bellek kullanımını döner"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True
        )
        used, total = result.stdout.strip().split(',')
        return int(used), int(total)
    except:
        return 0, 0

def test_bert_on_gpu():
    """BERT encoding performans test"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from bert_engine import get_bert_engine

    print("=" * 60)
    print("RTX 5070 GPU Monitor - BERT Test")
    print("=" * 60)

    # GPU bilgisi
    print(f"\nPyTorch CUDA: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
    print(f"Compute Capability: {torch.cuda.get_device_capability(0) if torch.cuda.is_available() else 'N/A'}")

    # Başlangıç memory
    used_mb, total_mb = get_gpu_memory()
    print(f"\nBaşlangıç GPU Memory: {used_mb} MB / {total_mb} MB")

    # BERT engine başlat
    print("\n[BERT] Model yükleniyor...")
    engine = get_bert_engine()

    used_mb, total_mb = get_gpu_memory()
    print(f"[BERT] Model yüklendikten sonra: {used_mb} MB / {total_mb} MB")
    print(f"[BERT] Model boyutu: ~{used_mb - 1464} MB (artış)")

    # Encoding test
    print("\n[BERT] Encoding test...")
    test_texts = [
        "Kadıköy'den Beşiktaş'a rota",
        "Taksim Meydanı'ndan Üsküdar'a nasıl giderim",
        "İstanbul'dan Ankara'ya yolculuk",
    ]

    for i, text in enumerate(test_texts, 1):
        start = time.time()
        emb = engine.encode(text)
        elapsed = (time.time() - start) * 1000

        used_mb, total_mb = get_gpu_memory()
        print(f"  {i}. \"{text[:30]}...\"")
        print(f"     Süre: {elapsed:.1f}ms | Memory: {used_mb} MB")

    # Batch encoding test
    print("\n[BERT] Batch encoding test (3 metin)...")
    start = time.time()
    embeddings = engine.encode_batch(test_texts)
    elapsed = (time.time() - start) * 1000
    used_mb, total_mb = get_gpu_memory()
    print(f"  Toplam süre: {elapsed:.1f}ms ({elapsed/len(test_texts):.1f}ms/ort)")
    print(f"  Memory: {used_mb} MB")

    # Memory clear test
    print("\n[BERT] Memory temizleme testi...")
    del embeddings
    import gc
    gc.collect()
    torch.cuda.empty_cache()

    used_mb, total_mb = get_gpu_memory()
    print(f"  Temizlemeden sonra: {used_mb} MB / {total_mb} MB")
    print(f"  (Model hala yüklü: ~{used_mb} MB)")

    print("\n" + "=" * 60)
    print("Test tamamlandı!")
    print("=" * 60)

if __name__ == "__main__":
    test_bert_on_gpu()
