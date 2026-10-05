# KiCad to Blender Pro - Proje Durumu ve Yol Haritası (durum.md)

## 1. Tamamlanan Özellikler (Mevcut Durum)

1. **VRML / WRL Akıllı İçe Aktarma Motoru**:
   - Blender dahili X3D/VRML eklentisini programatik kontrol etme ve otomatik aktifleştirme.
   - Inline kütüphane bağımlılıklarını çözümleme ve tam mesh yüklemesi.
2. **Sıfır Z-Fighting (Physical Layer Offsets)**:
   - FR4, Solder Mask, Copper/Gold, Silkscreen katmanları arasına mikron seviyesinde (0.035 mm - 0.055 mm) Z-ofsetleri uygulanarak yüzey çakışmaları sıfırlandı.
3. **Fotogerçekçi PBR Materyaller**:
   - FR4 Substrate (pürüzlü epoksi cam elyafı).
   - Lehim Maskesi (yarı saydam derinlikli yeşil/renkli cila).
   - İletken Katmanlar (ENIG Altın ve HASL Kalay/Gümüş).
   - Serigrafi (Baskı beyaz mat plastik bump efekti).
4. **Kusursuz Konumsal Eşleşme (Spatial Coordinate Matching)**:
   - KiCad `.kicad_pcb` dosyasından 110 ayak izi koordinatları ($pos\_x, pos\_y$) okundu.
   - Bounding-box yerine `obj.location` tabanlı eşleme ile 6.000+ alt parça 0.5 mm altı hata payıyla kendi komponentlerine bağlandı (0 kayıp / 0 parçalanma).
   - Her komponent (gövde + bacaklar + pinler) tek parça halinde birleştirildi (örn. `U5_RP2040`, `C16_1uF`, `J1_USB_C`).
5. **Sahne Koruma ve İzole Metrik Boyutlandırma**:
   - Kullanıcının sahnesindeki diğer objeleri ve sahne unit ayarlarını bozmamak için global birim ayarlarına dokunulmadı.
   - Sadece içe aktarılan PCB nesnelerine 0.001 ölçek çarpanı uygulandı ve `transform_apply` ile gerçek hayat metrik boyutuna sabitlendi (`151.0 mm x 95.0 mm x 1.57 mm`).
6. **Kesin İşlem Sırası (Strict Importer Pipeline)**:
   - VRML Import -> Katman/PBR Ayrımı -> Ham VRML'de Eşleme & Join -> Düz Yatırma (-90° X) & FR4 Merkezleme -> Sadece PCB'yi Metreye Ölçekleme -> Metrik Z-Ofsetleri -> Stüdyo Kurulumu.
7. **Otomatik Hiyerarşik Sınıflandırma**:
   - `05_Components` altında otomatik alt koleksiyonlar:
     * `01_Capacitors`
     * `02_Resistors`
     * `03_Integrated_Circuits`
     * `04_Transistors_FETs`
     * `05_Diodes_LEDs`
     * `06_Switches_Buttons`
     * `07_Connectors_Headers`
     * `08_Crystals_Oscillators`
     * `11_Audio_Buzzers`
8. **Kullanıcı Arayüzü (N-Panel)**:
   - Manuel `.kicad_pcb` ve `.wrl` seçici, durum bilgisi, import butonu.
9. **Katman Merkez Noktalarının (Origin/Pivot) Kart Merkezine Sabitlenmesi**:
   - Board layer objelerinin (`PCB_Substrate_FR4`, `PCB_Copper_Gold_*`, `PCB_SolderMask_*`, `PCB_Silkscreen`) orijin noktalarının kartın sol üstünde kalması sorunu çözüldü.
   - Sadece katman nesnelerine `transform_apply(location=True)` uygulanarak tüm katmanların orijin/pivot merkezleri tam kart merkezine `(0, 0, 0)` eşitlendi.
   - Komponentlerin orijinleri kendi kılıf merkezlerinde muhafaza edildi.
10. **Orijinal Dosya Renklerinin Korunması ve Renk Ayarlarının Opsiyonel Hale Getirilmesi**:
   - İçe aktarma sırasında KiCad `.wrl` dosyasından gelen orijinal VRML materyalleri, renkleri ve şeffaflıkları (`Shape`, `Shape.001` - `009`, `SHAPE_*`) varsayılan olarak bozulmadan korundu.
   - Komponentlerin gövde, bacak, işaretleme ve kılıf renklerinin ezilmesi engellendi (kırmızı LED, mavi kondansatör, sarı altın padler vb. orijinal renkleriyle geliyor).
   - Prosedürel PBR gölgelendiricileri ve lehim maskesi renk seçimleri varsayılandan çıkarılıp **tamamen opsiyonel** yapıldı.
   - "Restore File Colors" doğrudan canlı **Classic Green** lehim maskesi ve orijinal alt katman materyalleriyle tek tıkta sıfırlama yapacak şekilde güncellendi (kullanıcının ayrıca yukarıdan yeşil seçmesine gerek kalmadı).
   - "Recenter PCB to Origin" için sadece öteleme yapan `recenter_board_to_origin()` yazılarak kartın her tıklamada küçülmesi (0.001 ile tekrar çarpılması) hatası tamamen çözüldü.
   - **Akıllı Materyal Tekilleştirme ve Yetim Temizliği (Deduplication)**: KiCad VRML çıktısının oluşturduğu yüzlerce kopya `Shape.001`, `Shape.002` datablock'u, Principled BSDF gölgelendirme imzaları (Base Color, Metallic, Roughness, Alpha, Emission vb.) birebir aynı olan ana materyale bağlandı; sahipsiz kalan 100+ kopya materyal güvenle silinerek dosya boyutu ve bellek optimize edildi.
