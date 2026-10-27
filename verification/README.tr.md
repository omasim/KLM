# Nage tasdik kaydını bağımsız doğrulama

Bu klasör, bir Nage tasdik kaydını **bizim kodumuz olmadan**, kendi makinenizde
doğrulamanız için var.

```bash
python3 verify.py sample/receipt.json --pubkey sample/pubkey.txt
```

Bağımlılık: Python 3.9+. Ed25519 adımı için `cryptography` (yoksa o adım
**ÖLÇÜLMEDİ** yazar — atlanmaz, sessizce geçilmez).

---

## Neden var

KLM-5'in tanımı *"bağımsız olarak denetlenebilir"*. Bugüne kadar Nage'ın iki
referans uygulaması da, uygunluk süiti de, altın vektörleri de Nage'ındı. Yani
**seviyenin geçildiğini söyleyen alet, seviyeyi geçtiği iddia edilen sistemin
kendisiydi.**

Bu paket o döngüyü kırmak için. Bize güvenmenizi istemiyoruz; koşmanızı
istiyoruz.

---

## Ne doğrulanabilir, ne doğrulanamaz

Üç kademe. Bu ayrım süsleme değil — aşırı vaat etmemek için.

### KOŞULSUZ — yalnız kayıt + yayımlanmış açık anahtar yeter

| kademe | ne kanıtlar |
|---|---|
| **içerik bütünlüğü** | kayıt yayımlandıktan sonra değiştirilmedi |
| **özgünlük (Ed25519)** | kayıt gerçekten Nage'dan çıktı — sunucularımıza güvenmeden |
| **γ değişmezi** | `declared − grounded = gap`; tek bir güven skoru yok |
| **dürüst-null disiplini** | her `null`'un yanında gerekçesi var (bilinmeyen ≠ sıfır) |
| **bileşim manifesti** | hangi formül, hangi kalibrasyon, hangi worker ürettiği yazılı |

### KOŞULLU — kayıt gerekli metni taşıyorsa

| kademe | koşulu |
|---|---|
| **`claim_support` yeniden hesabı** | kayıt iddia **ve** kanıt metnini taşımalı (yalnız denetçi/operatör görünümü) |

### DOĞRULANAMAZ — ve bunu söylüyoruz

| ne | neden |
|---|---|
| `coherence` | gömü modeli + kalibrasyon artefaktı gerekir |
| attention atfetmesi | worker'ın iç durumu gerekir |
| **cevabın DOĞRU olması** | bu bir **köken** sistemi, doğruluk oracle'ı değil |

Son satır tezin tamamı. Bu sistem *"cevap doğru"* demez; *"cevap şu
kaynaklardan şu şekilde kuruldu ve şu sinyaller şu değerleri aldı"* der.

---

## Doğrulayıcıya neden güvenesiniz?

Güvenmeyin — sınayın:

```bash
python3 verify.py sample/receipt.json --pubkey sample/pubkey.txt --self-test
```

Kaydı kasten bozar (bir skoru oynatır, imzayı bozar, `gap`'i kırar, imzayı
tamamen siler) ve doğrulayıcının **kırmızıya döndüğünü** gösterir. Her zaman
"geçti" diyen bir doğrulayıcı hiçbir şey doğrulamaz. Son iki satır algoritma
beyanını tanınmayan bir değere çevirir; orada kırmızı **yetmez** — teşhisin
FAIL değil NOT MEASURED (`unsupported_algorithm`) olması gerekir.

Çıktı (2026-09-26, iki doğrulayıcıda aynı):

```
── SELF-TEST: the record is deliberately corrupted ──
  · perturb a score                    ✓ turned red
  · break the signature                ✓ turned red
  · break the γ invariant via gap      ✓ turned red
  · remove the signature entirely      ✓ turned red
  · declare an unknown algorithm       ✓ NOT MEASURED, not FAIL
  · declare an empty algorithm         ✓ NOT MEASURED, not FAIL

  the verifier catches corruption ✓
```

