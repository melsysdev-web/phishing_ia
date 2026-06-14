import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    virustotal_api_key: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    safe_browsing_api_key: str = os.getenv("SAFE_BROWSING_API_KEY", "")
    fact_check_api_key: str = os.getenv("FACT_CHECK_API_KEY", "")


settings = _Settings()
