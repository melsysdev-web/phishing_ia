from bs4 import BeautifulSoup


class HtmlFeatures:

    @staticmethod
    def extract(html: str):

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        title = soup.find("title")

        favicon = soup.find(
            "link",
            rel=lambda x:
            x and "icon" in x.lower()
        )

        description = soup.find(
            "meta",
            attrs={
                "name": "description"
            }
        )

        password_fields = soup.find_all(
            "input",
            {"type": "password"}
        )

        hidden_fields = soup.find_all(
            "input",
            {"type": "hidden"}
        )

        images = soup.find_all("img")

        css_files = soup.find_all(
            "link",
            rel="stylesheet"
        )

        js_files = soup.find_all("script")

        return {

            "HasTitle":
                int(title is not None),

            "HasFavicon":
                int(favicon is not None),

            "HasDescription":
                int(description is not None),

            "HasPasswordField":
                int(
                    len(password_fields) > 0
                ),

            "HasHiddenFields":
                int(
                    len(hidden_fields) > 0
                ),

            "NoOfImage":
                len(images),

            "NoOfCSS":
                len(css_files),

            "NoOfJS":
                len(js_files)
        }