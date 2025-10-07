import pandas as pd
import requests
import re
from bs4 import BeautifulSoup as bs
import os 
import glob
import time
from datetime import datetime

WEBHOOK_URL = "https://anasellll.app.n8n.cloud/webhook/cc3e67da-30b4-4805-a4fd-5c8439bd7b1e" ## Production
base_url = "https://tanmia.ma/appels-doffres/"

# --- Today's date in French format ---
months_fr = ["janvier","février","mars","avril","mai","juin","juillet",
             "août","septembre","octobre","novembre","décembre"]

today = datetime.now()
today_str = f"{today.day} {months_fr[today.month-1]} {today.year}"
print(f"📅 Today is: {today_str}")

# --- Store results ---
results = []

# --- Loop through first 5 pages ---
for page_num in range(1, 6):
    page_url = f"{base_url}{page_num}/"
    print(f"\n🌍 Scraping page {page_num}: {page_url}")

    resp = requests.get(page_url)
    if resp.status_code != 200:
        print("❌ Failed to load page.")
        break

    soup = bs(resp.text, "html.parser")
    articles = soup.find_all("article", class_="elementor-post")

    stop_scraping = False

    for article in articles:
        # --- Get post date ---
        date_tag = article.find("span", class_="elementor-post-date")
        if not date_tag:
            continue
        post_date = date_tag.text.strip()
        print(f"📅 Found post date: {post_date}")

        # --- Stop if the post is not today ---
        if post_date != today_str:
            print(f"🛑 Found post not from today ({post_date}). Stopping workflow.")
            stop_scraping = True
            break

        # --- Get article URL ---
        title_tag = article.find("h3", class_="elementor-post__title")
        if not title_tag or not title_tag.a:
            continue
        article_url = title_tag.a["href"]
        print(f"🔗 Visiting article: {article_url}")

        # --- Visit article page ---
        article_resp = requests.get(article_url)
        if article_resp.status_code != 200:
            continue

        article_soup = bs(article_resp.text, "html.parser")

        # --- Extract title and attachments ---
        title = article_soup.find("h1").text.strip() if article_soup.find("h1") else "Untitled"
        attachments = [a["href"] for a in article_soup.select(".post-attachments a[href]")]

        results.append({
            "Title": title,
            "URL": article_url,
            "Attachments": attachments
        })

    # --- Stop scraping if a post is not from today ---
    if stop_scraping:
        break

# --- Create DataFrame ---
df = pd.DataFrame(results)
print("\n✅ Scraping complete!")


# Loop through each row in the DataFrame
for idx, row in df.iterrows():
    payload = {
        "title": row["Title"],
        "url": row["URL"],
        "attachments": row["Attachments"]
    }

    print(f"\n🚀 Sending row {idx+1}/{len(df)} to n8n...")
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        
        if response.status_code == 200:
            print(f"✅ Row {idx+1} successfully sent and acknowledged by n8n.")
        else:
            print(f"❌ Row {idx+1} failed with status code: {response.status_code}")
            print(response.text)
            time.sleep(2)

    except Exception as e:
        print(f"❌ Error sending row {idx+1}: {e}")
