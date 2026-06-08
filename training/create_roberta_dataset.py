import pandas as pd

DATASET_PATH = "datasets/raw/phishing_urls.csv"

df = pd.read_csv(DATASET_PATH)

sample_size = 50000

df_sample = df.sample(
    n=sample_size,
    random_state=42
)

roberta_df = df_sample[
    ["URL", "label"]
]

roberta_df.to_csv(
    "datasets/roberta_dataset.csv",
    index=False
)

print(
    f"Dataset creado: {len(roberta_df)} registros"
)