Öz-sınama her doğrulayıcıyı **yalnız kendi içinde** sınar; iki uygulamanın aynı
kayıtta ayrışmasını göremez. Onun için:

```bash
python3 test_parity.py        # Node 22.6+ gerekir
```

İki öz-sınamayı koşar, sonra örnek kaydın 13 varyantını (sağlam, kurcalanmış,
tanınmayan / boş / sayısal / liste / nesne / vekil içeren algoritma beyanları,
beyansız, `null`) geçici bir dizinde üretir ve iki doğrulayıcının çıkış kodunu,
`content_integrity` hükmünü ve iddia edilen yerde bayt bayt aynı `--json`
çıktısını karşılaştırır. **Bu klasörü hiçbir CI koşmuyor** (2026-09-26); bir
değişiklikten sonra elle koşulur.

**Çıktı İngilizce** (2026-09-14): bu paket üçüncü taraf denetçiler için
dağıtılıyor ve aracın yüzeyi onların dilinde olmak zorunda. Türkçe anlatım
`docs/klm-standard/` altında kanon olarak duruyor; İngilizce teknik ek
`docs/konferans/EK-A-independent-verification.md`.

**İki uygulama birebir aynı basıyor.** Hüküm üzerinde anlaşıp ifade üzerinde
ayrışan iki doğrulayıcı, gereğinden zor karşılaştırılır — iki tane sevk
etmenin amacı yan yana koyabilmek.

`--json` her kademeyi **kararlı bir kimlikle** anahtarlıyor
(`content_integrity`, `authenticity_ed25519`, `gamma_invariant`,
`honest_nulls`, `composition_manifest`, `claim_support_recompute`) ve insan
okunur adı ayrı bir `name` alanında taşıyor. İlk sürüm görünen adı JSON
anahtarı olarak kullanıyordu; öyle kalsaydı her ifade değişikliği **kırıcı
değişiklik** olurdu.

---

## Kanonik biçim — tam tanım

Bütünlük hash'i şu gövde üzerinden hesaplanır:

```python
body = {k: v for k, v in record.items()
        if k not in ("verification", "signature", "record_ref")}
body["meta"].pop("verification", None)      # boşalırsa `meta` TAMAMEN düşer

canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))  # ensure_ascii=True
digest    = "sha256:" + sha256(canonical.encode("utf-8")).hexdigest()
```

Üç ayrıntı tahmin edilemez, o yüzden yazılı:

1. **`ensure_ascii=True`** — `"ç"` → `ç`. Nage kod tabanında bu biçim
   tek değil (`audit.py` ham UTF-8 yazar); makbuz yolu ASCII-kaçışlıdır.
1b. **Sayılar dilden bağımsız** (`sha256-canonical/2`): tam değerli float
   `1`, `1.0` değil. Aksi hâlde Python dışı hiçbir uygulama doğrulayamaz.
2. **Boşalan `meta` tamamen düşer.** `{"meta": {}}` ile `meta` yokluğu farklı
   kanonik gövdelerdir.
3. **`record_ref` hash'in dışında** — kendine referans olurdu.
4. **Hangi biçim, kayıt söyler:** `meta.verification.algorithm` (yoksa üst
   düzey `verification.algorithm`). Beyan yoksa eski `sha256`. Beyan
   **varlıkla** belirlenir: yalnız anahtarın yokluğu ya da `null` beyansızdır;
   `""`, `0`, `false`, `[]`, `{}` birer beyandır. Tanınan liste kapalıdır
   (`sha256`, `sha256-canonical/2`, `sha256-canonical/3`); listede olmayan bir
   beyan **hash'lenmez** — bütünlük ÖLÇÜLMEDİ (aşağıda, v3 bölümünün sonunda).

---

## Örnek kayıt hakkında

`sample/receipt.json` **üretim kod yollarıyla** üretildi (`gamma._composition`,
`receipt.sign_receipt_body`, `audit.sign_ed25519`) — elle yazılmadı. Ama:

