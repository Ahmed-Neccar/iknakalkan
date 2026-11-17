from services.analysis import analyze_message, analyze_rule_based


def test_detects_urgency_and_fear():
    text = "Hesabınız 24 saat içinde güncellenmezse erişiminiz kesilecektir, hemen tıklayın."
    result = analyze_rule_based(text)
    techniques = {f["technique"] for f in result["findings"]}
    assert "aciliyet" in techniques and "korku_tehdit" in techniques


def test_each_finding_has_required_fields():
    text = "Sayın müdürümüz bu talebi hemen onaylamanızı rica ediyor, herkes onayladı."
    result = analyze_rule_based(text)
    assert result["findings"]
    for f in result["findings"]:
        for key in ("technique", "evidence", "explanation", "confidence", "alternative", "defense"):
            assert key in f and f[key]


def test_no_technique_found_on_neutral_text():
    result = analyze_rule_based("Yarınki toplantı saat 10'da başlayacak, görüşmek üzere.")
    assert result["findings"] == [] and result["overall_risk"] == "düşük"


def test_empty_message_is_demo_mode():
    result = analyze_message("")
    assert result["mode"] == "demo" and result["findings"] == []


def test_without_llm_key_falls_back_to_rule_based(monkeypatch):
    import config
    monkeypatch.setattr(config, "llm_available", lambda: False)
    result = analyze_message("Acil! Hemen tıklayın.")
    assert result["mode"] == "rule_based"
    assert "demo" in result["note"].lower() or "kural" in result["note"].lower()
