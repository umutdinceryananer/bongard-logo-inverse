# Sunum yapısı, 20 Ekim 2026, Mohit ile görüşme

Depodaki notes/, outputs/figures/ ve outputs/logs/ taranarak çıkarıldı. Her slayt bir soru, bir karar, bir kanıt. Slayt metinleri İngilizce, konuşma notları Türkçe. Yalnızca depoda kaydı olan sayılar kullanıldı.

Kalıp. Önceki sunumla aynı. Başlık neden ya da nasıl sorusu. Slaytta karar, seçenekler, seçim, gerekçe, kanıt. Görsel varsa görsel. Küçük yazıdan kaçın, her blokta tek cümle.

## Sabah, slayta başlamadan önce Claude Code'dan alınacaklar

1. 150 görsellik kırpma karşılaştırmasının düzeltilmiş kuralla yeniden puanlanmış tablosu. Ön sonuç (jsonl'den okunan) şöyle, yön belli ama sayılar değişebilir.

| tür | n | stil 512 | stil kırpılmış | fark | sayı 512 | sayı kırpılmış | birebir 512 | birebir kırpılmış |
|---|---|---|---|---|---|---|---|---|
| ff tek | 30 | 62.0 | 67.6 | +5.6 | 49.0 | 59.1 | 6.7 | 10.0 |
| ff iki | 30 | 66.9 | 73.8 | +6.8 | 61.8 | 69.6 | 6.7 | 10.0 |
| bd | 60 | 63.3 | 65.9 | +2.6 | 7.8 | 10.5 | 0.0 | 0.0 |
| hd | 30 | 87.8 | 78.6 | -9.2 | 20.6 | 20.0 | 3.3 | 3.3 |
| hepsi | 150 | 68.7 | 70.4 | +1.7 | 29.4 | 33.9 | 3.3 | 4.7 |

   Okuma. Tam çözünürlükte kırpma 10 puan kuralını geçmiyor, hd'de düşürüyor. Karar, model tam çözünürlük alıyorsa görsel olduğu gibi, 224 alıyorsa kırpma. 2c kararı olduğu gibi kalıyor.
2. K1, K3 ve gemini-2.5-flash bittiyse özet tablo. Bitmediyse slayt 10'da "K2, 3.8 Flash" diye sınırla ve kalanını "devam ediyor" olarak söyle.
3. Ezber kontrolü (20 bozulmuş program) sonucu. Bitmediyse slayt 14'te açık soru.
4. zeroshot_examples.png son hali (3c sonrası yeniden üretilecekti).
5. findings.md'ye F10 (yay ters yön aynalama) ve F11 (zero-shot) eklendi mi.
6. Doğrulama. 2a kararındaki "her program 7 farklı pozla çizilmiş" cümlesi. Bir problemin 7 pozitifi aynı programı mı paylaşıyor? Claude Code'a taraf başına farklı program sayısını saydır. Doğrulanmadan slayta koyma, yerine "7 görsel per taraf" de.
7. Düşünme token'ı. decisions.md'ye göre "low" düzeyinde model çağrıların yarısında hâlâ düşünüyor (0 ile 2.000 token). Sözlü anlatımda "düşünme kapalı" deme, "en düşük düzey, yarısında hâlâ düşünüyor" de.

## Slaytlar

### 1. Başlık

How do we turn a Bongard-LOGO image back into its program, and why these choices?

Alt satır. Eight decisions, each with evidence. Depo adı ve tarih.

Konuşma. Geçen hafta tarih anlattım, bu hafta kararlar. Mohit'in listesi (which model, which images, how to train, sampling, hyperparameters, loss) bu sekiz kararın içinde.

### 2. Why this task?

- C-G replaces each image with the program that drew it. The programs come from the dataset.
- "in realistic settings such programs would need to be inferred from pixels via inverse graphics or symbolic detectors." (Vaishnav & Tammet, 2026, limitations)
- This week. Design the model that infers the program from the image, one decision at a time.
- Eight decisions. Task definition, images, model, size and training method, loss, sampling, hyperparameters, evaluation.

Konuşma. Bu adım çalışırsa C-G oracle olmaktan çıkar. Hedef bu hafta model değil, kanıtlı kararlar.

### 3. What does the data say?

- 12,000 problems, 168,000 images, every image paired with its program.
- A program says what to draw, not where. Position, rotation and scale are sampled at drawing time.
- Programs are short. At most 18 actions per image, 9 per shape.
- Two forms, five styles. line_style_length-turn, arc_style_radius_angle-turn.
- Every number comes from a finite set. Length 157 values, angle 45, turn 278. The arc radius is 0.500 in all 300,247 arcs.

Görsel. 03_numeric_values.png (dört panel). Sunumda yalnızca sağ üst (yarıçap, tek nokta) ve sağ alt (dönüş, ff 11 ve bd/hd 278) panellerini büyütmek yeterli.

Kanıt. data_layout.md, program_statistics.md bölüm 1 ve 3.

Konuşma. Bu dört olgu sekiz kararın yarısını belirliyor. Poz yok, bu yüzden poz tahmin edilmiyor ve kırpma bilgi kaybetmiyor. Sayılar ayrık, bu yüzden loss ve değerlendirme buna göre.

### 4. Why keep the dataset strings as the output?

Karar 1a.

- Options. (a) raw dataset strings, (b) the same with the arc radius removed, (c) English step-by-step descriptions.
- Choice. (b). line_style_length-turn, arc_style_angle-turn.
- Lossless. The radius is 0.500 in every arc, so it is recovered by inserting it back. C-G receives the original format.
- Every other field varies in bd and hd, so nothing else can be dropped.
- (c) is 3 to 5 times longer and needs a parser before scoring or drawing.

Kanıt. Alan başına farklı değer tablosu (program_statistics.md bölüm 3). Slayta küçük tablo. tür 2, stil 5, uzunluk 157, yarıçap 1, açı 45, dönüş 278.

Konuşma. Mohit "neden ham dizge" derse, cevap şu. Kayıpsız tek sadeleştirme yarıçap, gerisi veri setinin kendi dili. Çıktı C-G'ye olduğu gibi gider.

### 5. How are two-shape images written?

Karar 1b ve 1c.

- Half of ff and 84% of bd images have two shapes. hd has none.
- The shape boundary stays. It is a drawing instruction (lift the pen). Without it the same actions draw one connected shape.
- The order is fixed. Fewer actions first, ties alphabetical.
- Why fixed. The dataset order is arbitrary. The same pair recurs in both orders in 24% (ff) and 26% (bd) of recurring pairs. The renderer does not use the order.
- The C-G paper's 20-point "sequence permutation" drop concerns stroke order inside a shape. That stays untouched.
- The two shapes touch or overlap in 3.9% of two-shape images.

Görsel. 1b_shape_boundary.png (sınır korunmuş ve atılmış, iki satır).

Kanıt. decisions.md 1b, 1c. check_1c_shape_order.py, check_1b_shape_overlap.py.

Konuşma. Açık soru olarak söyle. C-G şekil bloklarının sırasına duyarlı mı, test edilmedi. 3. düzey değerlendirmede ground-truth programlarla iki sırada çalıştırıp bakılacak.

### 6. Which images, which types?

Karar 2a ve 2b.

- Training images. The dataset's own 168,000 images. No augmentation.
- Why no augmentation. Mirroring flips every turn, so the program no longer matches the image. Rotation is already random in the data.
- Own drawings are a fallback. The published renderer reproduces bd and hd images but not ff (stamp density and proportions differ).
- Pipeline trial on ff. 100 distinct action strings, length and angle constant.
- Target model. One model over all three types, because C-G tests all three and the three share one language.

Görsel. İsteğe bağlı, 02_render_pair.png satır 2 (ff, aynı şekiller farklı poz, damga yoğunluğu farklı). Slayt dolu geliyorsa görselsiz.

Kanıt. decisions.md 2a, 2b. data_layout.md "Pose is not stored" ve renderer karşılaştırması.

Konuşma. Nie ve Raghuraman da veri setinin kendi görselleriyle eğitmiş. F3 (renderer ff'yi birebir üretemiyor) bulunan şeylerden biri, kısa söyle. "Trial shows the pipeline works, not that the model works on bd and hd."

### 7. What resolution does the model need?

Karar 2c.

- Shapes are small. Ink box median ff 170, bd 280, hd 137 px in a 512 px image.
- At a 224 px input the smallest hd shapes shrink to about 30 px and the stamps become blobs. Cropped to the ink with a 10% margin they stay legible.
- Cropping loses nothing. The program has no position and no size.
- Test at full resolution (Gemini, 150 images). Cropping adds 1.7 points on style, hd drops 9. Below the 10-point rule.
- Decision. Full-resolution input, image as it is. 224 px input, crop to the ink. Same at test time.

Görsel. 2c_resolution.png. Sunumun en güçlü görseli, tam sayfa.

Kanıt. fig_2c_resolution.py, decisions.md 2c, kırpma koşusu 150 görsel (sabah yeniden puanlanmış tablo).

Konuşma. Figürdeki örnekler en küçük yüzde 10'dan, yani en kötü durum, bunu kendin söyle. İnce stiller ff'nin yüzde 80'inde, bu yüzden ayrıntı değil.

### 8. How is a predicted program scored?

Karar 8b.

- Three levels. Program (string), render (draw both at the same pose), task (C-G with predicted programs).
- Program level. Valid output, shape count, action count within 1, type, style and numbers per action, exact match, edit distance.
- One shape has many correct programs. A closed shape can start anywhere. Scoring tries every start point and keeps the best alignment.
- What I found while testing the scorer. Reversing the direction is valid only for shapes made of lines. Reversing an arc draws its mirror image. Verified on 300 shapes, fixed, changed 10 of 58 scores.

Görsel. zeroshot_examples.png ilk satır (ff best, style 100%, edit distance 0, exact False). Modelin programı doğru parçaları içeriyor ama çizim döndürülmüş. Döndürme sayısal olarak doğrulandı.

Kanıt. decisions.md 8b, 04_zeroshot.py score().

Konuşma. Bu slayt Mohit'in "gizli noktalar" dediği şeylerden ikisini taşıyor. Birden çok doğru program, ve yayların ters çevrilemeyeceği. "I tested my scoring and found a bug" cümlesi iyi bir cümle.

### 9. Can an untrained VLM read the drawing? The test

Karar 3b.

- Why. Decides the model family (3a). And extends the paper one step. Gemini is at chance on the Bongard task from pixels. Can it at least write the program for one image?
- 150 val images, each from a different problem. ff 30 one-shape, 30 two-shape, bd 60, hd 30. Test splits untouched.
- Prompt. Grammar plus three examples. K1 text only, K2 image-program pairs of the same type, K3 pairs of another type (copying or reading?).
- Models. gemini-3.8-flash (current) and gemini-2.5-flash (the paper's pixel baseline).
- Settings. Seed 0, thinking at the lowest level, 512 px, one answer per image.
- Decision rule fixed before the run. "Cannot read" only if style accuracy stays within 10 points of the majority baseline in every type and action count is wrong in half.

Kanıt. zeroshot_prompt.txt, zeroshot_sample.json, decisions.md 3b ve 8b.

Konuşma. "Amerika'yı yeniden keşif mi" sorusu gelirse. Mohit'in testi Bongard problemini çözmekti (algı artı akıl yürütme). Bu test yalnızca algı. Sonuç ne çıkarsa çıksın makaleye yeni bilgi.

### 10. Can an untrained VLM read the drawing? The result

- Table. K2, gemini-3.8-flash, 150 images, 512 px.

| type | n | valid | action count within 1 | style (best alignment) | majority baseline | numbers | exact |
|---|---|---|---|---|---|---|---|
| ff one shape | 30 | 100 | 90 | 62 | 21 | 49 | 7 |
| ff two shapes | 30 | 100 | 97 | 67 | 21 | 62 | 7 |
| bd | 60 | 100 | 67 | 63 | 68 | 8 | 0 |
| hd | 30 | 100 | 97 | 88 | 65 | 21 | 3 |
| all | 150 | 100 | 83 | 69 | | 29 | 3 |

- Reading. It reads what is drawn, not how much. Format, stroke count and most styles are right. Lengths and angles are not.
- ff numbers are inflated. Length and angle are constants in ff, so the model writes them without reading.
- bd does not beat its baseline. Two-shape images only, longest programs, widest vocabulary.
- Pending. K1, K3, gemini-2.5-flash, memorization check on 20 perturbed programs.

Görsel. zeroshot_examples.png (altı satır, her türden en iyi ve ortanca). Tablo ile aynı slayta sığmazsa bir sonraki slayt.

Kanıt. zeroshot_gemini-3.8-flash_K2.jsonl, zeroshot_summary.csv (sabah güncel hali).

Konuşma. "Mohit's paper says the bottleneck is in representation. Here the VLM gets the representation half right. It sees the structure but not the measurements." Bunu soru olarak sor, iddia olarak değil.

### 11. Which model family?

Karar 3a.

- Options. (a) Fine-tune a small VLM, about 2B parameters, LoRA, 4-bit, Colab T4. (b) Train a small vision encoder and program decoder from scratch, program vocabulary as output vocabulary.
- For (b). Short programs, 3,101 distinct strings, 150,000 clean black-and-white images. Nie's team built a small CNN program synthesizer in 2020.
- For (a). Pretrained vision already reads these drawings. The zero-shot test shows it. What is missing is the measurement, which fine-tuning targets directly.
- Rule. (b) only if the VLM could not read the drawings. It can. Choice (a).
- Hardware sets the size. No local GPU, free Colab T4. 2B model, 4-bit, LoRA.
- (b) stays as the fallback if fine-tuning does not learn the numbers.

Kanıt. Slayt 10 tablosu, decisions.md 3a, donanım kararı.

Konuşma. Seçim senin, kural (a) diyor. İki yolu da anlat, Mohit "neden sıfırdan değil" diye soracak. Cevap, VLM'in okuyamadığı varsayımı düştü. "Neden Qwen değil Gemini" sorusu gelirse, Gemini test için (API), eğitim için açık model gerekiyor, aday listesi sonraki hafta.

### 12. How to train? Loss, sampling, hyperparameters

Karar 4, 5, 6, 7. Dürüst başlık. Open, with the evidence collected so far.

- Size and method (4). 2B VLM, LoRA, 4-bit. Fixed by the hardware, not by preference.
- Loss (5). Token cross-entropy over the program string is the default. The numbers are discrete (157, 45, 278 values), so they can be treated as classes rather than free text. A render-based reward is a later option.
- Sampling (6). Training balance to decide. bd is 55% plain lines, ff is 80% fine styles, type sizes 38k, 45k, 47k. Inference, one answer or several candidates drawn and compared (Ellis et al., 2018).
- Hyperparameters (7). After the model is chosen. Output budget is small, at most 18 actions and 465 characters.
- These are decided with the first training run, next week.

Kanıt. program_statistics.md bölüm 2 ve 3, donanım notu.

Konuşma. Mohit'in listesindeki "sampling, hyperparameters, loss, how to train" bu slayt. Her birine bir cümle ve bir kanıt var, karar yok. Bunu açıkça söyle, Mohit bir haftada bunların verilemeyeceğini zaten söyledi.

### 13. How is the model evaluated?

Karar 8.

- Official splits. train 9,300, val 900, test_ff 600, test_bd 480, test_hd_comb 400, test_hd_novel 320 problems.
- test_ff is a length-extrapolation test. Train and val have 4 to 8 actions per image, every test_ff image has 9.
- A bd evaluation measures two-shape images only. All 627 one-shape bd problems are in train, by design of Nie's BA test set.
- 56 to 69% of shape programs in val, test_bd and test_hd also occur in train. test_ff 11%.
- Report per type and per split. One average would hide the ff and bd difference.
- Level 3. Replace the oracle programs in C-G with predicted ones and measure how much of 61 to 78% survives.

Görsel. 03_ff_length_gap.png.

Kanıt. data_layout.md "Splits" ve "Shape programs shared with train", program_statistics.md bölüm 4.

Konuşma. n ve n+1 meselesi burada gerçek bir sayıya dönüştü. 8'e karşı 9. İki şekilli BD bulgusunu "Nie'nin tasarımının sonucu" diye çerçevele, "veri setinde tuhaflık" diye değil.

### 14. What was not obvious, what is open, what is next

- Found in the data. One shape has many correct programs. Reversing an arc mirrors it. The arc radius is constant. test_ff is one action longer than anything in training. bd tests two-shape images only. The published renderer does not reproduce ff images. An untrained VLM reads the structure but not the measurements.
- Open. Is C-G sensitive to the order of the two shape blocks? Does a higher thinking level change the zero-shot result? Is gemini-2.5-flash still reachable? Memorization check result.
- Next week. Candidate open VLMs that fit a T4, first fine-tuning run on ff, level 2 evaluation, then bd and hd.
- Questions. HPC access at TalTech. Does "reads the structure, not the measurement" fit the paper's bottleneck claim? Did you look at shape-block order in the C-G experiments?

Konuşma. İlk madde Mohit'in "hidden things" sorusuna cevabın. Hepsini veriye bakarak bulduğunu söyle, listeden okuduğunu değil.

## Öncelik

Vakit daralırsa slayt 2'yi 1'e, slayt 9'u 10'a katla. 12 slayta iner. Slayt 7, 8, 10 ve 11 sunumun çekirdeği, bunlar kısalmaz.

## Prova için iki cümle kontrolü

Her slaytta Mohit "nasıl çalışıyor" diye sorabilir. Şunları iki cümleyle anlatabilmen gerekiyor.

- Loss. Model her token için bir olasılık dağılımı üretir, doğru token'ın olasılığı düşükse ceza alır. Cross-entropy bu cezanın adı.
- LoRA. Modelin ağırlıklarına küçük bir ek katman eklenir, yalnızca o eğitilir. Bellek ve süre küçülür.
- 4-bit. Ağırlıklar daha az bitle saklanır, model T4'e sığar, küçük bir hassasiyet kaybı olur.
- Best alignment. Kapalı bir şekil her noktadan başlayarak yazılabilir, puanlama bütün başlangıçları dener ve en iyisini alır.
- Üç düzey. Program metni, çizim, C-G görevi.
