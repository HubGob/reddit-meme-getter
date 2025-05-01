from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import requests
import time
from urllib.parse import urljoin

# Constants
URL = "https://www.reddit.com/r/memes/"
DOWNLOAD_DIR = 'downloaded_images'
NUM_IMAGES = 10
SCROLL_PAUSE_TIME = 2  # seconds
MAX_WAIT = 15  # seconds for element waits

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Set user-agent to mimic real browser
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def scroll_page(driver, scroll_pause_time=SCROLL_PAUSE_TIME):
    """Scroll page to trigger lazy loading"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):  # Scroll 3 times
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_images(driver, url, max_images=NUM_IMAGES):
    try:
        driver.get(url)
        
        # Wait for initial content to load
        WebDriverWait(driver, MAX_WAIT).until(
            EC.presence_of_element_located((By.TAG_NAME, 'shreddit-post'))
        )
        
        # Scroll to trigger lazy loading
        scroll_page(driver)
        
        # Find all post images (more specific than just 'img' tags)
        posts = driver.find_elements(By.TAG_NAME, 'shreddit-post')[:max_images]
        image_elements = []
        
        for post in posts:
            try:
                # Find the image inside each post
                img = post.find_element(By.CSS_SELECTOR, "img.preview-img.media-lightbox-img")
                
                image_elements.append(img)
                if len(image_elements) >= max_images:
                    break
            except:
                continue
                
        return image_elements
        
    except Exception as e:
        print(f"Error getting images: {e}")
        return []

def download_image(url, filename, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            else:
                ext = 'jpg'  # default
            
            full_path = f"{filename}.{ext}"
            
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
            
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed to download {url}: {e}")
                return False
            time.sleep(1)  # wait before retry

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    driver = setup_driver()
    
    try:
        images = get_images(driver, URL)
        print(f"Found {len(images)} potential images to download")
        
        for i, image in enumerate(images, 1):
            try:
                img_url = image.get_attribute('src')
                if not img_url:
                    print(f"Skipping image {i} - no source")
                    continue
                    
                # Some Reddit images might be in data attributes instead
                if not img_url.startswith(('http:', 'https:')):
                    img_url = image.get_attribute('data-url') or img_url
                
                if not img_url.startswith(('http:', 'https:')):
                    print(f"Skipping image {i} - invalid URL: {img_url}")
                    continue
                
                filename = os.path.join(DOWNLOAD_DIR, f"reddit_meme_{i}")
                if download_image(img_url, filename):
                    print(f"Successfully downloaded image {i}/10")
                else:
                    print(f"Failed to download image {i}")
                    
            except Exception as e:
                print(f"Error processing image {i}: {e}")
                
    finally:
        driver.quit()
        print("WebDriver closed")

if __name__ == "__main__":
    main()