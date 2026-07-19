from backend.app.services.phishing_service import PhishingService

url = "http://testsafebrowsing.appspot.com/s/phishing.html"
print("Analizando:", url)
print("-" * 60)

r = PhishingService.analyze(url)
ra = r.get("risk_assessment", {})
ml = r.get("machine_learning", {})
vt = r.get("virustotal", {})
sb = r.get("safe_browsing", {})
di = r.get("domain_info", {})

print("SCORE  :", ra.get("score"))
print("RIESGO :", ra.get("risk"))
print()
print("RAZONES:")
for i, reason in enumerate(ra.get("reasons", []), 1):
    print(f"  {i}.", reason)
print()
print("VirusTotal   :", vt.get("verdict", vt.get("error", "n/a")))
sb_verdict = sb.get("verdict") if sb.get("is_threat") else "limpia"
print("SafeBrowsing :", sb_verdict)
print("ML phishing  :", ml.get("fusion", {}).get("phishing_probability", "n/a"))
print("Edad dominio :", di.get("domain_age_days", "n/a"), "dias")
print("Tiempo       :", r.get("analysis_time_ms"), "ms")
