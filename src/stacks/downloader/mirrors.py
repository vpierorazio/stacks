def download_from_mirror(d, mirror_url, mirror_type, md5, title=None, resume_attempts=3, subfolder=None):
    """
    Download from any mirror with stale cookie handling.

    Logic:
    - slow_download: Use pre-warmed cookies with direct HTTP requests
    - external_mirror: Try direct, use FlareSolverr on 403 (with cookie refresh)

    Args:
        subfolder: Subfolder path to save file to (optional)
    """
    try:
        if mirror_type == 'slow_download':
            d.logger.debug("Accessing slow download (via cookies)")

            # Try to load cached cookies for this domain (uses current working domain)
            d.load_cached_cookies()

            if hasattr(d, 'status_callback'):
                d.status_callback("Accessing slow download page...")

            try:
                # Try to fetch the slow_download page with cookies
                response = d.session.get(mirror_url, timeout=30)

                # If we get a challenge page (403/503), solve it with FlareSolverr
                if response.status_code in [403, 503]:
                    if not d.flaresolverr_url:
                        d.logger.warning(f"Got {response.status_code} but no FlareSolverr configured")
                        return None

                    d.logger.warning(f"Got {response.status_code}, solving challenge with FlareSolverr...")

                    if hasattr(d, 'status_callback'):
                        d.status_callback("Solving CAPTCHA with FlareSolverr...")

                    # Solve challenge for THIS specific URL
                    success, cookies, html_content = d.solve_with_flaresolverr(mirror_url)

                    if not success:
                        d.logger.error("FlareSolverr failed")
                        return None

                    if hasattr(d, 'status_callback'):
                        d.status_callback("Extracting download link...")

                    download_link = d.parse_download_link_from_html(html_content, md5, mirror_url)
                    if download_link:
                        if hasattr(d, 'status_callback'):
                            d.status_callback("Downloading file...")
                        d.logger.info("Found download URL via FlareSolverr, downloading...")
                        return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

                    # If the direct parse didn't find a link, the slow_download page might
                    # contain the same download panel as the md5 page (Anna's Archive
                    # structure change). Try parsing the download panel from this page.
                    d.logger.debug("Direct parse failed on slow_download page, trying download panel parse...")
                    download_link = _parse_slow_download_panel(d, html_content, md5, mirror_url)
                    if download_link:
                        if hasattr(d, 'status_callback'):
                            d.status_callback("Downloading file...")
                        d.logger.info("Found download URL via download panel parse, downloading...")
                        return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

                    d.logger.warning("Could not find download link")
                    return None

                response.raise_for_status()

                if hasattr(d, 'status_callback'):
                    d.status_callback("Extracting download link...")

                download_link = d.parse_download_link_from_html(response.text, md5, mirror_url)
                if download_link:
                    if hasattr(d, 'status_callback'):
                        d.status_callback("Downloading file...")
                    d.logger.info("Found download URL, downloading...")
                    return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

                # Try parsing the download panel structure
                download_link = _parse_slow_download_panel(d, response.text, md5, mirror_url)
                if download_link:
                    if hasattr(d, 'status_callback'):
                        d.status_callback("Downloading file...")
                    d.logger.info("Found download URL via download panel parse, downloading...")
                    return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

                d.logger.warning("Could not find download link")
                return None

            except Exception as e:
                d.logger.error(f"Error accessing slow_download page: {e}")
                return None
        
        else:  # external_mirror
            d.logger.debug(f"Accessing external mirror: {mirror_url}")

            # Try to load cached cookies for this mirror
            d.load_cached_cookies(domain=mirror_url)

            try:
                response = d.session.get(mirror_url, timeout=30)

                # If 403, refresh cookies and retry
                if response.status_code == 403:
                    if d.flaresolverr_url:
                        d.logger.warning("Got 403 - trying to refresh cookies")

                        # Try to pre-warm new cookies
                        if d.prewarm_cookies():
                            d.logger.info("Retrying with fresh cookies...")
                            # Retry once with fresh cookies
                            response = d.session.get(mirror_url, timeout=30)

                            if response.status_code == 403:
                                d.logger.warning("Still got 403 after cookie refresh, using FlareSolverr for full solve")
                            else:
                                # Success with fresh cookies, continue to parse
                                response.raise_for_status()

                                if hasattr(d, 'status_callback'):
                                    d.status_callback("Extracting download link...")

                                download_link = d.parse_download_link_from_html(response.text, md5, mirror_url)
                                if not download_link:
                                    d.logger.warning("Could not find download link")
                                    return None

                                if hasattr(d, 'status_callback'):
                                    d.status_callback("Downloading file...")

                                return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

                        # If cookie refresh failed or still got 403, use FlareSolverr
                        if hasattr(d, 'status_callback'):
                            d.status_callback("Solving CAPTCHA with FlareSolverr...")
                        success, cookies, html_content = d.solve_with_flaresolverr(mirror_url)

                        if success:
                            if hasattr(d, 'status_callback'):
                                d.status_callback("Extracting download link...")
                            download_link = d.parse_download_link_from_html(html_content, md5, mirror_url)
                            if download_link:
                                if hasattr(d, 'status_callback'):
                                    d.status_callback("Downloading file...")
                                d.logger.info("Found download URL via FlareSolverr, downloading...")
                                return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)
                        return None
                    else:
                        d.logger.warning("Got 403 but FlareSolverr not configured")
                        return None

                response.raise_for_status()

                if hasattr(d, 'status_callback'):
                    d.status_callback("Extracting download link...")

                download_link = d.parse_download_link_from_html(response.text, md5, mirror_url)
                if not download_link:
                    d.logger.warning("Could not find download link")
                    return None

                if hasattr(d, 'status_callback'):
                    d.status_callback("Downloading file...")

                return d.download_direct(download_link, title=title, resume_attempts=resume_attempts, md5=md5, subfolder=subfolder)

            except Exception as e:
                d.logger.error(f"Error accessing external mirror: {e}")
                return None
    
    except Exception as e:
        d.logger.error(f"Error downloading from mirror: {e}")
        return None