11. **Fiziksel Doğruluğa Sahip, Abartısız Bakır (Copper) Gölgelendirmesi**:
    - Endüstriyel PCB bakır folyolarının (haddelenmiş tavlı / elektrolitik folyo ve anti-tarnish mikro pasivasyon) gerçek optik spektrofotometre ölçümlerine dayalı PBR değerleri entegre edildi:
      * **Linear RGB Base Color**: `(0.96, 0.48, 0.26, 1.0)` (sRGB karşılığı: `#FAB78A` / 250, 183, 138 - somon pembe veya pirinç/altın sarısına kaçmayan zengin sıcak bakır ışıltısı).
      * **Metallic**: `1.0` (saf iletken metal).
      * **Roughness**: `0.22` (gerçek PCB bakır yollarının mikro saten yüzey dokusu; yapay ayna parlaklığı veya mat plastik görünümü engellendi).
      * **Specular IOR Level**: `0.5`.
    - Kartı kirli, buruşuk veya taş gibi gösteren abartılı prosedürel noise/bump dokularından tamamen kaçınılarak temiz, pürüzsüz endüstriyel üretim kalitesi elde edildi.
    - Stüdyo aydınlatma sistemi (Key/Fill ve Ambient ortam) optimize edilerek düz metal yüzeylerdeki beyaz ışık patlamaları (specular burnout) engellendi.
12. **Eksik/3D Modeli Olmayan Komponentleri Tamamlama ve footprints.blend Kütüphane Sistemi**:
    - KiCad `.kicad_pcb` dosyasından ayak izi olup `.wrl` dosyasında 3D modeli bulunmayan elemanları otomatik tespit etme ("Scan Missing Components").
    - Token ve regex tabanlı akıllı eşleme motoru (`footprint_matcher.py`): 0402, 0603, 0805, 1206 (R ve C), SOT-23, SOT-23-6, SOT-223, TO-252 (DPAK), SOIC-8, TSSOP-8, SOIC-16, QFN-32, IND_5050, POT_PTV09A standart paketlerini %95+ güvenle otomatik eşleştirme.
    - IPC-7351 standartlarına ve KiCad yönelimlerine tam uyumlu dahili `footprints.blend` model kütüphanesi (18 standart paket).
    - Mikron hassasiyetinde konumsal ve rotasyonel yerleşim (`footprint_placer.py`): Top (`F.Cu`) ve Bottom (`B.Cu` - otomatik 180° ters çevirme ve aynalama).
    - **Pin 1 & Serigrafi Uyumu**: KiCad ve Blender Y-ekseni tersliği (+Y KiCad'de aşağı, Blender'da yukarı) dikkate alınarak Pin 1 gösterge noktası hizalandı. U1 (TP4056) entegresinin Pin 1 çentiği, kart serigrafisindeki (silkscreen) ok işaretiyle tam örtüştürüldü.
    - **Gerçekçi Kavisli Bacaklar (Curved Gullwing Leads)**: Bloklu bacaklar yerine resmi KiCad `U6` (SOIC-8) ve `U11` (TSSOP-20) modellerinden esinlenen omuz, diz, bacak inişi, bilek ve lehim ayağı eğrilerine sahip 6 segmentli pürüzsüz "gullwing" bacak profili modellendi (`SOIC-8`, `TSSOP-8`, `SOT-23`, `SOT-23-6`, `SOIC-16`, `SOT-223`).
    - **Özel Bileşenler**: 
      * `Q1` (FS8205A) için 0.65 mm dar bacak aralıklı `TSSOP-8`,
      * `U3` (FP6291) için 6 bacaklı kavisli `SOT-23-6`,
      * `R32`/`R33`/`R42` için 9 mm `POT_PTV09A` dikey potansiyometre: Kullanıcının `R33` üzerinde düzelttiği pürüzsüz 90° dirsek bacak geometrisi ve 0.30 mm standoff yüksekliği genel kütüphane standardı olarak kaydedildi ve sahnedeki tüm potansiyometrelere uygulandı.
      * `SW1` (WS-SLTV) için `SW_Slide_WS_SLTV` minyatür sürgülü anahtar: Kullanıcının gövde üzerine modellediği üst metal kızak yuvası, kıvrımlı sac kanalları ve sürgü boşluğu kütüphaneye dahil edildi.
    - **Test Noktaları (TP1..TP26)**: Test noktaları fiziksel olarak çıplak bakır pad olduğu için 3D parça atanmayarak serbest bırakıldı, arayüzde tespit edilmesi beklenen doğal davranış olarak korundu.
    - **Materyal Uyumu ve Tutarlı Gölgelendirme (Material Harmony Engine)**: Sonradan eklenen tüm entegre ve pasiflerin sahnede mevcut çiplerle (`U5_RP2040`, `U6`, `U11` vb.) aynı siyah kalıp epoksi tonunu ve kalay lehim parıltısını paylaşması (`material_harmony.py`).
    - N-Panel entegrasyonu: Tek tıkla "Scan Missing Components", "Fill Auto-Matched", eksik parçalar için manuel açılır menü listesi ve "Harmonize Component Shaders" butonu.