> **`sample/pubkey.txt` bir TEST anahtarıdır, üretim anahtarı değildir.**
> Tohumu deterministiktir ve gizli değildir. Gerçek bir denetimde Nage'ın
> yayımlanmış açık anahtarını ve kendi kaydınızı kullanın.

---

## En ağır bulgu — BULUNDU VE KAPATILDI: kanonik biçim dilden bağımsız değildi

İkinci bir uygulama (`verify.ts`, Node, ayrı yazıldı) aynı kayıt üzerinde
**beş kademede uyuştu, birinde ayrıştı** — ve ayrışan kademe içerik
bütünlüğüydü:

```
PY: "claim_support":1.0
TS: "claim_support":1
```

Python `json.dumps` bir float'ı `1.0` yazar; JavaScript'te float/int ayrımı
**yoktur** ve `JSON.stringify` aynı değeri `1` yazar. Yani bir skor tam olarak
`0` ya da `1` olduğunda iki uygulama farklı kanonik gövde üretir ve hash
tutmaz — **kayıtta hiçbir bozulma olmadan**.

> **Bu, KLM-5'in "üçüncü tarafça doğrulanabilir" iddiasını bütün bir kayıt
> sınıfı için geçersiz kılar.** Ve ancak Python DIŞINDA biri denediğinde
> görünür.

`claim_support = 1.0` nadir bir uç değil: kanıt iddiayı tamamen kapsadığında
tam olarak bu çıkar. Aynısı `0.0` için de geçerli.

### Çözüm: biçim SÜRÜMLENDİ, geçmiş kırılmadı

Yeni makbuzlar `sha256-canonical/2` ile imzalanıyor: sayılar dilden bağımsız
(tam değerli float `1.0` değil **`1`**). Eski makbuzlar `sha256` beyan eder ve
**o biçimle doğrulanmaya devam eder** — biçimi sessizce değiştirmek, saklanan
her makbuzu kurcalanmış gibi gösterirdi.

Her iki doğrulayıcı da **kaydın beyan ettiği** algoritmaya göre dallanıyor;
hiçbiri tahmin etmiyor. Beyan edilmiş ama tanınmayan bir algoritma eski
biçime **düşürülmez** (2026-09-26; bkz. v3 bölümünün sonu).

**Altın vektör** iki uygulamada birebir doğrulandı:

```
{"b":true,"d":{"a":2,"z":0},"f":1,"g":0.7124,"i":3,"l":[1,0.5],"n":null,"s":"\u00e7\u0131"}
```

Ve sonuç: `verify.py` ve `verify.ts` aynı kayıtta **6/6 aynı hüküm** veriyor.
Bu, TS'i Python'a taklit ettirerek değil — **şartname boşluğu kapatılarak**
sağlandı.

`NaN`/`Inf` **reddediliyor**: sessizce yazmak, hiçbir uygulamanın
doğrulayamayacağı bir gövde üretirdi.

**İki-uygulama şartının (KLM-Spec §8.4) var olma sebebi tam olarak budur.**
Tek doğrulayıcı, kaydın doğrulanabilir olduğunu değil yalnız o kodun kabul
ettiğini gösterir.

### v3 — v2'nin kapsam beyanı küçük sayılarda yanlıştı (2026-09-25)

v2 "sayılar [0,1] aralığında Python `repr` ile JS `String()` aynı" diyordu.
Değil: basamaklar aynı (ikisi de en kısa gidiş-dönüş) ama **yerleşim** farklı.

```
Python repr(5e-05)   → "5e-05"      JS String(5e-05)  → "0.00005"
Python repr(1.2e-05) → "1.2e-05"    JS                → "0.000012"
Python repr(1e-07)   → "1e-07"      JS                → "1e-7"
```

6 basamağa yuvarlanmış küçük bir ağırlık ya da pay (0.00005) içeren **v2**
makbuzu `verify.ts`'te tutmaz — kayıtta bozulma olmadan. (Bulan: platform
STEMMA akış incelemesi; `meta.attention_attribution` bloğu bu aralığı daha
erişilebilir kılıyordu.)

