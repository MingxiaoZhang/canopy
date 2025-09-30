import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class URLCanonicalizer:
    """URL canonicalization and normalization"""

    def __init__(self):
        # Common tracking parameters to remove
        self.tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', 'ref', 'referrer', '_ga', '_gid',
            'source', 'campaign', 'medium', 'content', 'term',
            'igshid', 'ncid', 'sr_share', 'recruiter', 'trk'
        }

        # Parameters that should be kept and normalized
        self.meaningful_params = {
            'id', 'page', 'p', 'offset', 'limit', 'sort', 'order',
            'category', 'tag', 'search', 'q', 'query', 'filter'
        }

    def canonicalize(self, url: str) -> str:
        """
        Canonicalize URL to standard form

        Args:
            url: Raw URL to canonicalize

        Returns:
            Canonicalized URL string
        """
        try:
            parsed = urlparse(url.lower().strip())

            # Normalize scheme
            if not parsed.scheme:
                parsed = urlparse(f"https://{url}")

            # Normalize domain (remove www, convert to lowercase)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # Normalize path (remove trailing slash, decode percent encoding)
            path = parsed.path.rstrip('/')
            if not path:
                path = '/'

            # Filter and sort query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)

                # Remove tracking parameters
                filtered_params = {
                    k: v for k, v in params.items()
                    if k.lower() not in self.tracking_params
                }

                # Sort parameters for consistency
                if filtered_params:
                    sorted_params = sorted(filtered_params.items())
                    query = urlencode(sorted_params, doseq=True)
                else:
                    query = ''
            else:
                query = ''

            # Remove fragment (everything after #)
            canonical_url = urlunparse((
                parsed.scheme,
                domain,
                path,
                '',  # params
                query,
                ''   # fragment
            ))

            return canonical_url

        except Exception as e:
            logging.warning(f"Failed to canonicalize URL {url}: {e}")
            return url.lower().strip()

    def is_equivalent(self, url1: str, url2: str) -> bool:
        """Check if two URLs are equivalent after canonicalization"""
        return self.canonicalize(url1) == self.canonicalize(url2)