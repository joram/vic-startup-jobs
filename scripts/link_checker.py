#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
URL_PATTERN = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

def check_link(url: str) -> bool:
    try:
        response = requests.get(url)
        print(f"Checking {url}: {response.status_code}")
        return response.ok
    except requests.exceptions.RequestException as e:

        return False


if __name__ == '__main__':
    with open("README.md") as f:
        for line in f:
            links = re.findall(URL_PATTERN, line)
            for url in links:
                if not check_link(url):
                    print(f"Broken link: {url}")