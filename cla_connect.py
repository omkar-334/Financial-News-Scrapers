import re
import time
from typing import Literal

import pandas as pd
import requests

from scraper_utils import check_months


class ClaConnect:
    def __init__(self):
        self.url = "https://www.claconnect.com/en/resources?pageNum=1"
        self.api_url = "https://www.claconnect.com/webapi/ResourcesApi/ResourceLandingSearch/?pageNum={}&loadAll=false&pageSize=20"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

    def get_posts(self, fetch):
        posts, count = [], 0
        page = 1

        while True:
            time.sleep(5)
            response = self.session.get(self.api_url.format(page))

            if response.status_code != 200:
                return posts
            data = response.json()["data"]

            df = self.make_df(data)
            posts.append(df)
            count += len(df)

            if fetch == "first":
                break
            elif fetch == "all":
                if not data["hasMoreResources"]:
                    break
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(df, fetch):
                    break
            else:
                break
        page += 1
        return posts

    def make_df(self, data):
        df = pd.DataFrame(data["resources"])
        df["url"] = "https://www.claconnect.com" + df["url"]
        df = df.drop(["target", "image"], axis=1)
        df = df.rename(columns={"abstractText": "desc", "type": "category"})
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
        return df

    def execute(self, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        posts = self.get_posts(fetch)
        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
