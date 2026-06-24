# PNG Analyzer – opis aplikacji

Aplikacja akademicka z przedmiotu **E-Media** (Projekty 1 i 2).  
Celem Projektu 1 jest **ręczna analiza plików PNG** – bez użycia bibliotek typu Pillow/PIL do parsowania formatu. Projekt 2 rozszerza aplikację o **szyfrowanie RSA** masy bitowej IDAT.

---

## Wymagania

- Python 3.10 lub nowszy
- Zależności z pliku `requirements.txt`:
  - `numpy` – operacje na macierzach pikseli i FFT
  - `matplotlib` – wykres widma FFT i wizualizacja ECB/CBC
  - `pytest` – testy jednostkowe
  - `pycryptodome` – porównanie referencyjne RSA (tylko `compare`)

---

## Instalacja i uruchomienie

### 1. Sklonuj / otwórz repozytorium

```bash
cd e-media
```

### 2. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 3. Uruchom aplikację z linii poleceń

Wszystkie komendy wykonujesz przez plik `main.py`:

```bash
# Raport metadanych PNG
python main.py info pwr.png

# Anonimizacja – usunięcie metadanych
python main.py anonymize pwr.png -o pwr_clean.png

# Widmo FFT (okno graficzne)
python main.py fft pwr.png

# Widmo FFT zapisane do pliku (bez okna)
python main.py fft pwr.png --save spectrum.png --no-show

# Test poprawności FFT na obrazie syntetycznym
python main.py fft --verify --no-show

# --- Projekt 2: RSA ---

# Generowanie kluczy RSA
python main.py keygen -o keys/rsa2048.json

# Szyfrowanie (domyślnie: out/<nazwa>_enc_ecb_filtered.png)
python main.py encrypt images/normal.png --public-key keys/rsa2048.json

# CBC + wariant B
python main.py encrypt images/normal.png --public-key keys/rsa2048.json --mode cbc --variant compressed

# Deszyfrowanie (domyślnie: out/<nazwa>_dec_ecb_filtered.png; IV: <plik>.iv)
python main.py decrypt out/normal_enc_ecb_filtered.png --private-key keys/rsa2048.json

# Porównanie z niezależnym pow(m,e,n) — ECB i CBC
python main.py compare images/normal.png --public-key keys/rsa2048.json
python main.py compare images/normal.png --public-key keys/rsa2048.json --mode cbc --iv-file out/normal_enc_cbc_filtered.png.iv

# Wizualizacja (domyślnie: out/<nazwa>_ecb.png, _cbc.png, _ecb_vs_cbc.png)
python main.py visualize images/normal.png --public-key keys/rsa2048.json
```

### 4. Uruchom testy jednostkowe

```bash
python -m pytest tests/ -v
```

---

## Komendy CLI


| Komenda                                                                          | Opis                                                                                                                     |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `info <plik.png>`                                                                | Wyświetla pełny raport: sygnatura, lista chunków z offsetami, atrybuty IHDR, zawartość chunków krytycznych i dodatkowych |
| `anonymize <plik.png> [-o wyjscie.png]`                                          | Usuwa chunki ancillary oraz dane ukryte za IEND; zapisuje „czysty” PNG                                                   |
| `fft <plik.png> [--save plik.png] [--no-show]`                                   | Pokazuje obraz w skali szarości i jego widmo FFT                                                                         |
| `fft --verify [--no-show]`                                                       | Test poprawności FFT na syntetycznym obrazie sinusoidalnym                                                               |
| `keygen [-o klucz.json] [--bits 2048]`                                           | Generuje parę kluczy RSA (JSON)                                                                                          |
| `encrypt <plik> --public-key …` | → `out/<stem>_enc_<mode>_<variant>.png` |
| `decrypt <plik> --private-key …` | → `out/<stem>_dec_<mode>_<variant>.png`; IV domyślnie `<wejście>.iv` |
| `compare <plik> --public-key …` | ECB/CBC vs niezależne `pow(m,e,n)` |
| `visualize <plik> --public-key …` | → `out/<stem>_ecb.png`, `_cbc.png`, `_ecb_vs_cbc.png` |


---

## Jak działa aplikacja

### Przepływ danych

