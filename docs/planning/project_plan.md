# KiCad to Blender Pro Add-on: Proje Yol Haritası ve Görevler

Bu proje, KiCad üzerinden dışa aktarılan 3B devre kartı modellerini (.wrl / VRML) Blender'a (özellikle Blender 5.2 LTS) tek tıkla aktaran, sahnedeki binlerce dağınık objeyi optimize eden, gerçekçi PBR (Fiziksel Tabanlı) materyaller atayan ve profesyonel stüdyo renderına hazır hale getiren bir Blender Eklentisidir (Add-on).

Referans Kart: /home/a/Belgeler/kiCad work/Deneme/Deneme.wrl

---

## Aşama 1: Ortam ve Gereksinim Analizi (Tamamlandı)
- [x] 1.1. Blender 5.2 LTS ve Flatpak ortamındaki VRML/X3D modülü ('bl_ext.blender_org.web3d_x3d_vrml2_format') incelendi ve doğrulandı.
- [x] 1.2. Deneme.wrl dosyasının anatomisi çıkarıldı:
  - 108 adet inline 3B bileşen referansı (Direnç, kondansatör, IC, soket, USB-C vb.)
  - 10 ana PCB katmanı (Substrate, Lehim Maskesi, Bakır/Altın Padler, Kalay, Serigrafi vb.)
  - Ham import sonrası ortaya çıkan 6.053 adet parça ve 56 kopya materyal tespit edildi.
- [x] 1.3. Proje takip dosyaları ('project_pipeline.json' ve 'project_plan.me') oluşturuldu.

## Aşama 2: Akıllı VRML/WRL İçe Aktarma Motoru (Smart Importer)
- [x] 2.1. Blender dahili VRML eklentisinin otomatik kontrolü ve eksikse arka planda etkinleştirilmesi.
- [x] 2.2. Göreceli/mutlak dosya yolu çözücü (Inline VRML bileşenlerinin eksiksiz yüklenmesi).
- [x] 2.3. Kartın geometrik merkezinin hesaplanması (Origin to Center of Mass) ve sahne merkezine (0,0,0) taşınması.
- [x] 2.4. KiCad ölçek faktörünün (2.54 / 0.001) Blender metrik sistemine otomatik dönüştürülmesi ve rotasyon düzeltmesi (Z-up hizalama).

## Aşama 3: Obje Hiyerarşisi, Temizleme ve Performans Optimizasyonu
- [x] 3.1. 6.000'den fazla objenin taranıp mantıksal Koleksiyonlara (Collections) ayrılması:
  - [PCB] Substrate (FR4 gövde)
  - [PCB] SolderMask (Üst ve alt lehim maskesi)
  - [PCB] Copper & Pads (Bakır hatlar, lehim padleri, test noktaları, vialar)
  - [PCB] Silkscreen (Baskı yazıları ve semboller)
  - [PCB] Components (Tüm SMD ve THT elektronik bileşenler)
- [x] 3.2. Kopya materyallerin ('SHAPE_1.001', 'SHAPE_15.001' vb.) tekilleştirilmesi (Deduplication).
- [x] 3.3. **Ultra Performans Modu**: Aynı materyal ve katmana ait binlerce küçük parçanın tek bir mesh altında birleştirilmesi (Batch Join) -> Sahne 6000 nesneden ~15 nesneye düşerek 60 FPS viewport performansı sağlar.
- [x] 3.4. **Bileşen Hiyerarşisi Modu**: Her elektronik bileşenin (örneğin U1, J1, C1) parçalarını kendi Empty objesi altına toplayarak tek tek seçilebilir ve gizlenebilir hale getirilmesi.

## Aşama 4: Gerçekçi Fiziksel (PBR) Materyal Motoru
- [x] 4.1. **FR4 Substrate Materyali**: Yarı pürüzlü cam elyafı epoksi dokusu, iç ışık geçirgenliği (Subsurface Scattering).
- [x] 4.2. **Lehim Maskesi (Solder Mask) Materyali**:
  - Yarı saydam parlak/saten katman, alttaki bakır yolları belirginleştiren derinlik.
  - Canlı renk presetleri:
    * Klasik KiCad Yeşili
    * Mat / Parlak Siyah
    * OSH Park Moru
    * Kraliyet Mavisi
    * Ateş Kırmızısı
    * Parlak Beyaz
- [x] 4.3. **Pad ve Lehim Yüzeyleri**:
  - ENIG (Electroless Nickel Immersion Gold): Altın kaplama yansıma (Metalik 1.0, Roughness 0.2, Altın sarısı).
  - HASL / Kalay Lehim: Parlak gümüş lehim rengi ve pürüzsüz menisküs yansıması.
