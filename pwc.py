import re
from typing import Literal

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import check_months, clean


class PWC:
    def __init__(self):
        self.scraper = AsyncScraper(headless=False)
        self.urls = [
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&q=In%20brief&sp_k=us&rows={}&sort=pwcSortDate_dt%20desc&fq=pwcContentType_s%3A(%22In%20brief%22)&pwcSearchType=curated&_cookie=false",
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&rows={}&q=In%20depth&disp=Indepth&sp_k=us&pwcSearchType=main&_cookie=false",
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&q=In%20the%20loop&sp_k=us&rows={}&sort=pwcSortDate_dt%20desc&fq=pwcContentType_s%3A(%22In%20the%20loop%22)&pwcSearchType=curated&_cookie=false",
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&q=News&sp_k=us&rows={}&sort=pwcSortDate_dt%20desc&fq=pwcContentType_s%3A(%22News%22)&pwcSearchType=curated&_cookie=false",
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&q=PwC%20comment%20letter&sp_k=us&rows={}&sort=pwcSortDate_dt%20desc&fq=pwcContentType_s%3A(%22PwC%20comment%20letter%22)&fq=source_s%3A(%22PwC%22)&pwcSearchType=curated&_cookie=false",
            "https://viewpoint.pwc.com/bin/pwc-madison/vp-search?locale=en_us&start={}&q=%22accounting%20weekly%20news%22&sp_k=us&rows={}&fq=pwcContentType_s%3A(%22Newsletter%22)&pwcSearchType=main&_cookie=false",
        ]

    async def get_pwc_table(self, content):
        soup = BeautifulSoup(content, "html.parser")
        a = soup.select("div.condensed-cards div.columns")
        d = []
        for article in a:
            title = clean(article.find("div", {"class": "module-heading"}))
            date = clean(article.find("div", {"class": "date"}))
            ref = clean(article.find("div", {"class": "pwc-col"}))
            link = article.find("a")
            link = link.get("href") if link else None

            d.append({"title": title, "date": date, "ref": ref, "link": link})
        return d

    def get_posts(self, url, fetch):
        start, rows = 0, 20
        posts, count = [], 0
        while True:
            response = requests.get(url.format(start, rows))
            if response.status_code != 200:
                return None
            response = response.json()["response"]
            df = self.make_df(response)
            posts.append(df)
            count += len(df)

            if fetch == "first":
                break
            elif fetch == "all":
                if count >= response["numFound"]:
                    break
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(df, fetch):
                    break
            else:
                break

            start += rows
        return posts

    def make_df(self, response):
        data = response["docs"]
        df = pd.DataFrame(data)[["pwcContentId", "pwcContentType", "pwcReleaseDate", "description", "title", "url"]]
        df = df.rename(columns={"pwcReleaseDate": "date"})
        df["date"] = pd.to_datetime(df["date"], format="%d %b %Y")
        return df

    async def scrape_article(self, url):
        pdftext = "A PDF version of the full publication is attached here:"
        content = await self.scraper.scrape(url)
        soup = BeautifulSoup(content, "html.parser")
        div = soup.find("div", {"class": "topic doc-body-content"})
        if not div:
            return None
        textdivs = div.find_all("div")
        text = "\n".join([clean(i) for i in textdivs if pdftext not in i.text])
        return text

    async def execute(self, url=None, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        urls = [url] if url else self.urls
        posts = []
        for url in urls:
            print(f"---{url}", end="---")
            posts.extend(self.get_posts(url, fetch))

        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