Çözüm yine sürümleme: yeni makbuzlar **`sha256-canonical/3`** ile imzalanır.
Tek fark sayı biçimidir: **ECMAScript Number::toString** (`String(x)`in
tanımı; ECMA-262), anahtarlar UTF-16 kod birimi sırasıyla. `verify.ts`'te bu
dilin kendi `String()`idir; `verify.py` tanımı Python'da yeniden uygular.
Ölçülen (2026-09-25, Node v25.9.0): platform üretici (`receipt._num_v3`) ve
`verify.py` `_num_v3`, **50 012 double** (20 000 rastgele 64-bit desenin
19 994 sonlu olanı + 30 000 yapılı değer + 18 uç değer) ve **3 004 büyük
tamsayıda** Node `String()` ile karşılaştırıldı: ikisinde de 0 ayrışma.
(Önceki satır "50 000 rastgele double" diyordu; o koşumun kendi raporu
49 990 sayıyordu. Bu sayılar bu koşumda yeniden ölçüldü.)

v2 **değişmedi**: saklanan v2 makbuzları `verify.py`'de doğrulanmaya devam
eder. **Bilinen açık:** |x| < 1e-4 (sıfır hariç) sayı taşıyan saklı v2
makbuzları `verify.ts`'te hâlâ FAIL verir; `verify.ts` v2'yi üreticinin
(`repr`) biçimiyle yeniden kurmuyor.

**Uyumluluk — v3'ü tanımayan doğrulayıcı YENİ makbuzda kırılır.** Ölçülen
(2026-09-25, platformun ürettiği 4 sentetik v3 makbuzu): bu klasörün v3
öncesi `verify.py`'si **4/4 bütünlük FAIL** verir — tanımadığı algoritmayı
eski `json.dumps` biçimiyle okur; `0.0` ↔ `0` ya da `5e-05` ↔ `0.00005`
ayrışır. v3 öncesi `verify.ts` aynı 4 makbuzda PASS verir; bu **tesadüftür**
(eski yedek biçimi `JSON.stringify` + `.sort()` + ASCII kaçış, v3 ile
çakışıyor), bir uyumluluk sözü değildir. Kendi doğrulayıcısını yazan üçüncü
taraf, beyan edilen algoritmaya göre dallanmalı ve **tanımadığı** bir beyanı
kurcalama değil, ölçülmemiş saymalıdır.

**Tanınmayan algoritma — ÖLÇÜLMEDİ, kurcalama değil (2026-09-26).** Yukarıdaki
4/4 FAIL'in sebebi, tanınmayan beyanın sessizce eski biçimle okunmasıydı. Bu
artık yapılmıyor: iki doğrulayıcı da tanıdığı biçimleri kapalı bir listede
tutar (`sha256` — beyan yoksa da bu —, `sha256-canonical/2`,
`sha256-canonical/3`). Listede olmayan bir beyan hash'lenmez;
`content_integrity` **NOT MEASURED** olur ve ayrıntı satırı sabit
`unsupported_algorithm` belirteciyle başlar. Kabul profili reddeder (çıkış
`3`) ama bunu FAIL (çıkış `2`) diye göstermez. Beyan yoksa (anahtar yok ya da
`null`) eski yol aynen sürer.

Bu bir **tercihtir, bilinemezlik değil.** Bilinen bir biçim beyan edilen
hash'i tutarsa gövde sağlamdır, biçimin adı ne olursa olsun. Doğrulayıcı yine
de beyan edilmeyen bir biçimi yedek olarak denemez: tutmayan bir yedek
kurcalama göstermez (sahte FAIL olurdu), ve eski yedeğin tutup tutmadığı dile
göre değişir (Python eski biçimde `1.0`, JS `1` yazar) — iki uygulama yine
ayrışırdı.

Ölçülen (2026-09-26, örnek kayıt; yalnız `meta.verification.algorithm`
değişti; `--pubkey sample/pubkey.txt --json`; çıkış kodu `verify.py` /
`verify.ts`):

