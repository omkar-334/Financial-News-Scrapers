import re
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import requests


class RSM:
    def __init__(self):
        self.url = "https://rsmus.com/insights/_jcr_content/root/container/container/container_copy/cardlist.list.json"

    def get_posts(self, fetch):
        r = requests.get(self.url)
        if r.status_code != 200:
            return None
        df = pd.DataFrame(r.json()["originalResultsList"])
        df["url"] = "https://rsmus.com" + df["callToActionLink"].apply(lambda x: x["url"])
        df["tags"] = df["displayableTags"].apply(lambda x: [i["title"] for i in x])
        df = df[["title", "formattedDate", "description", "url", "tags"]]
        df = df.rename(columns={"formattedDate": "date"})

        if fetch == "all":
            return df
        elif re.match(r"\b\d{1,2}m\b", fetch):
            df = df.dropna(subset=["date"])
            months = int(fetch[:-1])
            threshold_date = datetime.now() - timedelta(days=months * 30)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df[df["date"] >= threshold_date]
            return df
        else:
            return None

    def execute(self, fetch):
        print(f"---{self.url}", end="---")
        if fetch == "first":
            fetch == "all"
        posts = self.get_posts(fetch)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
