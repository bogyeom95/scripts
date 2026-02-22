import os
import csv
import time
import random
import re
import subprocess
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
from datetime import datetime
from .enums import FilterType



logging.basicConfig(level=logging.INFO, format='[%(levelname)s][%(asctime)s][%(name)s]: %(message)s')
log = logging.getLogger(__name__)

class CoupangSeleniumScraper:
    def __init__(self, keyword, filter_type=FilterType.ROCKET, max_page=1, headless=False):
        self.keyword = keyword
        self.filter_type = filter_type
        self.max_page = max_page
        self.results = []
        self.headless = headless # 권장사항에 따라 가급적 False 추천
        
    def _init_driver(self):
        options = uc.ChromeOptions()
        
        
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options, version_main=145) # 자신의 크롬 버전에 맞게 수정
        return driver

    def _natural_entrance(self, driver):
        driver.get("https://www.google.com")
        time.sleep(random.uniform(1, 2))
        
        # 구글 검색창에 키워드 입력
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(f"쿠팡 {self.keyword}")
        search_box.send_keys(Keys.ENTER)
        time.sleep(random.uniform(2, 3))
        
        # 검색 결과 중 쿠팡 링크 클릭 (실제로는 바로 URL 이동해도 Referer가 남도록 처리)
        target_url = f"https://www.coupang.com/np/search?q={self.keyword}&filterType={self.filter_type}"
        driver.get(target_url)

    def _human_scroll(self, driver):
        actions = ActionChains(driver)
        scroll_count = random.randint(3, 6)
        
        for i in range(scroll_count):
            if i < scroll_count - 1:
                actions.send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(random.uniform(0.6, 1.2))
            else:
                actions.send_keys(Keys.END).perform()
                time.sleep(random.uniform(1.5, 2.5))

    def _clean_html_and_get_soup(self, driver):
        clean_script = """
            const scripts = document.querySelectorAll('script, iframe, head');
            scripts.forEach(s => s.remove());
        """
        driver.execute_script(clean_script)
        return BeautifulSoup(driver.page_source, 'html.parser')

    def scrape(self):
        driver = self._init_driver()
        try:
            # 1. 자연스러운 접속
            self._natural_entrance(driver)
            
            for page in range(1, self.max_page + 1):
                url = f"https://www.coupang.com/np/search?q={self.keyword}&filterType={self.filter_type}&page={page}"
                if page > 1: driver.get(url)
                
                try:
                    # 상품 로드 대기
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'li[class*="ProductUnit"]'))
                    )
                    
                    # 2. 사람처럼 스크롤 (데이터 로딩 유도)
                    self._human_scroll(driver)
                    
                    # 3. HTML 클리닝 및 파싱
                    soup = self._clean_html_and_get_soup(driver)
                    self._parse_items(soup)
                    
                    log.info(f"[{page}페이지] 완료 (현재 누적 {len(self.results)}개)")
                    time.sleep(random.uniform(3, 5)) # 페이지 간 충분한 휴식
                    
                except TimeoutException:
                    log.warning(f"{page}페이지 로딩 실패. 건너뜁니다.")
                    continue
                    
        except Exception as e:
            log.error(f"오류 발생: {e}")
        finally:
            driver.quit()
        return self.results

    def _parse_items(self, soup):
        """
        기존 로직 + 중량, 단위가격, 할인율, 광고여부, 로켓배송, 품절여부 통합 최적화
        """
        items = soup.select('li[class*="ProductUnit"]')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for rank, item in enumerate(items, 1):
            try:
                # 1. 상품명 추출
                name_tag = item.select_one('div[class*="productName"]')
                if not name_tag: continue
                name = name_tag.text.strip()

                # 2. 가격 관련 정보 (현재가, 원가, 할인율)
                price_area = item.select_one('div[class*="PriceArea"]')
                price = 0
                base_price = 0
                discount_rate = "0%"
                
                if price_area:
                    # 현재가 추출
                    price_tag = price_area.select_one('strong.value')
                    if price_tag:
                        price = int(price_tag.text.replace(',', ''))
                    
                    # 원가(할인 전 가격) 추출
                    base_price_tag = price_area.select_one('del.base-price')
                    base_price = int(base_price_tag.text.replace(',', '')) if base_price_tag else price
                    
                    # 할인율 추출
                    discount_tag = price_area.select_one('span.discount-percentage')
                    discount_rate = discount_tag.text.strip() if discount_tag else "0%"

                # 3. 단위당 가격 및 중량 (Regex 활용)
                unit_price = "정보 없음"
                if price_area:
                    unit_match = re.search(r'\((.*?당\s*[0-9,]+원)\)', price_area.text)
                    if unit_match:
                        unit_price = unit_match.group(1)

                # 상품명에서 중량/용량 추출 (예: 500g, 1.5L, 10kg 등)
                weight = "정보 없음"
                weight_matches = re.findall(r'([0-9.]+\s?(?:kg|g|ml|l|oz|lbs|매|입))', name, re.IGNORECASE)
                if weight_matches:
                    weight = weight_matches[-1]

                # 4. 배송 및 광고/상태 정보
                # 로켓배송/로켓프레시/제트배송 통합 체크
                is_rocket = "X"
                if item.select_one('span.badge.rocket'): is_rocket = "로켓배송"
                elif item.select_one('span.badge.fresh'): is_rocket = "로켓프레시"
                elif item.select_one('span.badge.jet'): is_rocket = "제트배송"
                
                is_ad = "O" if item.select_one('span.ad-badge') else "X"
                is_sold_out = "O" if "품절" in item.text or item.select_one('.out-of-stock') else "X"

                # 5. 평점 및 리뷰 수
                rating = 0.0
                rating_tag = item.select_one('em.rating')
                if rating_tag:
                    rating = float(rating_tag.text)
                
                review_count = 0
                review_tag = item.select_one('span.rating-total-count')
                if review_tag:
                    count_match = re.search(r'\d+', review_tag.text.replace(',', ''))
                    if count_match:
                        review_count = int(count_match.group())

                # 6. 링크 추출
                link_tag = item.select_one('a[class*="search-product-link"]')

                # 만약 클래스명으로 못 찾았다면, 해당 아이템 내의 첫 번째 a 태그를 시도
                if not link_tag:
                    link_tag = item.find('a', href=True)

                if link_tag and 'href' in link_tag.attrs:
                    raw_href = link_tag['href']
                    # 이미 full URL인 경우와 relative path인 경우 처리
                    if raw_href.startswith('http'):
                        link = raw_href
                    else:
                        # URL에 중복 슬래시 방지
                        link = f"https://www.coupang.com{raw_href}"
                else:
                    link = ""
                # 최종 데이터 저장
                self.results.append({
                    '수집시간': current_time,
                    '검색순위': rank,
                    '상품명': name,
                    '현재가': price,
                    '원가': base_price,
                    '할인율': discount_rate,
                    '단위당가격': unit_price,
                    '중량': weight,
                    '평점': rating,
                    '리뷰수': review_count,
                    '배송타입': is_rocket,
                    '광고여부': is_ad,
                    '품절여부': is_sold_out,
                    '상품링크': link
                })
                
            except Exception as e:
                log.error(f"아이템 파싱 중 건너뜀: {e}")
                continue

    def save_to_csv(self, folder_path, filename):
        if not self.results: return
        os.makedirs(folder_path, exist_ok=True)
        path = os.path.join(folder_path, filename)
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        log.info(f"저장 완료: {path}")