| beyan | önce (`79a2c66`) | şimdi |
|---|---|---|
| `"sha256-canonical/9"` | 2 / 0 | 3 / 3 |
| `""`, `0`, `false`, `[]`, `{}` | 2 / 0 | 3 / 3 |
| `"\ud800x"` (eşi olmayan vekil) | 1 (çöküş) / 0 | 3 / 3 |

"Önce" sütununda Python'un 2'si **sahte kurcalama**dır: gövde sağlam, imza
geçerli. TS'in 0'ı ise **doğru bir hükümdü**, şansa bağlı olsa da: JS'te eski
yedek biçim v2 ile aynı baytları üretir (sayıyı ikisi de `String(x)` yazar;
örnek gövdede 1 706 bayt birebir, rastgele 20 000 JSON değerinde 0 ayrışma) ve
imzalı hash'i tuttu. Yanlış olan yalnız ayrıntı satırıydı —
`[sha256-canonical/9] computed …` diye, hiç uygulamadığı bir biçimi
hesaplamış gibi yazıyordu. Aynı yedek, JS biçiminden gerçekten ayrılan bir v4'te
sahte FAIL verirdi. Vekilli beyanda `verify.py` stdout'a yazarken
`UnicodeEncodeError` ile çöküyordu (çıkış 1, belgelenen 0/2/3 dışında).

Bu değişikliğin **ilk hâli** de iki delik taşıyordu ve gözden geçirmede
bulundu: beyanı doğrulukla sınıyordu (`""`, `0`, `false` → Python 2 / TS 0;
`[]`, `{}` → Python 2 / TS 3, çünkü "yanlış-değer" kümesi dillere göre
değişir) ve vekil çöküşü sürüyordu. Şimdi bütün satırlarda `--json` çıktıları
bayt bayt aynı (`test_parity.py`). Örnek kaydın kendisi (`sha256-canonical/2`)
PASS kalır; tek bir değeri değiştirilmiş kopya FAIL (çıkış 2) kalır. Sonuç: bir
sonraki biçimi (ör. v4) tanımayan bu doğrulayıcı v4 makbuzunu **reddeder ama
kurcalanmış demez**.

**Bedeli — algoritma beyanı imzalı değil.** `meta.verification` hash'lenen
gövdeden çıkarılır ve Ed25519 imzası yalnız beyan edilen hash'i kapsar; yani
`algorithm` alanını ne bütünlük ne özgünlük bağlar. Kurcalanmış bir gövdeye
tanınmayan bir algoritma yazmak teşhisi FAIL'den (2) NOT MEASURED'a (3)
indirir. Kabul profili yine reddeder; `--diagnostic` görünümü ise bunu
"hiçbir koşulsuz kademe düşmedi" diye basar (o mod zaten kabul kapısı
değildir). Beyanı imza kapsamına almak üretici tarafında ayrı bir karardır.

