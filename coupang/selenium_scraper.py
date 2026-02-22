import os
import csv
import time
import random
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .enums import FilterType
import logging



logging.basicConfig(level=logging.INFO, format='[%(levelname)s][%(asctime)s][%(name)s]: %(message)s')
log = logging.getLogger(__name__)




class CoupangSeleniumScraper:
    def __init__(self, keyword, filter_type=FilterType.ROCKET, max_page=1, headless=True):
        self.keyword = keyword
        self.filter_type = filter_type
        self.max_page = max_page
        self.results = []
        self.base_url = "https://www.coupang.com/np/search?q="
        self.headless = headless    
        

    def _init_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")

        
        driver = uc.Chrome(options=options, use_subprocess=True, headless=self.headless)
        return driver

    def scrape(self):
        driver = self._init_driver()
        log.info(f"[{self.keyword}] 크롤링 시작... (총 {self.max_page}페이지)")
        
        try:
            for page in range(1, self.max_page + 1):
                url = f"{self.base_url}{self.keyword}&filterType={self.filter_type}&page={page}"
                driver.get(url)
                
            
                try:
                    # 상품 리스트가 로드될 때까지 대기 (상품 단위의 li 태그가 나타날 때까지)
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'li[class*="ProductUnit"]'))
                    ) # 최대 30초 대기
                    # 봇 탐지 우회를 위한 랜덤 딜레이 (상품이 로드된 후 추가로 대기)
                    time.sleep(random.uniform(0.5, 1.5))
                except TimeoutException:
                    log.warning(f"[{page}페이지] 상품 로딩 시간 초과. 페이지를 건너뜁니다.")
                    continue
                
                self._parse_html(driver.page_source)
                log.info(f"[{self.keyword}] {page}페이지 완료")
                
                
                
                # 페이지를 넘기기 전 딜레이는 봇 탐지 회피를 목적
                time.sleep(random.uniform(2.0, 4.0))
                
        except Exception as e:
            
            log.error(f"오류 발생: {e}")
            today = time.strftime("%Y%m%d_%H%M%S")
           
        
            if not os.path.exists(f"error_screenshots/{self.keyword}"):
                os.makedirs(f"error_screenshots/{self.keyword}")
            driver.save_screenshot(f"error_screenshots/{self.keyword}/error_{today}.png")
        finally:
            driver.quit()
            
        return self.results
  
    def _parse_html(self, html_source):
        soup = BeautifulSoup(html_source, 'html.parser')
        items = soup.select('li[class*="ProductUnit"]')
        
        for item in items:
            # 1. 상품명 추출
            name_tag = item.select_one('div[class*="productName"]')
            name = name_tag.text.strip() if name_tag else "상품명 없음"
            
            if name == "상품명 없음":
                continue 
                
            # 2. 가격 추출
            price_area = item.select_one('div[class*="PriceArea"]')
            price = "0"
            unit_price_text = "정보 없음"
            
            if price_area:
                # 가격 추출 (예: 70,000원 -> 70000)
                match = re.search(r'([0-9,]+)원', price_area.text)
                if match:
                    price = match.group(1).replace(',', '')
                
                # 추가1: 단위당 가격 추출 (예: (10g당 309원))
                unit_match = re.search(r'\((.*?당\s*[0-9,]+원)\)', price_area.text)
                if unit_match:
                    unit_price_text = unit_match.group(1)

            # 추가2: 품절 여부 확인 ("품절"이라는 글자가 텍스트 내에 있는지 확인)
            is_sold_out = "O" if "품절" in item.text else "X"

            # 추가3: 상품 중량 추출 (상품명에서 kg, g, ml, l 등의 패턴을 찾음)
            weight = "정보 없음"
            # 대소문자 구분 없이 숫자+단위 패턴 검색
            weight_matches = re.findall(r'([0-9.]+\s?(?:kg|g|ml|l|oz|lbs))', name, re.IGNORECASE)
            if weight_matches:
                weight = weight_matches[-1] # 보통 상품명 맨 뒤에 있는 단위가 총 중량입니다.

            # 4. 평점 추출
            rating_tag = item.select_one('div[aria-label]')
            rating = rating_tag['aria-label'] if rating_tag else "0.0"

            # 5. 리뷰 수 추출
            review_count = "0"
            rating_area = item.select_one('div[class*="ProductRating"]')
            if rating_area:
                match = re.search(r'\(([0-9,]+)\)', rating_area.text)
                if match:
                    review_count = match.group(1).replace(',', '')
            
            # 6. 링크 추출
            link_tag = item.select_one('a[href*="/vp/products"]')
            link = f"https://www.coupang.com{link_tag['href']}" if link_tag else ""

            # 추출한 모든 데이터를 결과 리스트에 담습니다.
            self.results.append({
                '상품명': name,
                '가격(원)': int(price) if price.isdigit() else 0,
                '단위당가격': unit_price_text,
                '중량': weight,
                '품절여부': is_sold_out,
                '평점': float(rating) if rating.replace('.', '', 1).isdigit() else 0.0,
                '리뷰수': int(review_count) if review_count.isdigit() else 0,
                '상품링크': link
            })

    def save_to_csv(self, folder_path, filename):
        if not self.results: 
            log.warning("저장할 데이터가 없습니다.")
    
            return
            
        keys = self.results[0].keys()
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(os.path.join(folder_path, filename), 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.results)

        log.info(f"🎉 파일 저장 완료: {os.path.join(folder_path, filename)} (총 {len(self.results)}개 상품)")
        
        
