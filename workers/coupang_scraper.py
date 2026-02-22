import argparse
import time
from coupang.selenium_scraper import CoupangSeleniumScraper
from coupang.enums import FilterType

def run(keyword, filter_name, max_page, headless):
    # 1. 문자열로 받은 필터 이름을 Enum 타입으로 변환
    try:
        filter_type : str = FilterType[filter_name.upper()].value
        
    except KeyError:
        print(f"❌ 지원하지 않는 필터입니다: {filter_name}")
        print(f"✅ 가능한 필터: {[f.name for f in FilterType]}")
        return

    print(f"🚀 스크래핑 시작: 키워드='{keyword}', 필터='{filter_type}', 페이지={max_page}")

    # 2. 스크래퍼 초기화 및 실행
    scraper = CoupangSeleniumScraper(
        keyword=keyword, 
        filter_type=filter_type,
        max_page=max_page,
        headless=headless
    )
    
    scraper.scrape()

    # 3. 결과 저장
    today = time.strftime("%Y%m%d")
    folder = f"results/{keyword.replace('+', '_')}" # 폴더명에 + 기호 방지
    filename = f"coupang_{keyword}_{today}.csv"
    
    scraper.save_to_csv(folder_path=folder, filename=filename)
    print(f"✨ 저장 완료: {folder}/{filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="쿠팡 스크래퍼 통합 실행 도구")
    
    # 필수 인자
    parser.add_argument("-k", "--keyword", required=True, help="검색 키워드 (예: wpi, 크레아틴)")
    
    # 선택 인자 (기본값 설정)
    parser.add_argument("-f", "--filter", default="ROCKET", 
                        help="필터 타입 (ROCKET, COUPANG_GLOBAL 등 / 기본값: ROCKET)")
    parser.add_argument("-p", "--pages", type=int, default=1, 
                        help="스크래핑할 최대 페이지 수 (기본값: 1)")
    parser.add_argument("--headless", action="store_true", 
                        help="브라우저 창을 띄우지 않고 실행")

    args = parser.parse_args()

    run(
        keyword=args.keyword, 
        filter_name=args.filter, 
        max_page=args.pages, 
        headless=args.headless
    )