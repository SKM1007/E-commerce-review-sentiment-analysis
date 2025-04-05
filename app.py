from flask import Flask, request, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from nlp_analyzer import SentimentAnalyzer
import time

app = Flask(__name__)
analyzer = SentimentAnalyzer()

def scrape_amazon_reviews(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(3)

        # Scroll to load reviews
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):  # Limited scrolls to avoid infinite loops
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        soup = BeautifulSoup(driver.page_source, "lxml")
        
        reviews = [review.get_text(strip=True) for review in soup.select("span[data-hook='review-body']")]
        product_name = soup.find("span", {"id": "productTitle"})
        product_name = product_name.get_text(strip=True) if product_name else "Unknown Product"
        product_image = soup.find("img", {"id": "landingImage"})
        product_image = product_image.get("src") if product_image else None
        product_rating = soup.find("span", {"class": "a-icon-alt"})
        product_rating = product_rating.get_text(strip=True) if product_rating else "No Rating"

        return reviews, product_name, product_image, product_rating

    except Exception as e:
        print(f"Error during scraping: {e}")
        return [], "Unknown Product", None, "No Rating"
    finally:
        driver.quit()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        if not url.startswith(("https://www.amazon.in", "https://www.amazon.com")):
            return render_template("index.html", error="Please enter a valid Amazon URL")
        
        reviews, product_name, product_image, product_rating = scrape_amazon_reviews(url)
        if not reviews:
            return render_template("index.html", error="No reviews found")
        
        analyzed_reviews = analyzer.analyze_reviews(reviews)
        
        # Initialize counts properly
        counts = {
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        for review in analyzed_reviews:
            counts[review['sentiment']] += 1
            
        return render_template(
            "results.html",
            product_name=product_name,
            product_image=product_image,
            product_rating=product_rating,
            reviews=analyzed_reviews,
            counts=counts,
            total_reviews=len(reviews)
        )
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