**Yayım sırası:** bu klasörün v3 sürümü, v3 imzalayan platformla **aynı
anda** (ya da önce) yayımlanır; aksi hâlde yayımlanan `verify.py`, tam
değerli bir float (`0.0`) ya da |x| < 1e-4 bir sayı taşıyan her yeni makbuzda
FAIL verir (ölçülen 4 makbuzun 4'ü bu sınıftaydı).

## Bu paketin ilk koşumunda bulduğu iki kusur

Dürüstlük gereği burada duruyor — paket işini yaptı:

**1. İmzala → doğrula turu kırılıyordu.** `sign_receipt_body`, gövdede `meta`
yoksa onu *yaratıyor*; doğrulama ise geriye `meta: {}` bırakıyordu. Boş sözlük
ile hiç-olmayan anahtar farklı kanonik gövde verir, yani imza tutmuyordu.
Üretimde ateşlemiyordu (`build_receipt_body` her zaman dolu bir `meta` verir)
ama gizli bir kusurdu. Düzeltildi.

**2. Kanonik biçim belirtilmemişti.** Aynı kod tabanında iki farklı
kanonikleştirme var (`receipt.py` ASCII-kaçışlı, `audit.py` ham UTF-8).
Türkçe içeren bir kayıtta ikisi farklı hash verir ve dışarıdan doğrulayan biri
hangisi olduğunu tahmin edemez. Yukarıda tanımlandı; kod tarafındaki
birleştirme açık iş kalemi.

---

## Kayıt nasıl alınır

Kendi kaydınızı almak için:

```
GET /attestation/{request_id}?tier=auditor
```

`tier` ne kadar açarsa o kadar doğrulanır: `user` görünümü koşullu kademeyi
taşımaz, `auditor` taşır. Kademeler `klm-disclosure/0.1` ile tanımlı.

---

## Uyumluluk süiti (CTS)

Kaydın **şekli** için ayrı bir süit var: `packages/conformance-cts/`. Bu
doğrulayıcı tek bir kaydın içeriğini sınar; CTS bir uygulamanın sözleşmeye
uyup uymadığını sınar. İkisi farklı sorular.

---

## Sınırlar

- Bu doğrulayıcı **bu kaydın** iç tutarlılığını ve özgünlüğünü sınar. Kaydın
  tarif ettiği çıkarımın gerçekten olduğunu kanıtlamaz; onun için zincir/Merkle
  içerme kanıtı gerekir (`klm5-verifiable-exit-test.md` §1.3 — henüz açık).
- Merkle içerme kanıtı **henüz yayımlanmıyor**. Seçmeli atlama (bir kaydı
  gizleme) bu paketle tespit edilemez.
- İki-uygulama şartı (`KLM-Spec §8.4`) **karşılandı ve geçti**: `verify.py` ve
  `verify.ts` ayrı yazıldı, aynı kayıtta **6/6 aynı hüküm** veriyor, ikisi de
  **dört** mutasyonda kırmızıya dönüyor (2026-09-26'dan beri iki
  tanınmayan-beyan satırında da NOT MEASURED teşhisini veriyor; iki dilin
  eşliği `test_parity.py` ile). Ayrışma, TS'i taklit ettirerek değil
  şartname boşluğu kapatılarak giderildi.
  **2026-09-22 daraltması:** o 6/6 yalnız **örnek** kayıtta ölçülmüştü. Gerçek bir üretim
  kaydında (`klm-disclosure/0.1`, operator görünümü) imza hükmü **ayrışıyordu** — Python PASS,
  TS NOT MEASURED — çünkü TS imzayı `record_ref.signature_ed25519`'da aramıyordu ve üretim onu
  tam orada taşıyor. TS arama sırası Python'la birebir yapıldı; iki kayıtta 6/6 aynı hüküm.
  Örnek kayıt, üretimin "Kayıt nasıl alınır" yoluyla verdiği **şekilde değil** — `sample-not-production`
  yalnız anahtar için değil şekil için de geçerli (`docs/IDDIA-KAYDI.md` #100).
- **Dürüst-null kontrolü yalnız SONEKLİ kardeşi gerekçe sayar** (`_reason`,
  `_status`, `_basis`). Kendi gerekçesini çıplak `status`/`reason`
  anahtarlarında taşıyan iç içe bir blok — ör. worker'ın aynen saklanan
  `meta.attention_attribution`'ı (`status: not_attempted`,
  `reason: no_chunk_blocks`) — gerekçesiz null sayılır. Ölçülen (2026-09-25,
  sentetik platform makbuzu): böyle bir iskelet +10, ölçülmüş bir blok +2
  gerekçesiz null ekler. Platform makbuzlarında bu kontrol zaten FAIL'di;
  kural **değiştirilmedi** (yayımlanan anlamı değiştirmek ayrı bir karardır).
- Bu doğrulayıcılar **Nage deposundaki ayrı uygulamalardır**. Nage SDK'sını ya da
  sunucu iç kodunu gerektirmemeleri değerlidir; fakat verilen betiği koşturmak,
  **bağımsız yeniden-uygulama** kanıtı değildir. İkisi ayrı kanıttır.

## Kabul profili — `nage-acceptance/1`

**Bir teslim kapısı çıplak `ok` alanını okumamalıdır.** 2026-09-19'a kadar `ok`
şöyle hesaplanıyordu: *koşulsuz kontrollerden herhangi biri FAIL mı?* Zorunlu bir
kontrolün **ölçülmemiş** olması genel sonucu düşürmüyordu. Ölçülen sonuç: imza alanı
kaldırılınca `ok=true`, çıkış 0; `cryptography` kurulu değilken de `ok=true`, çıkış 0.

Bu, Ed25519'un kırılması değildi. Projenin birinci ilkesinin (`CLAUDE.md` §3.1,
*not-known ≠ zero*) doğrulayıcının **kendi toplama kuralında** ihlaliydi.

