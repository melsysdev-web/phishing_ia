from urllib.parse import urlparse


class FeatureMapper:

    @staticmethod
    def map(url, url_features):

        parsed = urlparse(url)

        return {

            "URLLength":
                url_features.get(
                    "url_length",
                    0
                ),

            "DomainLength":
                url_features.get(
                    "domain_length",
                    0
                ),

            "IsDomainIP":
                int(
                    url_features.get(
                        "has_ip",
                        False
                    )
                ),

            "TLDLength":
                len(
                    parsed.netloc.split(".")[-1]
                ),

            "NoOfSubDomain":
                max(
                    0,
                    len(
                        parsed.netloc.split(".")
                    ) - 2
                ),

            "IsHTTPS":
                int(
                    url_features.get(
                        "has_https",
                        False
                    )
                )
        }