- [x] 4.4. **Serigrafi (Silkscreen)**:
  - Mat beyaz mürekkep baskısı, UV kurutmalı hafif kabartma (Bump/Normal haritası).
- [x] 4.5. **Elektronik Bileşen Materyalleri**:
  - IC Çipleri: Mat siyah epoksi kompozit gövde ve lazer kazıma dokusu.
  - SMD Bacaklar / Pinler: Parlak nikel ve kalay metalik yansıma.
  - Kondansatörler: Seramik sarımsı kahverengi gövdeler ve alüminyum elektrolitik kılıflar.

## Aşama 5: Stüdyo Işıklandırması ve Kamera Kurulumu (Ready-to-Render)
- [x] 5.1. Kartın en-boy oranına göre otomatik konumlanan yumuşak 3 noktalı stüdyo ışık seti (Key Light, Fill Light, Rim Light).
- [x] 5.2. World ortamı için gerçekçi nötr aydınlatma.
- [x] 5.3. Kartı mükemmel kadrajlayan ortografik ve perspektif kamera kurulumu.
- [x] 5.4. Sunumlar için tek tıkla 360 derece döner tabla (Turntable Animation) ekleme.

## Aşama 6: Blender Arayüzü (N-Panel UI) ve Eklenti Paketleme
- [x] 6.1. 3D Viewport sağ panelinde (N-Panel) 'KiCad PCB' sekmesi oluşturulması.
- [x] 6.2. Tek Tıkla 'Kartı İçe Aktar ve Hazırla' (One-Click Import & Ready) butonu.
- [x] 6.3. Anında Renk Değiştirici (Canlı lehim maskesi renk paleti seçimi).
- [x] 6.4. Blender 5.2 uyumlu 'blender_manifest.toml' ve '__init__.py' ile ZIP formatında kurulabilir Add-on paketi oluşturulması.


## Faz 7: Fiziksel Boyut, Z-Fighting Sıfırlama ve Eleman Bilgileri
- [x] **Gerçek Hayat Ölçü Doğrulaması**: KiCad Edge.Cuts (151.0 x 95.0 mm, 1.6 mm kalınlık) ile Blender boyutları birebir eşitlendi.
- [x] **Metrik Milimetre Sistemi**: Sahne birimlerini bozmadan izole metrik ölçekleme uygulandı.
- [x] **Z-Fighting Çözümü**: Gerçek PCB üretim katmanları gibi Substrate (0), Copper/Gold (+0.035 mm), Solder (+0.045 mm), Mask (+0.055 mm), Silkscreen (+0.080 mm) Z-yükseklikleri uygulandı.
- [x] **KiCad PCB Metaveri Okuyucu**: 143 footprint'in (C16, R8, U1 vb.) değerleri, adları ve konumları otomatik ayrıştırıldı.
- [x] **Arayüz (N-Panel) Güncellemesi**: İçe aktarılan kartın gerçek milimetre boyutlarını gösteren bilgi kutucuğu eklendi.

## Faz 8: Eksik Komponent Tamamlama & footprints.blend Kütüphane Sistemi
- [x] **footprints.blend Kütüphanesi**: 18 temel IPC paketi (R_0402..1206, C_0402..1206, SOT-23, SOT-23-6, SOT-223, TO-252, SOIC-8, TSSOP-8, SOIC-16, QFN-32, IND_5050, POT_PTV09A).
- [x] **Token/Regex Eşleme Motoru**: `footprint_matcher.py` ile üretici kılıf isimlerinden paket tipi çıkarımı (%95+ doğruluk).
- [x] **Pin 1 & Serigrafi Uyumu**: U1 ve diğer IC'ler için KiCad (+Y aşağı) ve Blender (+Y yukarı) simetrisine göre Pin 1 noktası ve silkscreen ok eşleşmesi.
- [x] **Özel Parça Desteği**: Q1 (TSSOP-8), U3 (SOT-23-6), L1/L2 (IND_5050), R32/R33/R42 (POT_PTV09A); TP padlerinin çıplak bakır olarak korunması.
- [x] **Material Harmony Engine**: Yeni eklenen elemanların mevcut IC'lerle (U5_RP2040) aynı siyah epoksi ve kalay parıltısını paylaşması, tek tıkla senkronizasyon.
- [x] **N-Panel Entegrasyonu**: Eksik tarama, otomatik doldurma, açılır menüden manuel atama ve materyal uyumlandırma butonları.

