# Grab one discussion thread from  phpBB ®
import re, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

BASE = "https://forum.domain.com/forum/"                    # CHANGE THIS ! Url of forum
TOPIC = urljoin(BASE, "viewtopic.php?t=123456789")          # Thread number
OUTPUT = "discussion.md"                                    # File where to grab discussion

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; ForumArchive/1.0)"
})


def get_soup(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def clean_content(element):
    # Poista käyttöliittymäelementit ja allekirjoitukset.
    for tag in element.select(
        ".signature, .back2top, .post-buttons, "
        ".notice, .responsive-hide"
    ):
        tag.decompose()

    # Säilytä hymiöiden vaihtoehtoiset tekstit.
    for img in element.find_all("img"):
        alt = img.get("alt", "")
        img.replace_with(alt if alt else "")

    # Säilytä linkkien tekstit ja URL-osoitteet.
    for link in element.find_all("a"):
        label = link.get_text(" ", strip=True)
        href = link.get("href", "")

        if label and href:
            absolute_url = urljoin(BASE, href)
            link.replace_with(f"{label} ({absolute_url})")
        elif label:
            link.replace_with(label)
        else:
            link.decompose()

    for br in element.find_all("br"):
        br.replace_with("\n")

    return element.get_text("\n", strip=True)


def find_post_id(post):
    link = post.select_one('a[href*="p="]')
    if not link:
        return None

    href = link.get("href", "")
    query = parse_qs(urlparse(href).query)
    values = query.get("p", [])

    return values[0] if values else href


def extract_author(post):
    selectors = [
        ".author a.username",
        ".author a.username-coloured",
        "a.username",
        "a.username-coloured",
    ]

    for selector in selectors:
        element = post.select_one(selector)
        if element:
            return element.get_text(" ", strip=True)

    return "Tuntematon kirjoittaja"


def extract_time(post):
    # phpBB-foorumeilla aika löytyy tavallisesti author-elementistä
    # tai sen sisältämästä time-elementistä.
    for selector in [
        ".author time",
        "time",
        ".author",
    ]:
        element = post.select_one(selector)
        if element:
            value = element.get("datetime", "")
            if value:
                return value

            value = element.get_text(" ", strip=True)

            # Jos author-elementissä on myös kirjoittajan nimi,
            # poista nimi ajan alusta.
            value = re.sub(
                r"^\s*Kirjoittaja\s+.*?\s+[»›]\s*",
                "",
                value,
                flags=re.IGNORECASE
            )

            value = re.sub(
                r"^\s*.*?\s+[»›]\s*",
                "",
                value
            )

            if value:
                return value

    return "Tuntematon aika"


def extract_title(post):
    # Otsikko on tavallisesti postbody-elementin h3-otsikossa.
    heading = post.select_one(".postbody h3, h3")
    if heading:
        return heading.get_text(" ", strip=True)

    # Jos otsikkoa ei löydy, käytä yleisotsikkoa.
    return "Viesti"


def extract_content(post):
    body = post.select_one(".postbody")
    if not body:
        return None

    content = body.select_one(".content")
    if not content:
        return None

    return clean_content(content)


seen_posts = set()
seen_pages = set()
page_url = TOPIC
page_number = 0

with open(OUTPUT, "w", encoding="utf-8") as out:
    while page_url and page_url not in seen_pages:
        seen_pages.add(page_url)
        page_number += 1

        print(f"Käsitellään sivua {page_number}: {page_url}")

        try:
            soup = get_soup(page_url)
        except requests.RequestException as error:
            print(f"Sivun haku epäonnistui: {error}")
            break

        posts = soup.select("div.post")

        if not posts:
            posts = soup.select("article")

        for post in posts:
            content = extract_content(post)
            if content is None:
                continue

            post_id = find_post_id(post)

            # Estä saman viestin tallentaminen useaan kertaan.
            identity = post_id or (
                extract_author(post),
                extract_title(post),
                content
            )

            if identity in seen_posts:
                continue

            seen_posts.add(identity)

            title = extract_title(post)
            author = extract_author(post)
            date = extract_time(post)

            # Kaikki header-tiedot yhdellä rivillä.
            header = (
                f"## {title} | "
                f"Kirjoittaja: {author} | "
                f"Aika: {date}"
            )

            out.write(header + "\n\n")
            out.write(content.strip() + "\n\n")
            out.write("---\n\n")

        # Etsi seuraavan sivun linkki.
        next_link = soup.select_one(
            'a[rel="next"], li.next a, a[aria-label="Next"]'
        )

        if not next_link:
            for link in soup.select(
                ".pagination a, .action-bar a"
            ):
                label = link.get_text(" ", strip=True).lower()

                if label in (
                    "seuraava", "next", "»", "›", ">"
                ):
                    next_link = link
                    break

        if next_link and next_link.get("href"):
            next_url = urljoin(page_url, next_link["href"])

            if next_url != page_url:
                page_url = next_url
            else:
                page_url = None
        else:
            page_url = None

        time.sleep(1.5)

print()
print(f"Käsiteltyjä sivuja: {page_number}")
print(f"Tallennettuja viestejä: {len(seen_posts)}")
print(f"Tiedosto: {OUTPUT}")
