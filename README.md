# script 모음

## 가상환경 세팅
```sh
pyenv install 3.11.7

# 설치 확인
pyenv versions

# 가상환경 생성
pyenv virtualenv 3.11.7 scripts

# 가상환경 적용(activate)
pyenv activate scripts
# 가상환경 비활성화(deactivate)
pyenv deactivate

# 특정 폴더 가상환경 적용 
pyenv local scripts
```

## 개인 모듈
```sh
pip install -e .
```

## 프로젝트 필요 패키지 추출
```sh
# 1. pipreqs 패키지 설치
pip install pipreqs

# 2. 현재 작업 중인 폴더(.)를 기준으로 requirements.txt 생성
pipreqs .
```

## requirements.txt 패키지 설치
```
pip install -r requirements.txt
```


## example
```sh
# 로켓 직구 - wpi
python workers/coupang_scraper.py --keyword="wpi" --filter="COUPANG_GLOBAL" -p="3"

# 로켓 직구 - 크레아틴
python workers/coupang_scraper.py --keyword="크레아틴" --filter="COUPANG_GLOBAL" -p="1"

# 로켓 배송 - 셀렉스 프로핏 wpi
python workers/coupang_scraper.py --keyword="셀렉스+프로핏+wpi" --filter="ROCKET" -p="1"
```