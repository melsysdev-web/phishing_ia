# Augments roberta_dataset.csv with legitimate ccTLD URLs and phishing mimic
# examples so the RoBERTa URL classifier learns to distinguish them.


import random
import pandas as pd

random.seed(42)

# ──────────────────────────────────────────────
# Legitimate ccTLD base domains (real patterns)
# ──────────────────────────────────────────────

LEGIT_BASES = {
    # El Salvador
    "com.sv":  ["banco", "telcel", "claro", "tigo", "fepade", "ues",
                 "bcr", "hacienda", "presidencia", "mined", "digicel",
                 "almacenes", "distribuidora", "ferreteria", "tecnologia"],
    "gob.sv":  ["hacienda", "salud", "educacion", "presidencia", "rree",
                 "defensoria", "pnc", "fiscalia", "csj", "dgii"],
    "edu.sv":  ["ues", "utec", "udb", "ujmd", "univo", "unica",
                 "ups", "catolica", "morazan", "panam"],
    "org.sv":  ["fundemas", "fusades", "funde", "cámara", "anep",
                 "insaforp", "isss", "fisdl", "bienestar"],
    "net.sv":  ["tigo", "claro", "columbus", "snet", "speednet"],

    # Mexico
    "com.mx":  ["banamex", "banorte", "hsbc", "santander", "bbva",
                 "televisa", "telcel", "telmex", "oxxo", "liverpool",
                 "palacio", "soriana", "walmart", "sams", "coppel"],
    "gob.mx":  ["sat", "imss", "issste", "sep", "sre", "shcp",
                 "segob", "semarnat", "sedena", "semar", "inegi"],
    "edu.mx":  ["unam", "ipn", "itesm", "udg", "uam", "buap",
                 "uanl", "uady", "uabc", "colmex"],
    "org.mx":  ["cce", "coparmex", "canacintra", "concamin", "amexcap"],

    # Argentina
    "com.ar":  ["mercadolibre", "clarin", "infobae", "lanacion",
                 "telecom", "personal", "fibertel", "cablevision",
                 "galicia", "naranjax", "bbva"],
    "gob.ar":  ["afip", "anses", "migraciones", "cancilleria",
                 "educacion", "salud", "justicia", "interior"],
    "edu.ar":  ["uba", "unc", "unl", "unr", "unlp", "unsam", "utn"],
    "org.ar":  ["rnia", "coa", "conicet", "senasa"],

    # Colombia
    "com.co":  ["davivienda", "bancolombia", "avianca", "ecopetrol",
                 "claro", "movistar", "tigo", "codensa", "exito"],
    "gov.co":  ["dian", "minhacienda", "mineducacion", "minsalud",
                 "cancilleria", "superfinanciera", "icfes"],
    "edu.co":  ["unal", "uniandes", "eafit", "javeriana", "rosario"],

    # Peru
    "com.pe":  ["bcp", "bbva", "interbank", "scotiabank", "entel",
                 "movistar", "claro", "ripley", "saga", "wong"],
    "gob.pe":  ["sunat", "reniec", "onpe", "mef", "minedu",
                 "minsa", "pcm", "rree", "indecopi"],
    "edu.pe":  ["pucp", "unmsm", "up", "ulima", "usmp", "udep"],

    # Chile
    "cl":      ["falabella", "ripley", "sodimac", "bci", "scotiabank",
                 "entel", "movistar", "claro", "latam", "cmr"],
    "gob.cl":  ["sii", "registrocivil", "chileatiende", "bcn",
                 "minsal", "mineduc", "minhac", "conaf"],
    "edu.cl":  ["uchile", "puc", "usach", "uach", "udec", "ubiobio"],

    # UK
    "co.uk":   ["bbc", "tesco", "sainsburys", "marks-and-spencer",
                 "lloydsbank", "barclays", "natwest", "rbs",
                 "boots", "argos", "currys", "asos"],
    "gov.uk":  ["hmrc", "dwp", "dvla", "nhs", "companies-house",
                 "parliament", "judiciary", "legislation"],
    "org.uk":  ["redcross", "oxfam", "ncvo", "rspca", "shelter"],
    "ac.uk":   ["ox", "cam", "imperial", "ucl", "manchester",
                 "birmingham", "bristol", "edinburgh", "kcl"],

    # Spain
    "es":      ["bbva", "santander", "caixabank", "sabadell",
                 "bankia", "movistar", "vodafone", "orange",
                 "renfe", "iberia", "correos", "elcorteingles"],

    # Brazil
    "com.br":  ["bradesco", "itau", "caixa", "santander", "nubank",
                 "globo", "uol", "ig", "terra", "americanas",
                 "magazine-luiza", "casas-bahia", "tim", "claro"],
    "gov.br":  ["receita", "previdencia", "mec", "mms", "ans",
                 "anatel", "anvisa", "ibge", "banco-central"],
    "edu.br":  ["usp", "unicamp", "ufrj", "ufmg", "ufrgs", "ufsc"],

    # Australia
    "com.au":  ["commbank", "westpac", "anz", "nab", "woolworths",
                 "coles", "telstra", "optus", "qantas", "jetstar",
                 "bigw", "kmart", "bunnings", "realestate"],
    "gov.au":  ["ato", "myhealth", "centrelink", "abf", "asic",
                 "accc", "apra", "austrade"],
    "edu.au":  ["unimelb", "anu", "usyd", "uq", "unsw", "monash"],

    # Germany
    "de":      ["bahn", "telekom", "sparkasse", "volksbank",
                 "dhl", "otto", "zalando", "mediamarkt",
                 "saturn", "aldi", "lidl", "rewe"],

    # France
    "fr":      ["credit-agricole", "bnpparibas", "societegenerale",
                 "laposte", "sncf", "edf", "orange", "sfr",
                 "bouygues", "leboncoin", "cdiscount", "fnac"],

    # Japan
    "co.jp":   ["rakuten", "amazon", "yahoo", "ntt", "softbank",
                 "au", "docomo", "mufg", "smbc", "mizuho"],
    "ne.jp":   ["ocn", "biglobe", "nifty", "so-net"],

    # India
    "co.in":   ["sbi", "icici", "hdfc", "axis", "kotak",
                 "reliance", "airtel", "vodafone", "bsnl", "jio"],
    "gov.in":  ["incometax", "mca", "uidai", "irctc",
                 "epfindia", "nic", "niti", "mospi"],
    "edu.in":  ["iitb", "iitd", "iitm", "iitk", "iisc", "jnu"],

    # Canada
    "ca":      ["rbc", "td", "scotiabank", "bmo", "cibc",
                 "bell", "rogers", "telus", "shopify",
                 "cbc", "globeandmail"],
    "gc.ca":   ["cra", "servicecanada", "parl", "statcan",
                 "cbsa", "ircc", "nrcan", "tc"],
}