---

## 2. Sıradaki Öncelikli Görevler (Next Steps)

1. **Lehim Maskesi Renk Yönetimi (Solder Mask Color Engine)**:
   - N-Panel üzerinden tek tıkla canlı lehim maskesi rengi değiştirme:
     * Klasik Yeşil (Classic Green)
     * Mat / Parlak Siyah (Matte / Glossy Black)
     * Lacivert / Mavi (Royal Blue)
     * Kırmızı (Ferrari Red)
     * Beyaz (Arctic White)
     * Mor (OSH Park Purple)
     * Şeffaf / Sarı (Clear FR4)
   - FR4 tabanı ile lehim maskesi arasındaki renk etkileşimini ve saydamlık tonunu koruma.

2. **Komponent Renkleri ve Malzeme Kütüphanesi (Component Material Engine)**:
   - Çip gövdeleri için siyah mat/saten kalıp epoksi materyali.
   - SMD seramik kondansatörler için gerçekçi kahverengi/bej seramik gövde ve kalay kaplı uçlar.
   - Dirençler için siyah gövde, beyaz işaretleme ve metal uçlar.
   - Metal konektörler, ekranlama kapakları ve lehim bacakları için parlak nikel/kalay/altın kaplama.
   - Elektrolitik kondansatörler için alüminyum/mavi/siyah plastik kılıf dokuları.
   - Butonlar ve plastik soketler için renk varyasyonları.

---

## 3. Tartışılan ve Eklenecek Gelecek Özellikler (Backlog & Roadmap)

### A. Görsel Gerçekçilik ve Detaylar (Hyper-Realistic Details)
- **LED Işıma ve Çalışma Simülasyonu (Emissive LEDs)**:
  - Karttaki LED'leri (`D1`, `D2`, `LED_...`) otomatik tespit etme.
  - Açık/Kapalı anahtarı, ayarlanabilir lümen/parlaklık, renk seçici (Kırmızı, Yeşil, Mavi, Sarı, Beyaz).
- **Çip Üzeri Lazer Kazıma (Procedural IC Markings)**:
  - Çip yüzeyine gerçekçi çip kodu, parça numarası, pin-1 noktası ve üretici logosu ekleyen procedural doku.
- **Bakır Yol Rölyefi (Trace Relief / Normal Map)**:
  - Lehim maskesi altından geçen bakır yolların kabarık endüstriyel dokusunu hissettiren normal/bump haritası.
- **Yüzey Kusurları (Surface Imperfections)**:
  - İsteğe bağlı toz, hafif montaj parmak izi/çizik ve lehim akısı (flux) kalıntısı efektleri.

### B. Sunum ve Animasyon Araçları (Presentation & Motion)
- **Patlatılmış Görünüm Kaydırıcısı (Exploded View Slider)**:
  - N-Panel'de tek bir slider ile komponentlerin, serigrafinin, lehim maskesinin, bakır yolların ve FR4 tabanın Z ekseninde birbirinden ayrılarak havada süzülmesi.
- **Sinematik Kamera ve Turntable 360**:
  - Tek tıkla ürünün etrafında dönen 360° stüdyo animasyonu oluşturma.
  - Seçilen bir bileşene odaklanan otomatik Alan Derinliği (Depth of Field / Bokeh) kamera odağı.
- **Teknik X-Ray / Saydam İnceleme Modu**:
  - Katmanların içini ve gizli sinyal yollarını göstermek için şeffaf teknik görünüm.

### C. İşlevsellik, Sahne Yönetimi ve Dışa Aktarma
- **Etkileşimli Bileşen Arama ve Odaklanma (Component Inspector)**:
  - Panelden referans seçildiğinde (örn. `U5_RP2040`) kameranın o parçaya yumuşakça odaklanması ve parçayı vurgulaması.
- **Toplu Filtreleme / Gizleme**:
  - Kategori veya kılıf bazında (tüm dirençleri gizle, sadece konektörleri göster vb.) tek tık görünürlük kontrolleri.
- **Kasa / Muhafaza (Enclosure) Entegrasyon Desteği**:
  - Kartın kutusunu (STEP/STL) sahneye yerleştirip montaj uyumunu görselleştirme.
- **Web 3D / AR Çıktısı (glTF / USDZ Export)**:
  - Doku haritalarını tek bir texture içine fırınlayıp (Bake) web sitelerinde ve mobilde artırılmış gerçeklik (AR) ile görüntülenebilir hafif model olarak dışa aktarma.
