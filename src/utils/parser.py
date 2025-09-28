from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class HTMLParser:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc

    def parse(self, html_content):
        """Parse HTML content and extract relevant data"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract all links
        links = []
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(self.base_url, link['href'])
            # Filter out non-HTTP(S) links
            if absolute_url.startswith(('http://', 'https://')):
                links.append(absolute_url)

        # Extract CSS links
        css_links = []
        for link in soup.find_all('link', rel='stylesheet'):
            if link.get('href'):
                css_url = urljoin(self.base_url, link['href'])
                css_links.append(css_url)

        # Extract inline CSS
        inline_css = []
        for style in soup.find_all('style'):
            if style.string:
                inline_css.append(style.string)

        # Extract meta information
        meta_data = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_data[name] = content

        return {
            'title': soup.title.string.strip() if soup.title and soup.title.string else '',
            'links': list(set(links)),  # Remove duplicates
            'css_links': list(set(css_links)),  # Remove duplicates
            'inline_css': inline_css,
            'meta_data': meta_data,
            'html': str(soup),
            'text_content': soup.get_text(strip=True)
        }

    def extract_images(self, html_content):
        """Extract image URLs from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []

        # Extract img tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(self.base_url, src)
                images.append(absolute_url)

        return list(set(images))