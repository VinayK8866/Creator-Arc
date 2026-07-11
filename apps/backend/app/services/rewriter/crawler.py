import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import socket

# Common User-Agent header to emulate web browsers
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}


class StyleCrawler:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def fetch_rss_feed(self, feed_url: str) -> list:
        """Fetch article links and titles from an RSS feed.
        Returns a list of dictionaries: [{'title': '...', 'link': '...'}]
        """
        print(f"Crawler: Fetching RSS feed from: {feed_url}...")
        try:
            req = urllib.request.Request(feed_url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = []
            
            # Search for typical RSS items
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                
                if link:
                    items.append({"title": title, "link": link})
                    
            print(f"Crawler: Found {len(items)} items in feed.")
            return items
        except socket.timeout:
            print(f"Crawler Error: Timeout fetching RSS feed {feed_url}")
            return []
        except Exception as e:
            print(f"Crawler Error: Failed to parse feed {feed_url}. Error: {str(e)}")
            return []

    def fetch_page_html(self, url: str) -> str:
        """Fetch the raw HTML content of a single webpage."""
        print(f"Crawler: Fetching page HTML from: {url}...")
        try:
            req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                # Handle potential compression if needed, otherwise read raw bytes
                html_bytes = response.read()
                
            # Detect encoding if possible, fallback to utf-8
            content_type = response.headers.get_content_charset()
            encoding = content_type if content_type else "utf-8"
            
            try:
                return html_bytes.decode(encoding, errors="replace")
            except Exception:
                return html_bytes.decode("utf-8", errors="replace")
                
        except socket.timeout:
            print(f"Crawler Error: Timeout fetching URL: {url}")
            return ""
        except Exception as e:
            print(f"Crawler Error: Failed to fetch URL {url}. Error: {str(e)}")
            return ""
