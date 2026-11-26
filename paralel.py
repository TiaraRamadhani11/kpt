import os, sys, random, hashlib, time
from collections import defaultdict
from multiprocessing import Pool, cpu_count

FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

EKS_TEKS = [".txt", ".csv", ".log", ".json", ".md", ".py"]      # isi berupa teks
EKS_BINER = [".bin", ".dat", ".pdf", ".zip"]                    # isi berupa byte acak

def buat_data(jumlah):
    os.makedirs(FOLDER, exist_ok=True)
    random.seed(42)
    asli = []                                    # daftar (isi, ekstensi)
    for i in range(1, jumlah + 1):
        if asli and random.random() < 0.2:       # 20% file = salinan
            isi, eks = random.choice(asli)           # salinan: isi dan ekstensi sama
        else:
            if random.random() < 0.5:            # 50% file teks, 50% biner
                isi = "".join(f"baris {random.getrandbits(64)}\n"
                              for _ in range(random.randint(10000, 50000))).encode()
                eks = random.choice(EKS_TEKS)
            else:
                isi = random.randbytes(random.randint(300_000, 1_500_000))
                eks = random.choice(EKS_BINER)
            asli.append((isi, eks))
        nama = f"file{i}{eks}"
        with open(os.path.join(FOLDER, nama), "wb") as f:
            f.write(isi)

def hitung_hash(path):
    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest(), path
    except (OSError, PermissionError) as e:
        print(f"Gagal membaca {path}: {e}")
        return None

def kelompokkan(hasil_hash):
    """Ubah daftar (hash, path) menjadi grup duplikat"""
    hasil = defaultdict(list)
    for item in hasil_hash:
        if item:
            hasil[item[0]].append(os.path.relpath(item[1], FOLDER))
    return {h: p for h, p in hasil.items() if len(p) > 1}

def metode_serial(daftar):
    mulai = time.perf_counter()
    hasil_hash = [hitung_hash(p) for p in daftar]
    waktu = time.perf_counter() - mulai
    return kelompokkan(hasil_hash), waktu

def metode_paralel(daftar, worker):
    mulai = time.perf_counter()
    with Pool(worker) as pool:
        hasil_hash = pool.map(hitung_hash, daftar, chunksize=10)
    waktu = time.perf_counter() - mulai
    return kelompokkan(hasil_hash), waktu

if __name__ == "__main__":
    # Pemakaian: python serial_paralel.py [jumlah_file_baru] [jumlah_worker]
    if len(sys.argv) > 1:
        buat_data(int(sys.argv[1]))
    elif not os.path.isdir(FOLDER) or not os.listdir(FOLDER):
        buat_data(500)
    print("Folder data:", FOLDER)
    worker = int(sys.argv[2]) if len(sys.argv) > 2 else cpu_count()

    daftar = [os.path.join(r, n) for r, _, fs in os.walk(FOLDER) for n in fs]

    grup_s, waktu_s = metode_serial(daftar)
    grup_p, waktu_p = metode_paralel(daftar, worker)
    duplikat = sum(len(p) - 1 for p in grup_p.values())

    jenis = defaultdict(int)                     # hitung file per ekstensi
    for p in daftar:
        jenis[os.path.splitext(p)[1]] += 1

    print("\n=== HASIL ===")
    print(f"Jumlah file diperiksa : {len(daftar)}")
    print("Jenis file            :", ", ".join(f"{e}={n}" for e, n in sorted(jenis.items())))
    print(f"Jumlah grup duplikat  : {len(grup_p)}")
    print(f"Jumlah file duplikat  : {duplikat}")

    print("\n=== PERBANDINGAN WAKTU ===")
    print(f"Serial               : {waktu_s:.4f} detik")
    print(f"Paralel ({worker} worker)   : {waktu_p:.4f} detik")

    print("\n=== DAFTAR GRUP DUPLIKAT ===")
    for i, (h, paths) in enumerate(grup_p.items(), 1):
        print(f"Grup {i}")
        for p in sorted(paths):
            print("  -", p)
