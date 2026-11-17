# İKNAKALKAN — Açıklanabilir Sosyal Mühendislik Analiz Platformu

Üniversite düzeyinde araştırma ve güvenli farkındalık eğitimi için Streamlit tabanlı uygulama. Sentetik/izinli verilerle çalışacak şekilde tasarlanmıştır.

## Öne çıkanlar
- Rol tabanlı giriş, işlem kayıtları ve SQLite veri tabanı
- Sentetik profiller, senaryo yönetimi ve güvenli simülasyon akışı
- Açıklanabilir, kanıt ifadeleri içeren kural tabanlı analiz
- İsteğe bağlı yerel Ollama analizi; JSON çıktı doğrulama ve hata durumunda açık kural tabanlı geri dönüş
- Eğitim öncesi/sonrası ölçümleri, grafikler ve CSV/PDF raporları
- Gerçek e-posta gönderimi varsayılan olarak kapalı

## Kurulum (Windows/macOS/Linux)
Python 3.11 veya üzeri önerilir.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; macOS/Linux: cp .env.example .env
streamlit run app.py
```

İlk yerel demo hesapları: `admin/admin123`, `analyst/analyst123`, `viewer/viewer123`. İlk çalıştırmada yönetici parolasını `IKNA_ADMIN_PASSWORD` ile ayarlayın; demo hesaplarını herkese açık sunucuda kullanmayın.

## Yerel LLM (isteğe bağlı)
1. Ollama'yı kurun: https://ollama.com/download
2. Terminalde `ollama pull qwen2.5:3b` çalıştırın.
3. `.env` içinde `IKNA_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434` ve `OLLAMA_MODEL=qwen2.5:3b` bırakın.
4. Ollama uygulamasının çalıştığından emin olun. Uygulama modelin erişilebilirliğini analiz çağrısı sırasında doğrular.

Ollama kullanılamazsa sistem kural tabanlı analizle devam eder ve bunu kullanıcıya bildirir. Model çıktısı karar desteğidir; kesin hüküm veya bağımsız bilimsel doğrulama değildir.

## Güvenlik ve etik
- `.env`, veritabanı dosyaları, sanal ortam ve kişisel veriler depoya/ZIP'e eklenmemelidir.
- `ALLOW_REAL_SEND=false` varsayılandır; araştırma demosunda gerçek gönderimi açmayın.
- Yalnızca sentetik veya açıkça izin verilmiş test verileri kullanın.
- Canlı dağıtım öncesi demo parolaları, erişim denetimleri, gizlilik ve tehdit modeli gözden geçirilmelidir.

## Testler
```bash
pytest -q
```

Test sonuçları, kullanılan Python ve bağımlılık sürümleriyle birlikte raporlanmalıdır. Bilimsel değerlendirme için etiketli, bağımsız test veri kümesi ve önceden belirlenmiş metrikler gerekir.

## Giriş sorunu / parola sıfırlama

Mevcut veritabanındaki parola demo parolasıyla eşleşmiyorsa veritabanını silmeyin. Uygulamayı durdurun, bu klasörde terminal açın ve `python reset_password.py` komutunu çalıştırın. Listeden kullanıcıyı seçip yeni parolayı iki kez girin. Parola ekranda görünmez. Ardından `streamlit run app.py` ile uygulamayı yeniden başlatın.
