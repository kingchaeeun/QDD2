from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote
import time

SEARCH_BASE = "https://rollcall.com/factbase/trump/search/?q="

def get_search_results(query, top_k=5):
    encoded_query = quote(query)
    url = SEARCH_BASE + encoded_query

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    wait = WebDriverWait(driver, 30)

    # 🔹 iframe 제거 → 바로 결과 찾기
    wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a[title='View Transcript']")
        )
    )
    time.sleep(1)

    elems = driver.find_elements(By.CSS_SELECTOR, "a[title='View Transcript']")
    links = [
        e.get_attribute("href")
        for e in elems
        if e.get_attribute("href") and "transcript" in e.get_attribute("href")
    ][:top_k]

    driver.quit()
    return links


if __name__ == "__main__":
    query = "trump venezuela 29"
    links = get_search_results(query)

    print("\n=== Top Search Results ===")
    for i, link in enumerate(links, start=1):
        print(f"{i}. {link}")
    if not links:
        print("❌ No results found.")
