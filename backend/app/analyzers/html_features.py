from urllib.parse import urlparse

from bs4 import BeautifulSoup

_SOCIAL_PATTERNS = (
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
    "reddit.com", "snapchat.com", "whatsapp.com", "telegram.org", "t.me",
)


class HtmlFeatures:

    @staticmethod
    def extract(html: str, url: str = ""):

        soup = BeautifulSoup(html, "lxml")

        parsed_url = urlparse(url)
        page_domain = parsed_url.netloc.replace("www.", "")

        # ── Existing features ────────────────────────────────

        title = soup.find("title")

        favicon = soup.find(
            "link",
            rel=lambda x: x and any(
                "icon" in v.lower()
                for v in (x if isinstance(x, list) else [x])
            )
        )

        description = soup.find("meta", attrs={"name": "description"})

        password_fields = soup.find_all("input", {"type": "password"})
        hidden_fields   = soup.find_all("input", {"type": "hidden"})
        images          = soup.find_all("img")
        css_files       = soup.find_all("link", rel="stylesheet")
        js_files        = soup.find_all("script")

        # ── New HTML features ────────────────────────────────

        iframes = soup.find_all("iframe")

        # External form submit
        has_external_form = 0
        for form in soup.find_all("form"):
            action = form.get("action", "")
            if action.startswith("http"):
                action_domain = urlparse(action).netloc.replace("www.", "")
                if page_domain and action_domain != page_domain:
                    has_external_form = 1
                    break

        # Social network links
        all_links = soup.find_all("a", href=True)
        has_social_net = int(any(
            any(s in link["href"] for s in _SOCIAL_PATTERNS)
            for link in all_links
        ))

        # Submit button
        submit_inputs   = soup.find_all("input", {"type": "submit"})
        submit_buttons  = soup.find_all("button", {"type": "submit"})
        has_submit = int(bool(submit_inputs or submit_buttons))

        # Copyright
        page_text = soup.get_text()
        has_copyright = int(
            "©" in page_text or "copyright" in page_text.lower()
        )

        # Responsive (viewport meta)
        viewport = soup.find("meta", attrs={"name": "viewport"})
        is_responsive = int(viewport is not None)

        # Self / empty / external refs
        self_ref = empty_ref = external_ref = 0
        for link in all_links:
            href = link.get("href", "").strip()
            if not href or href == "#":
                empty_ref += 1
            elif href.startswith("http"):
                link_domain = urlparse(href).netloc.replace("www.", "")
                if page_domain and link_domain == page_domain:
                    self_ref += 1
                else:
                    external_ref += 1
            elif href.startswith("/"):
                self_ref += 1

        return {
            "HasTitle":        int(title is not None),
            "HasFavicon":      int(favicon is not None),
            "HasDescription":  int(description is not None),
            "HasPasswordField": int(len(password_fields) > 0),
            "HasHiddenFields":  int(len(hidden_fields) > 0),
            "NoOfImage":       len(images),
            "NoOfCSS":         len(css_files),
            "NoOfJS":          len(js_files),

            "NoOfiFrame":           len(iframes),
            "HasExternalFormSubmit": has_external_form,
            "HasSocialNet":          has_social_net,
            "HasSubmitButton":       has_submit,
            "HasCopyrightInfo":      has_copyright,
            "IsResponsive":          is_responsive,
            "NoOfSelfRef":           self_ref,
            "NoOfEmptyRef":          empty_ref,
            "NoOfExternalRef":       external_ref,
        }
