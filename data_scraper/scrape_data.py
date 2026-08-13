import csv
import time
import re
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_CSV_PATH = os.path.join(DATA_DIR, "product_reviews.csv")
os.makedirs(DATA_DIR, exist_ok=True)

def get_chrome_major_version():
    """Detect installed Chrome major version to prevent ChromeDriver version mismatch."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split(".")[0])
    except Exception:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}")
            version, _ = winreg.QueryValueEx(key, "pv")
            return int(version.split(".")[0])
        except Exception:
            return None

def get_top_reviews(driver, product_url, count=2):
    if not product_url.startswith("http"):
        return "No reviews found"

    reviews_url = product_url.replace("/p/", "/product-reviews/")

    try:
        driver.get(reviews_url)
        time.sleep(3)
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
            time.sleep(0.5)
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")
        review_blocks = soup.select("div.fWi7J_, div.Z11P_d, div.t-ZTKy, div.cPHRSc, p._2-N2g5, div._27M-vq, div._16Pblm, div.col-12-12")
        
        seen = set()
        reviews = []

        for block in review_blocks:
            text = block.get_text(separator=" ", strip=True)
            # Exclude header summaries or navigation bars
            if len(text) > 20 and text not in seen and not any(skip in text.lower() for skip in ["overall sound quality", "ratings and", "most helpful", "keyboard_arrow"]):
                reviews.append(text)
                seen.add(text)
            if len(reviews) >= count:
                break

        # Fallback if dedicated selectors missed
        if not reviews:
            for tag in soup.find_all(['div', 'p', 'span']):
                txt = tag.get_text(separator=" ", strip=True)
                if 25 < len(txt) < 400 and not any(skip in txt.lower() for skip in ["flipkart", "ratings", "reviews", "certified buyer", "helpful"]):
                    if txt not in seen:
                        reviews.append(txt)
                        seen.add(txt)
                if len(reviews) >= count:
                    break
    except Exception:
        reviews = []

    return " || ".join(reviews) if reviews else "No reviews found"

def scrape_flipkart_products(query, max_products=1, review_count=2):
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    chrome_version = get_chrome_major_version()
    driver = uc.Chrome(options=options, version_main=chrome_version) if chrome_version else uc.Chrome(options=options)
    search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
    driver.get(search_url)
    time.sleep(4)

    try:
        driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
    except Exception:
        pass

    for _ in range(2):
        ActionChains(driver).send_keys(Keys.END).perform()
        time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("div[data-id]")
    products = []
    badges = {"bestseller", "top discount", "trending", "featured", "sponsored"}

    for item in items:
        if len(products) >= max_products:
            break

        # 1. Product Link & ID
        link_el = item.select_one("a[href*='/p/'], a[href*='pid=']")
        if not link_el:
            continue
        href = link_el.get("href", "")
        product_link = href if href.startswith("http") else "https://www.flipkart.com" + href

        id_match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href) or re.findall(r"pid=([0-9A-Za-z]+)", href)
        product_id = id_match[0] if id_match else "N/A"

        # 2. Product Title (multi-selector with badge filter)
        title = ""
        title_candidates = item.select("a.wPMLyi, a.CGtFDu, a[title], div.KzDlHZ, div._4rR01T, a._1fQflY, a.GnxRXv, a.WP4Gry, div._2Wk-1T, a.IRwfWa, a.rP1x41")
        for cand in title_candidates:
            t = cand.get_text(strip=True)
            if t and t.lower() not in badges and len(t) > 3:
                title = t
                break

        if not title:
            img_el = item.select_one("img[alt]")
            if img_el and img_el.get("alt"):
                t = img_el["alt"].strip()
                if t.lower() not in badges:
                    title = t

        if not title:
            continue

        # 3. Price
        price_el = item.select_one("div.Nx9bqj, div._30jeq3, div._1vC4OE, div.D554sg, div.Ds9405")
        if price_el:
            price = price_el.get_text(strip=True)
        else:
            price_match = re.search(r"₹[\d,]+", item.get_text())
            price = price_match.group(0) if price_match else "N/A"

        # 4. Rating
        rating = "N/A"
        rating_el = item.select_one("div.XQDdHH, div._3LWZlK, div._5O2W_D, span._1l43rN, div._31R2Bq")
        if rating_el:
            rating = rating_el.get_text(strip=True)
        else:
            m = re.search(r"\b([1-5]\.\d)\b", item.get_text())
            if m:
                rating = m.group(1)

        # 5. Total Reviews
        total_reviews = "N/A"
        rev_el = item.select_one("span.Wphh3N, span._2_R_ns, span.CLR1Mr, span._385yR7")
        if rev_el:
            total_reviews = rev_el.get_text(strip=True)
        else:
            m = re.search(r"\([\d,]+\)|\b[\d,]+\s*(?:Ratings|Reviews)", item.get_text())
            if m:
                total_reviews = m.group(0)

        # 6. Top Reviews
        top_reviews = get_top_reviews(driver, product_link, count=review_count) if "flipkart.com" in product_link else "Invalid product URL"

        # Fallback rating from top_reviews if search card rating was missing
        if rating == "N/A" and top_reviews:
            r_match = re.search(r"\b([1-5]\.\d)\b", top_reviews)
            if r_match:
                rating = r_match.group(1)

        products.append([product_id, title, rating, total_reviews, price, top_reviews])

    driver.quit()
    return products

def save_to_csv(data, filename=DEFAULT_CSV_PATH):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
        
        cleaned_data = []
        for row in data:
            if len(row) == 6:
                pid, ptitle, prating, prevs, pprice, ptop = row
                # Strip parentheses so Excel does not convert "(1,780)" into a negative number "-1780"
                prevs_clean = re.sub(r"[()]", "", str(prevs)).strip()
                # Replace inner newlines with spaces so Excel keeps each product on a single row
                ptop_clean = re.sub(r"[\r\n]+", " ", str(ptop)).strip()
                cleaned_data.append([pid, ptitle, prating, prevs_clean, pprice, ptop_clean])
            else:
                cleaned_data.append(row)

        writer.writerows(cleaned_data)

def run_scrape_workflow(search_queries, max_products=1, review_count=2):
    """
    Orchestrate scraping across queries, deduplicate products against existing CSV, and save output CSV.
    """
    final_data = []
    for query in search_queries:
        results = scrape_flipkart_products(query, max_products=max_products, review_count=review_count)
        final_data.extend(results)

    existing_titles = set()
    if os.path.exists(DEFAULT_CSV_PATH) and os.path.getsize(DEFAULT_CSV_PATH) > 0:
        try:
            with open(DEFAULT_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("product_title"):
                        existing_titles.add(row.get("product_title"))
        except Exception:
            pass

    unique_products = {}
    for row in final_data:
        if len(row) > 1 and row[1] not in unique_products and row[1] not in existing_titles:
            unique_products[row[1]] = row

    scraped_list = list(unique_products.values())
    if scraped_list:
        save_to_csv(scraped_list, DEFAULT_CSV_PATH)
    return scraped_list