Neden yakalanmadı: öz-sınamanın üç mutasyonu da bir alanı **bozuyordu** (→ FAIL →
kırmızı). Hiçbiri alanı **kaldırmıyordu** (→ NOT MEASURED → yeşil). Artık
"imzayı tamamen kaldır" mutasyonu da var.

Kabul kuralı (varsayılan):

- Zorunlu beş kontrolün **her biri PASS** olmalı: `content_integrity`,
  `authenticity_ed25519`, `gamma_invariant`, `honest_nulls`, `composition_manifest`.
- **Hiçbir** kademede FAIL olmamalı; koşullu bir kontrolün FAIL'i de kabulü düşürür.
- `NOT MEASURED` FAIL ile aynı teşhis değildir, fakat **PASS da değildir**.

`--diagnostic` eski gevşek görünümü verir ve kendini "kabul kapısı DEĞİL" diye
etiketler. Kabul için kullanılmaz.

**İki kontrol ayrı ayrı zorunludur ve biri diğerini ima etmez.** İmza *beyan edilen
hash*'i kapsar. Gövde düzenlenirse yalnız bütünlük yakalar; imza silinirse yalnız
özgünlük yakalar.

| müdahale | beklenen |
|---|---|
| özgün kayıt | kabul (0) |
| JSON'a tek boşluk | **kabul** (0) — kanonik gövde aynı |
| imzalı içerik değişti | ret (2), `content_integrity: FAIL` |
| tanınmayan algoritma beyanı (ör. `sha256-canonical/9`; `""`, `0`, `[]` de) | ret (3), `content_integrity: NOT MEASURED` — `unsupported_algorithm` |
| imza alanı kaldırıldı | ret (2), `authenticity_ed25519: NOT MEASURED` |
| `cryptography` yok | ret (2), `authenticity_ed25519: NOT MEASURED` |
| yanlış açık anahtar | ret (2), `authenticity_ed25519: FAIL` |
| `--pubkey` verilmedi | ret (3) |
| **cevap uydurma + hash yeniden hesaplanmış + imza silinmiş** | **ret (3)** |
| **cevap uydurma + hash ve imza silinmiş** | **ret (3)** |

Son iki satır bu profilin varlık sebebidir. Cevabı değiştirip hash'i **doğru** yeniden hesaplayan ve
imzayı silen bir makbuz, eski kuralda iki doğrulayıcıdan da geçiyordu: bütünlük PASS veriyordu, çünkü
gövde ile hash tutarlıydı. Yakalayabilecek tek kontrol imzaydı — ve o "ölçülmemiş" sayılıyordu.

Çıkış kodları: `0` kabul · `2` gerçek bir FAIL ile ret · `3` yalnız zorunlu kontrol ölçülemediği için ret.
İkisi de kabul etmez; kod hangisi olduğunu saklar.

"Tek bayt değişince FAIL" **yanlış bir kabul ölçütüdür**: JSON boşluğu değişebilir
ve PASS kalmalıdır. Değişmemesi gereken, kanonik gövdedir.

## Kanon bağı
`docs/klm-standard/klm5-verifiable-exit-test.md` · `KLM-Specification.md` §8.4 ·
`docs/klm-standard/composition-manifest.md`
