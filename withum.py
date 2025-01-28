import re
from typing import Literal

import pandas as pd
import requests

from scraper_utils import check_months


class Withum:
    def __init__(self):
        self.url = "https://www.withum.com/resources/?category_filter=71,63,84,73"
        self.api_url = "https://www.withum.com/wp-json/wp/v2/posts?_embed=true&page={}&per_page=20&_fields=author,id,excerpt,title,link,featured_media,_links,_embedded,post_authors&tax_relation=AND&category_filter=71,63,84,73"
        self.search_url = "https://www.withum.com/wp-json/wp/v2/posts?_embed=true&page=1&per_page=6&_fields=author%2Cid%2Cexcerpt%2Ctitle%2Clink%2Cfeatured_media%2C_links%2C_embedded%2Cpost_authors&tax_relation=AND&category_filter=71%2C63%2C84%2C73&s_filter=finance"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

    def get_posts(self, fetch):
        posts, count = [], 0
        page = 1

        while True:
            response = self.session.get(self.api_url.format(page))

            if response.status_code != 200:
                return posts
            df = self.make_df(response)
            posts.append(df)
            count += len(df)

            if fetch == "first":
                break
            elif fetch == "all":
                if not len(df):
                    break
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(df, fetch):
                    break
            else:
                break
        page += 1
        return posts

    def make_df(self, response):
        posts = []
        for post in response.json():
            posts.append({"title": post["title"]["rendered"], "link": post["link"], "date": post["_embedded"]["wp:featuredmedia"][0]["date"]})

        df = pd.DataFrame(posts)
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%dT%H:%M:%S")
        return df

    def execute(self, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        posts = self.get_posts(fetch)
        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