```
Plik PNG (bajty)
    │
    ▼
PNGReader          – sekwencyjny odczyt bajtów
    │
    ▼
PNGSignature       – walidacja 8-bajtowej sygnatury (\x89PNG\r\n\x1a\n)
    │
    ▼
PNGParser          – pętla: length → type → data → CRC
    │                 zapisuje offsety każdego chunka w pliku
    ▼
chunk_factory()    – tworzy obiekt właściwej klasy (IHDR, tEXt, eXIf, …)
    │
    ▼
PNGFile            – kontener z listą chunków i metodami analizy
```

### Struktura pliku PNG

Każdy plik PNG składa się z:

1. **Sygnatury** (8 bajtów) – magic number identyfikujący format
2. **Chunków** – kolejnych segmentów w formacie:

```
[4 bajty: długość danych]
[4 bajty: typ chunka, np. "IHDR", "IDAT", "tEXt"]
[N bajtów: dane]
[4 bajty: suma kontrolna CRC32]
```

### Chunki krytyczne vs. dodatkowe

Typ chunka (4 litery ASCII) koduje właściwości w **bicie 5 każdego bajtu**:


| Właściwość                             | Zasada                 |
| -------------------------------------- | ---------------------- |
| **Krytyczny** (IHDR, PLTE, IDAT, IEND) | pierwsza litera wielka |
| **Dodatkowy** (tEXt, gAMA, eXIf, …)    | pierwsza litera mała   |
| **Publiczny / prywatny**               | druga litera           |
| **Safe to copy**                       | czwarta litera mała    |


Program automatycznie rozpoznaje te flagi i wyświetla je w raporcie `info`.

### Obsługiwane typy chunków

**Krytyczne:** IHDR, PLTE, IDAT, IEND

**Dodatkowe (ancillary):** tEXt, iTXt, zTXt, gAMA, pHYs, tIME, sRGB, cHRM, eXIf

Nieznane typy są obsługiwane jako `GenericChunk` – dane są zachowane bez dekodowania, więc plik można odtworzyć bez utraty informacji.

### Dekodowanie obrazu (IDAT)

Dane pikseli w chunkach IDAT są **skompresowane algorytmem zlib** i dodatkowo **filtrowane** wiersz po wierszu. Moduł `image_data.py` realizuje pełny pipeline:

1. Połączenie wszystkich chunków IDAT
2. Dekompresja zlib
3. Odwrócenie filtrów PNG (None, Sub, Up, Average, Paeth)
4. Obsługa interlace Adam7 (jeśli włączony w IHDR)
5. Obsługa głębi 1/2/4/8/16 bitów oraz palety kolorów

### Anonimizacja

`PNGAnonymizer` usuwa:

- wszystkie chunki **ancillary** (metadane: autor, gamma, czas modyfikacji, EXIF, …)
- **bajty za chunkiem IEND** (ukryte / doklejone dane)

Obraz (chunki IHDR, PLTE, IDAT, IEND) pozostaje bez zmian – plik nadal się otwiera i wygląda identycznie.

### Analiza FFT

`FFTAnalyzer`:

1. Pobiera piksele przez `get_raw_pixels()`
2. Konwertuje do skali szarości (wzorzec Rec.601 dla RGB)
3. Oblicza `np.fft.fft2()` i przesuwa zero do środka (`fftshift`)
4. Wyświetla logarytm modułu widma

Test poprawności (`fft --verify`) generuje obraz sinusoidalny o znanej częstotliwości i sprawdza, czy piki w widmie FFT pojawiają się we właściwych miejscach.

---

## Architektura pakietu `png_parser`

```
png_parser/
├── reader.py          PNGReader – czytnik bajtów z pozycją w pliku
├── signature.py       PNGSignature – walidacja sygnatury
├── chunk.py           Chunk, CriticalChunk, AncillaryChunk, GenericChunk
├── parser.py          PNGParser – główna pętla parsowania + offsety
├── png_file.py        PNGFile – kontener, piksele, zapis pliku
├── image_data.py      ImageData – filtry, Adam7, BitArray, encode/decode
├── anonymizer.py      PNGAnonymizer – czyszczenie metadanych
├── fft_analysis.py    FFTAnalyzer – widmo 2D
└── chunks/
    ├── __init__.py    chunk_factory() – rejestr typów chunków
    ├── critical/      IHDR, PLTE, IDAT, IEND
    └── ancillary/     tEXt, iTXt, zTXt, gAMA, pHYs, tIME, sRGB, cHRM, eXIf
```

---

## Użycie jako biblioteki Python

