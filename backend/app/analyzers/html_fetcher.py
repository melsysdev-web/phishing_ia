import requests


class HtmlFetcher:

    @staticmethod
    def get_html(url: str):

        try:

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            return {
                "success": True,
                "status_code": response.status_code,
                "html": response.text
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
                "html": ""
            }