def _parse_slow_download_panel(d, html_content, md5, mirror_url):
    """
    Parse a slow_download page that contains a download panel (like the md5 page).

    Anna's Archive changed its structure: the slow_download page now shows the same
    download panel as the /md5/ page instead of directly serving the file. This parser
    looks for download links inside that panel structure.

    It tries multiple strategies:
    1. Find links with the MD5 prefix (direct CDN links)
    2. Find clipboard buttons or spans with download URLs
    3. Find js-download-link elements that point to actual file downloads
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(html_content, 'html.parser')
    md5_prefix = md5[:12]

    # Strategy 1: Look for links in the downloads panel
    panel = soup.find('div', id='md5-panel-downloads')
    if panel:
        # Look for links containing the MD5 that are NOT slow_download or fast_download
        for a in panel.find_all('a', href=True):
            href = a['href']
            if md5_prefix in href.lower():
                # Skip slow_download and fast_download pages — we need the actual file
                if 'slow_download' in href.lower() or 'fast_download' in href.lower():
                    continue
                # Skip navigation links
                if '/md5/' in href.lower():
                    continue

                # Resolve relative URLs
                if not href.startswith('http'):
                    href = urljoin(mirror_url, href)

                d.logger.debug(f"Found download link in panel: {href}")
                return href

    # Strategy 2: Look for js-download-link elements with actual file URLs
    # (not slow_download/fast_download navigation links)
    for a in soup.find_all('a', class_='js-download-link', href=True):
        href = a['href']
        if 'slow_download' in href or 'fast_download' in href:
            continue
        if md5_prefix in href.lower():
            if not href.startswith('http'):
                href = urljoin(mirror_url, href)
            d.logger.debug(f"Found js-download-link: {href}")
            return href

    # Strategy 3: Look for download URLs in any element (clipboard buttons, spans, etc.)
    for btn in soup.find_all('button', onclick=True):
        onclick = btn['onclick']
        import re
        match = re.search(r"writeText\('([^']+)'", onclick)
        if match:
            url = match.group(1)
            if md5_prefix in url:
                d.logger.debug(f"Found clipboard URL in panel page: {url}")
                return url

    for span in soup.find_all('span'):
        text = span.get_text(strip=True)
        if text.startswith("http") and md5_prefix in text:
            d.logger.debug(f"Found raw URL in span on panel page: {text}")
            return text

    # Strategy 4: Look for any link with a file extension that might be a direct download
    from stacks.constants import LEGAL_FILES
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(ext in href.lower() for ext in LEGAL_FILES):
            if not href.startswith('http'):
                href = urljoin(mirror_url, href)
            # Verify it's not just a navigation link
            if md5_prefix in href.lower() or 'cdn' in href.lower():
                d.logger.debug(f"Found file link on panel page: {href}")
                return href

    return None