Możesz korzystać z parsera bez CLI:

```python
from png_parser import PNGParser, PNGAnonymizer, FFTAnalyzer

# Parsowanie
png = PNGParser().parse("pwr.png")

# Raport tekstowy
print(png.display_info())

# Atrybuty obrazu z IHDR
ihdr = png.get_ihdr()
print(ihdr.width, ihdr.height, ihdr.color_type_name)

# Lista chunków
for chunk in png.chunks:
    print(chunk.type_code, chunk.length, chunk.crc_valid)

# Offset chunka w pliku (hex)
start, end = png.get_chunk_offset(0)
print(f"IHDR: {start:08X}-{end:08X}")

# Piksele (zdekompresowane, odfiltrowane)
pixels = png.get_raw_pixels()
width, height, channels = png.get_pixel_layout()

# Anonimizacja
anonymizer = PNGAnonymizer()
stats = anonymizer.save_clean(png, "pwr_clean.png")
print(anonymizer.report(stats))

# FFT
analyzer = FFTAnalyzer(png)
spectrum = analyzer.compute_fft()       # macierz numpy
analyzer.plot_spectrum(save_path="spectrum.png")
```

### Hooki pod Projekt 2 (szyfrowanie RSA)

Wysokopoziomowe API:

```python
from idat_processor import BlockMode, DataVariant, encrypt_idat, decrypt_idat
from png_parser import PNGParser
from rsa import generate_keypair

key = generate_keypair(bits=2048)
png = PNGParser().parse("images/rgb.png")

enc = encrypt_idat(png, key, mode=BlockMode.ECB, variant=DataVariant.FILTERED)
enc.png.save("out/encrypted.png")

dec = decrypt_idat(enc.png, key, mode=BlockMode.ECB, variant=DataVariant.FILTERED)
dec.png.save("out/decrypted.png")
```

Niskopoziomowe hooki w `PNGFile`:

```python
# Skompresowany strumień IDAT (wariant B)
compressed = png.get_idat_compressed()

# Zdekompresowane bajty z filtrami (wariant A)
filtered = png.get_filtered_idat_bytes()

# Po modyfikacji – podmiana IDAT
new_png = png.replace_idat(ciphertext_or_plaintext_bytes)
new_png.save("modified.png")
```

Szczegóły teoretyczne: [RAPORT_P2.md](RAPORT_P2.md).

---

## Testy

Katalog `tests/` zawiera 50 testów jednostkowych:


| Plik                           | Zakres                                        |
| ------------------------------ | --------------------------------------------- |
| `test_signature.py`            | walidacja sygnatury PNG                       |
| `test_chunk.py`                | klasy chunków, flagi, CRC                     |
| `test_parser.py`               | parsowanie, offsety, błędy                    |
| `test_image_data.py`           | filtry, BitArray, paleta, Adam7               |
| `test_png_file.py`             | ekstrakcja pikseli, roundtrip                 |
| `test_anonymizer.py`           | usuwanie metadanych                           |
| `test_fft.py`                  | widmo FFT, test syntetyczny                   |
| `test_integration_project2.py` | round-trip RSA na images/rgb.png, palette.png |
| `test_integration.py`          | test na pliku `pwr.png`                       |


Fixtures w `conftest.py` generują minimalne pliki PNG w pamięci (RGB, paleta, interlace) – testy nie wymagają zewnętrznych plików poza opcjonalnym `pwr.png`.

---

## Ograniczenia

- **Re-kodowanie obrazów Adam7** – dekodowanie interlace działa, ale `replace_idat_from_image_data()` zapisuje plik jako non-interlaced.
- **Biblioteki PNG** – Pillow/PIL nie są używane do parsowania; NumPy i Matplotlib służą wyłącznie do FFT i wizualizacji.
- **Analiza teoretyczna** (wpływ kompresji na steganografię) – do uzupełnienia w raporcie akademickim.

---

## Powiązane pliki


| Plik               | Opis                              |
| ------------------ | --------------------------------- |
| `main.py`          | Punkt wejścia CLI                 |
| `requirements.txt` | Zależności Python                 |
| `pytest.ini`       | Konfiguracja testów               |
| `gemini-plan.md`   | Plan projektów 1 i 2 (wewnętrzny) |
| `RAPORT_P2.md`     | Materiał prezentacyjny Projekt 2  |
| `pwr.png`          | Przykładowy plik testowy          |