PATHS = [
    "", "/", "/index.html", "/home", "/inicio", "/en/", "/es/",
    "/login", "/mi-cuenta", "/servicios", "/productos", "/contacto",
    "/about", "/nosotros", "/noticias", "/blog", "/soporte",
    "/ayuda", "/pagos", "/transferencias", "/reportes",
]

# Incluye parámetros de tracking legítimos con valores numéricos largos
# para que el modelo aprenda que ?zx=..., ?t=..., ?ref=... son normales
QUERY_PARAMS = [
    "", "", "", "",   # mayoría sin query params
    "?lang=es", "?lang=en", "?ref=home", "?section=personal",
    "?utm_source=web", "?utm_medium=email", "?utm_campaign=nav",
    "?page=1", "?id=main", "?tab=overview",
    # cache-busters y tracking numérico (patrón ?zx=, ?t=, etc.)
    f"?zx={random.randint(10**11, 10**13)}",
    f"?zx={random.randint(10**11, 10**13)}",
    f"?t={random.randint(10**9, 10**12)}",
    f"?_={random.randint(10**9, 10**12)}",
    f"?ts={random.randint(10**9, 10**12)}",
    f"?ref={random.randint(10**6, 10**9)}",
    f"?v={random.randint(1, 9999)}",
    f"?session_id={random.randint(10**8, 10**10)}",
    "?source=email&medium=cta",
    "?from=banner&campaign=summer",
]

SUBDOMAINS = [
    "www", "www", "www", "www",   # la mayoría con www
    "", "", "",                    # algunos sin subdominio
    "portal", "banca", "online",
    "servicios", "pagos", "mail",
    "mi", "app", "secure",
]


def _make_legit_url(subdomain: str, name: str, tld: str,
                    path: str, qp: str) -> str:
    if subdomain:
        host = f"{subdomain}.{name}.{tld}"
    else:
        host = f"{name}.{tld}"
    return f"https://{host}{path}{qp}"


def _make_phishing_url(name: str, tld: str) -> str:
    """Phishing mimicking a ccTLD brand."""
    tricks = [
        f"http://{name}-{tld.replace('.', '-')}-secure.com/login",
        f"http://secure-{name}.{tld}.verify-account.net/confirm",
        f"http://{name}.{tld}.account-update.info/login",
        f"http://login-{name}-{tld.replace('.', '')}.xyz/access",
        f"http://{name}-verify.com/{tld}/login",
        f"http://192.168.{random.randint(1,254)}.{random.randint(1,254)}/{name}/login",
        f"http://{name}.{tld}.phishing-test-{random.randint(1000,9999)}.tk/",
    ]
    return random.choice(tricks)


def generate_samples(n_legit_per_tld: int = 40):
    legit_rows = []
    phish_rows = []

    for tld, names in LEGIT_BASES.items():
        for _ in range(n_legit_per_tld):
            name = random.choice(names)
            sub  = random.choice(SUBDOMAINS)
            path = random.choice(PATHS)
            qp   = random.choice(QUERY_PARAMS)
            legit_rows.append({
                "URL":   _make_legit_url(sub, name, tld, path, qp),
                "label": 1,   # legítimo
            })
            # Phishing mimético para el mismo TLD/marca (mantener balance)
            phish_rows.append({
                "URL":   _make_phishing_url(name, tld),
                "label": 0,   # phishing
            })

    return legit_rows, phish_rows


if __name__ == "__main__":
    print("Cargando dataset original...")
    df_orig = pd.read_csv("datasets/roberta_dataset.csv", encoding="latin-1")
    print(f"  Original: {len(df_orig)} filas  {df_orig['label'].value_counts().to_dict()}")

    legit, phish = generate_samples(n_legit_per_tld=40)
    df_aug = pd.DataFrame(legit + phish)
    df_aug.columns = ["URL", "label"]

    print(f"  Generados: {len(df_aug)} filas  {df_aug['label'].value_counts().to_dict()}")

    df_final = pd.concat([df_orig, df_aug], ignore_index=True).sample(
        frac=1, random_state=42
    )

    out = "datasets/roberta_dataset_augmented.csv"
    df_final.to_csv(out, index=False, encoding="utf-8")

    print(f"\nDataset aumentado guardado en: {out}")
    print(f"Total filas: {len(df_final)}")
    print(f"Distribución:\n{df_final['label'].value_counts().to_string()}")
