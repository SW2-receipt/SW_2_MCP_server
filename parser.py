"""
영수증 텍스트에서 구조화된 정보를 추출하는 파서 모듈
"""
import logging
import re
from collections import defaultdict
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

try:
    from konlpy.tag import Okt

    _okt = Okt()
    logger.info("KoNLPy Okt 형태소 분석기를 사용하여 카테고리 분류를 강화합니다.")
except Exception as e:  # pragma: no cover - 환경에 따라 실패 가능
    _okt = None
    error_text = str(e).lower()
    if "java" in error_text or "jvm" in error_text:
        guidance = "Java(JDK) 미설치 또는 JAVA_HOME 미설정으로 인해 KoNLPy Okt 로딩에 실패했습니다."
    else:
        guidance = "KoNLPy 또는 JPype1 설치가 누락되었습니다. `pip install konlpy JPype1` 후 다시 시도하세요."
    logger.warning("⚠️ KoNLPy Okt 초기화 실패: %s", e)
    logger.warning("%s 기본 키워드 기반 분류로 대체합니다.", guidance)


STOPWORDS = {
    "영수증",
    "영수",
    "증",
    "합계",
    "총구매",
    "총",
    "구매",
    "매출",
    "카드",
    "금액",
    "결제",
    "요금",
    "수납",
    "신용",
    "현금",
    "고객",
    "번호",
    "승인",
    "거래",
    "일시",
    "청구",
    "영업",
}


CATEGORY_KEYWORDS = {
    "교육": [
        "학원",
        "교습소",
        "미술",
        "음악",
        "체육",
        "영어",
        "수학",
        "교육",
        "강의",
        "레슨",
        "학습",
        "아트풀",
    ],
    "쇼핑": [
        "롯데",
        "백화점",
        "보석",
        "상품권",
        "마트",
        "편의점",
        "마켓",
        "슈퍼",
        "쇼핑",
        "하나로마트",
        "리치몬트",
        "까르띠에",
        # 편의점 브랜드 추가
        "CU",
        "cu",
        "GS25",
        "gs25",
        "세븐일레븐",
        "7-ELEVEN",
        "7eleven",
        "이마트24",
        "미니스톱",
        "세븐",
        "편의",
    ],
    "의료": [
        "약국",
        "병원",
        "의원",
        "치과",
        "phampay",
        "오팜페이",
        "조제의약품",
        "일반의약품",
    ],
    "교통": [
        "주유",
        "경유",
        "디젤",
        "주유소",
        "주유금액",
        "매출금액",
        "nhvan",
        "농협대전유통",
        "고속도로",
        "톨게이트",
        "주차",
    ],
    "음식": [
        "음식",
        "식당",
        "카페",
        "레스토랑",
        "초밥",
        "회",
        "맛집",
        "치킨",
        "피자",
        "들밥",
        "보리굴비",
        "간장게장",
        "주먹밥",
        "교자",
        "활어회",
        "국민활어회초밥",
        "짜장면",
        "탕수육",
        "커피",
        "음료",
        "빵",
    ],
}


def _tokenize_for_category(text: str) -> List[str]:
    tokens: List[str] = []
    # 정규식 기반 기본 토큰화
    tokens.extend(re.findall(r"[가-힣A-Za-z]+", text))

    if _okt:
        try:
            tokens.extend(_okt.nouns(text))
        except Exception as e:  # pragma: no cover - 환경 의존
            logger.warning("⚠️ KoNLPy 분석 중 오류 발생: %s", e)

    # 소문자로 통일 (영문 대비)
    normalized_tokens = [
        token.lower()
        for token in tokens
        if token and token.lower() not in STOPWORDS
    ]
    return normalized_tokens


def extract_info(text: str, pattern: str, flags: int = 0) -> Optional[str]:
    """
    텍스트와 정규식 패턴을 받아, 매칭되는 첫 번째 그룹을 반환하는 함수
    
    Args:
        text: 검색할 텍스트
        pattern: 정규식 패턴
        flags: re 모듈 플래그 (기본값: 0)
    
    Returns:
        매칭된 첫 번째 그룹 또는 None
    """
    match = re.search(pattern, text, flags)
    if match:
        return match.group(1)  # 괄호()로 묶인 첫 번째 그룹 반환
    return None


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    날짜 형식 변환 함수 (YY/MM/DD -> YYYY-MM-DD)
    
    Args:
        date_str: 날짜 문자열 (YY/MM/DD 또는 YYYY-MM-DD 형식)
    
    Returns:
        정규화된 날짜 문자열 (YYYY-MM-DD) 또는 원본 문자열
    """
    if not date_str:
        return None
    
    try:
        # YY/MM/DD 형식 처리
        if re.match(r'\d{2}[/.-]\d{1,2}[/.-]\d{1,2}', date_str):
            parts = re.split(r'[/.-]', date_str)
            if len(parts) == 3:
                year, month, day = parts
                # YY를 YYYY로 변환 (20XX 가정)
                if len(year) == 2:
                    year_int = int(year)
                    # 2000년 ~ 2049년으로 가정
                    year = f"20{year_int:02d}"
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        # YYYY-MM-DD 형식이면 그대로 반환
        elif re.match(r'\d{4}[/.-]\d{1,2}[/.-]\d{1,2}', date_str):
            parts = re.split(r'[/.-]', date_str)
            if len(parts) == 3:
                year, month, day = parts
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except Exception:
        pass
    
    return date_str  # 변환 실패 시 원본 반환


def categorize_receipt(text: str, store_name: Optional[str]) -> str:
    """
    영수증 내용을 기반으로 카테고리를 분류하는 함수
    
    Args:
        text: OCR로 추출된 영수증 텍스트
        store_name: 추출된 상호명
    
    Returns:
        카테고리 문자열 (우체국, 교육, 쇼핑, 의료, 교통, 음식, 기타)
    """
    combined_text = f"{text} {(store_name or '')}".lower()

    # 우체국 및 택배 관련 키워드는 항상 기타로 분류
    postal_keywords = ['우체국', '우편', '등기', '택배', 'ems', 'epost', '취급국']
    if any(keyword in combined_text for keyword in postal_keywords):
        return "기타"

    text_tokens = _tokenize_for_category(text)
    store_tokens = _tokenize_for_category(store_name or "")

    scores = defaultdict(int)

    # 1단계: 상호명 기반 분류 (가중치 3점)
    # 상호명에서 브랜드명 직접 매칭 (예: "CU 용인마평점" → "CU" 인식)
    if store_name:
        store_name_lower = store_name.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # 상호명에 키워드가 포함되어 있으면 높은 가중치
                if keyword_lower in store_name_lower:
                    scores[category] += 3
                    logger.debug(f"상호명 매칭: {keyword} → {category} (+3점)")

    # 2단계: 본문 및 토큰 기반 분류 (가중치 1점)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_tokens:
                scores[category] += 1
            if keyword_lower in store_tokens:
                scores[category] += 3

    # 3단계: 품목명 기반 힌트 (가중치 0.5점)
    # 품목명에서 음식 관련 키워드가 많이 나오면 "음식" 힌트
    # 하지만 매장이 "편의점"이면 최종적으로 "쇼핑"으로 분류
    item_hints = {
        "음식": ["치킨", "피자", "햄버거", "라면", "김밥", "도시락", "샌드위치", 
                "새우", "짬뽕", "요거트", "우유", "빵", "과자", "음료", "커피"],
        "의료": ["약", "비타민", "영양제", "건강식품"],
    }
    
    # 편의점 브랜드가 감지되면 "쇼핑" 카테고리에 보너스 점수
    convenience_store_brands = ["cu", "gs25", "세븐일레븐", "7-eleven", "이마트24", "미니스톱"]
    if store_name and any(brand in store_name.lower() for brand in convenience_store_brands):
        scores["쇼핑"] += 2
        logger.debug(f"편의점 브랜드 감지: {store_name} → 쇼핑 (+2점)")

    if scores:
        best_category = max(scores.items(), key=lambda item: item[1])
        if best_category[1] > 0:
            logger.debug(f"최종 카테고리: {best_category[0]} (점수: {best_category[1]})")
            return best_category[0]

    # KoNLPy 기반 점수가 없으면 기본 키워드 규칙으로 보정
    if any(keyword in combined_text for keyword in CATEGORY_KEYWORDS["교육"]):
        return "교육"
    if any(keyword in combined_text for keyword in CATEGORY_KEYWORDS["쇼핑"]):
        return "쇼핑"
    if any(keyword in combined_text for keyword in CATEGORY_KEYWORDS["의료"]):
        return "의료"
    if any(keyword in combined_text for keyword in CATEGORY_KEYWORDS["교통"]):
        return "교통"
    if any(keyword in combined_text for keyword in CATEGORY_KEYWORDS["음식"]):
        return "음식"

    return "기타"


def extract_total_price(text: str) -> Optional[str]:
    """
    영수증 텍스트에서 총 금액을 추출하는 함수
    
    Args:
        text: OCR로 추출된 영수증 텍스트
    
    Returns:
        추출된 금액 문자열 (쉼표 제거) 또는 None
    """
    # 금액 패턴: 다양한 형식 지원
    total_price_patterns = [
        r"총\s+구\s+매\s+액\s*[:：]\s*\n\s*([\d,\s]+)",
        r"거래\s+금액\s*[:：]\s*\n?\s*([\d,\s]+)\s*원",
        r"계\s*\n\s*([\d,\s]+)\s*원",
        r"합\s*\n\s*계\s*\n\s*([\d,\s]+)(?:\s*원|$|\n)",
        r"합계\s*[:：]\s*([\d,\s]+)\s*원",
        r"합\s+계\s*[:：]\s*([\d,\s]+)(?:\s*원|$|\n)",
        r"합계\s*[:：]?\s*([\d,\s]+)(?!\d)(?!원)",
        r"계\s*[:：]\s*([\d,\s]+)\s*원",
        r"총구매액\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"총구매액\s*\n\s*([\d,]+)",
        r"신용액\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"주유금액\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"매출금액\s*[:：]?\s*([\d,]+)\s*원",
        r"소계\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"청구금액\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"받을금액\s*[:：]\s*([\d,]+)(?:\s*원|$|\n)",
        r"총요금\s*[:：]?\s*[^(]*?\([^)]*\)\s*([\d,]+)\s*원",
        r"총요금\s*[:：]?\s*([\d,]+)\s*원",
        r"수납요금\s*[:：]?\s*([\d,]+)\s*원",
        r"합계\s+[\d,]+\s*통\s+([\d,]+)\s*원",
        r"총금액\s*[:：]?\s*([\d,]+)\s*원",
        r"(?:합계|총금액|총구매액|총요금|수납요금|신용액|주유금액|매출금액|소계|청구금액|받을금액)\s*[:：]?\s*\n?\s*([\d,]+)(?:\s*원|$|\n)"
    ]
    
    total_price = None
    for pattern in total_price_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            total_price = match.group(1)
            total_price = total_price.replace(',', '').replace(' ', '')
            try:
                price_int = int(total_price)
                if 100 <= price_int <= 10000000000:
                    break
                else:
                    total_price = None
            except:
                total_price = None
    
    # 여전히 찾지 못했으면 줄 단위로 검색
    if not total_price:
        lines = text.split('\n')
        keywords = ['거래 금액', '총구매액', '총 구 매 액', '합계', '합 계', '계', '신용액', '주유금액', '매출금액', '소계', '청구금액', '받을금액', '총요금', '수납요금']
        
        # "합\n계\n4,750,000" 형식 처리
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped == '합' or (len(line_stripped) == 1 and line_stripped == '합'):
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line == '계' or (len(next_line) == 1 and next_line == '계'):
                        for k in range(j + 1, min(j + 6, len(lines))):
                            amount_line = lines[k].strip()
                            match = re.search(r'([\d,\s]+)', amount_line)
                            if match:
                                price_candidate = match.group(1).replace(',', '').replace(' ', '')
                                try:
                                    price_int = int(price_candidate)
                                    if 1000000 <= price_int <= 10000000000:
                                        total_price = price_candidate
                                        break
                                except:
                                    pass
                        if total_price:
                            break
                if total_price:
                    break
        
        # "총\n구\n매\n액" 같은 줄바꿈으로 분리된 경우 처리
        if not total_price:
            # "총", "구", "매", "액"이 연속된 줄에 있는지 확인
            for i in range(len(lines) - 3):
                line1 = lines[i].strip()
                line2 = lines[i + 1].strip() if i + 1 < len(lines) else ""
                line3 = lines[i + 2].strip() if i + 2 < len(lines) else ""
                line4 = lines[i + 3].strip() if i + 3 < len(lines) else ""
                
                # "총", "구", "매", "액" 패턴 찾기
                if (line1 == '총' or '총' in line1) and \
                   (line2 == '구' or '구' in line2) and \
                   (line3 == '매' or '매' in line3) and \
                   (line4 == '액' or '액' in line4 or '액' in line3):
                    # 다음 몇 줄에서 금액 찾기
                    for j in range(i + 2, min(i + 6, len(lines))):
                        amount_line = lines[j].strip()
                        # 숫자만 있는 줄 또는 숫자+쉼표만 있는 줄 찾기
                        amount_match = re.search(r'^[\d,\s]+$', amount_line)
                        if amount_match:
                            price_candidate = amount_line.replace(',', '').replace(' ', '')
                            try:
                                price_int = int(price_candidate)
                                if 100 <= price_int <= 10000000000:
                                    total_price = price_candidate
                                    break
                            except:
                                pass
                    if total_price:
                        break
        
        # "총 구 매 액" 같은 공백 많이 포함된 키워드 처리 (한 줄에 있을 때)
        if not total_price:
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if '총' in line_stripped and '구' in line_stripped and '매' in line_stripped and '액' in line_stripped:
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        match = re.search(r'([\d,\s]+)', next_line)
                        if match:
                            price_candidate = match.group(1).replace(',', '').replace(' ', '')
                            try:
                                price_int = int(price_candidate)
                                if 100 <= price_int <= 10000000000:
                                    total_price = price_candidate
                                    break
                            except:
                                pass
        
        # "결제금액", "결 제 금 액" 같은 줄바꿈 분리 패턴 처리
        if not total_price:
            payment_keywords = ['결제금액', '결 제 금 액', '결제 금액']
            for i in range(len(lines) - 1):
                line_stripped = lines[i].strip()
                # "결", "제", "금", "액"이 연속된 줄에 있는지 확인
                if i + 3 < len(lines):
                    line1 = lines[i].strip()
                    line2 = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    line3 = lines[i + 2].strip() if i + 2 < len(lines) else ""
                    line4 = lines[i + 3].strip() if i + 3 < len(lines) else ""
                    
                    if (line1 == '결' or '결' in line1) and \
                       (line2 == '제' or '제' in line2) and \
                       (line3 == '금' or '금' in line3) and \
                       (line4 == '액' or '액' in line4 or '액' in line3):
                        for j in range(i + 2, min(i + 6, len(lines))):
                            amount_line = lines[j].strip()
                            amount_match = re.search(r'^[\d,\s]+$', amount_line)
                            if amount_match:
                                price_candidate = amount_line.replace(',', '').replace(' ', '')
                                try:
                                    price_int = int(price_candidate)
                                    if 100 <= price_int <= 10000000000:
                                        total_price = price_candidate
                                        break
                                except:
                                    pass
                        if total_price:
                            break
                
                # 한 줄에 있을 때
                for keyword in payment_keywords:
                    if keyword in line_stripped:
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            match = re.search(r'([\d,\s]+)', next_line)
                            if match:
                                price_candidate = match.group(1).replace(',', '').replace(' ', '')
                                try:
                                    price_int = int(price_candidate)
                                    if 100 <= price_int <= 10000000000:
                                        total_price = price_candidate
                                        break
                                except:
                                    pass
                        if total_price:
                            break
                if total_price:
                    break
        
        # 일반 키워드 검색
        if not total_price:
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                for keyword in keywords:
                    if keyword in line_stripped:
                        match = re.search(r'([\d,\s]+)', line_stripped)
                        if match:
                            price_candidate = match.group(1).replace(',', '').replace(' ', '')
                            try:
                                price_int = int(price_candidate)
                                if 100 <= price_int <= 10000000000:
                                    total_price = price_candidate
                                    break
                            except:
                                pass
                        if not total_price and i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            match = re.search(r'([\d,\s]+)', next_line)
                            if match:
                                price_candidate = match.group(1).replace(',', '').replace(' ', '')
                                try:
                                    price_int = int(price_candidate)
                                    if 100 <= price_int <= 10000000000:
                                        total_price = price_candidate
                                        break
                                except:
                                    pass
                    if total_price:
                        break
                if total_price:
                    break
    
    return total_price


def extract_purchase_date(text: str) -> Optional[str]:
    """
    영수증 텍스트에서 구매 날짜를 추출하는 함수
    
    Args:
        text: OCR로 추출된 영수증 텍스트
    
    Returns:
        추출된 날짜 문자열 또는 None
    """
    date_patterns = [
        r"(?:거래일시|거래일|구매일시|구매일|접수일자|접수일|날짜)\s*:?\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})(?:\s+\d{2}[:]\d{2})?",
        r"(?:거래일시|거래일|구매일시|구매일|접수일자|접수일|날짜)\s*:?\s*(\d{2}[-./]\d{1,2}[-./]\d{1,2})(?:\s+\d{2}[:]\d{2})?"
    ]
    
    purchase_date = None
    for pattern in date_patterns:
        purchase_date = extract_info(text, pattern)
        if purchase_date:
            break
    
    if not purchase_date:
        date_pattern = r"(?<!\d)(\d{4}[-./]\d{1,2}[-./]\d{1,2})(?!\d)"
        matches = re.findall(date_pattern, text)
        for match in matches:
            parts = re.split(r'[-./]', match)
            if len(parts) == 3:
                year, month, day = parts
                try:
                    year_int = int(year)
                    if 1900 <= year_int <= 2100:
                        if not (len(year) == 3 and int(parts[0]) < 200):
                            purchase_date = match
                            break
                except:
                    continue
    
    if not purchase_date:
        date_pattern = r"(?:거래일시|거래일|구매일시|구매일|접수일자|접수일)\s*:?\s*(\d{2}[-./]\d{1,2}[-./]\d{1,2})(?:\s+\d{2}[:]\d{2})?"
        purchase_date = extract_info(text, date_pattern)
    
    return purchase_date


def extract_store_name(text: str) -> Optional[str]:
    """
    영수증 텍스트에서 상호명을 추출하는 함수
    (버그 수정: "남시약국" 케이스 추가, "팜 페이" 같은 서비스명 제외)
    
    Args:
        text: OCR로 추출된 영수증 텍스트
    
    Returns:
        추출된 상호명 문자열 또는 None
    """
    store_name = None
    lines = text.split('\n')
    
    # 1. "상호명 / 이름" 형식 먼저 찾기 (예: "남시약국 / 김효경") - 최우선
    for line in lines:
        line_stripped = line.strip()
        if '/' in line_stripped and '상호명' not in line_stripped and '가맹점명' not in line_stripped:
            match = re.search(r'^([가-힣A-Za-z0-9\s]+?)\s*/\s*[가-힣]+$', line_stripped)
            if match:
                candidate = match.group(1).strip()
                # 한글이 포함된 상호명만 선택 (2자 이상)
                if re.match(r'.*[가-힣].*', candidate) and len(candidate) >= 2:
                    exclude_words = ['수량', '금액', '단가', '상품명', '제약사', '거래일시', '조제의약품', '일반의약품', '합계']
                    if candidate not in exclude_words:
                        store_name = candidate
                        break
    
    # 2. "주소" 기반으로 찾기 (1번에서 못 찾은 경우)
    if not store_name:
        address_keywords_city = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '경기']
        address_keywords_unit = ['구', '로', '길', '층', '동', '가', '읍', '면', '리']
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # "가맹점명" 단어가 포함된 줄은 주소로 보지 않음 (버그 수정)
            if '가맹점명' in line_stripped:
                continue
            
            # 주소 줄인지 확인 ("주소:" 또는 지역명 + 단위 포함)
            is_address = (('주소' in line_stripped and ':') or 
                          (any(city in line_stripped for city in address_keywords_city) and
                           any(unit in line_stripped for unit in address_keywords_unit)))
            
            if is_address:
                # 주소 위쪽 몇 줄에서 상호명 찾기 (우선)
                for j in range(max(0, i - 5), i):
                    prev_line = lines[j].strip()
                    
                    # "(주)..." 패턴 먼저 확인
                    if prev_line.startswith('(주)'):
                        store_name = prev_line
                        break
                    
                    # 한글이 포함된 상호명만 선택
                    if re.match(r'.*[가-힣].*', prev_line) and re.match(r'^[가-힣A-Za-z0-9\s\(\)]{2,30}$', prev_line):
                        exclude_words = ['승인', '거래', '금액', '합계', '부가세', '할부', '일시불', '알림', '제출', 
                                        '이성문', '서울', '부산', '강서구', '수', '영', '팜', '페이', 'www']
                        if prev_line not in exclude_words and '팜' not in prev_line and '페이' not in prev_line:
                            store_name = prev_line
                            break
                if store_name:
                    break
                
                # 주소 다음 줄도 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # 다음 줄이 "대표:", "전화:" 등이 아닌 경우만 확인
                    if not ('대표' in next_line or '전화' in next_line or '사업자번호' in next_line):
                        # 한글이 포함된 상호명만 선택
                        if re.match(r'.*[가-힣].*', next_line) and re.match(r'^[가-힣A-Za-z0-9\s]{2,20}$', next_line):
                            exclude_words = ['승인', '거래', '금액', '합계', '부가세', '할부', '일시불', '알림', '제출', 
                                            '이성문', '서울', '부산', '강서구', '팜', '페이']
                            if next_line not in exclude_words and '팜' not in next_line and '페이' not in next_line:
                                store_name = next_line
                                break
    
    # 3. "상호명:" 또는 "가맹점명:" 패턴 시도
    if not store_name:
        store_pattern = r"(?:상호명|가맹점명)\s*:?\s*([가-힣A-Za-z0-9\s\(\)]+?)(?=\n|$|/|사업자|대표|전화)"
        store_name_match = re.search(store_pattern, text, re.IGNORECASE)
        if store_name_match:
            store_name = store_name_match.group(1).strip()
    
    # 4. "(주)..." 패턴 시도 (주소 기반 검색에서 못 찾은 경우)
    if not store_name:
        # "(주)회사명(부가설명)" 형식 포함
        store_pattern = r"\(주\)([가-힣A-Za-z0-9\s]+(?:\([가-힣A-Za-z0-9\s]+\))?)"
        store_name_match = re.search(store_pattern, text, re.IGNORECASE)
        if store_name_match:
            extracted = store_name_match.group(1).strip()
            if len(extracted) >= 2:
                store_name = "(주)" + extracted
    
    # 5. 상단 10줄에서 순수 한글 상호명 찾기 (약국 영수증 등) - "팜 페이" 제외
    if not store_name:
        for i, line in enumerate(lines[:10]):
            line_stripped = line.strip()
            # 한글이 포함된 2~20자의 상호명 (약국, 마트 등)
            if re.match(r'.*[가-힣].*', line_stripped) and re.match(r'^[가-힣A-Za-z0-9\s]{2,20}$', line_stripped):
                exclude_words = ['승인', '거래', '금액', '합계', '부가세', '할부', '일시불', '알림', '제출', 
                                '이성문', '서울', '부산', '강서구', '수', '영', '단가', '수량', '상품명', 
                                '제약사', '조제의약품', '일반의약품', '팜', '페이', 'www', 'co', 'kr']
                # "팜", "페이"가 포함된 줄 제외
                if line_stripped not in exclude_words and '팜' not in line_stripped and '페이' not in line_stripped:
                    store_name = line_stripped
                    break
    
    # 상호명이 추출되지 않았을 경우 디버깅 정보 출력
    if not store_name:
        print("⚠️ 상호명 추출 실패 - 텍스트 상단 일부:")
        lines_debug = text.split('\n')
        for i_debug, line_debug in enumerate(lines_debug[:20]):  # 상단 20줄만 출력
            print(f"   Line {i_debug}: {line_debug.strip()}")
    
    return store_name


def extract_items(text: str) -> List[Dict[str, Optional[str]]]:
    """
    영수증 텍스트에서 품목명과 개별 가격을 추출하는 함수
    
    Args:
        text: OCR로 추출된 영수증 텍스트
    
    Returns:
        품목 정보 리스트:
        [
            {"name": "품목명", "price": "가격", "quantity": "수량"},
            ...
        ]
    """
    items = []
    lines = text.split('\n')
    
    # 제외할 키워드 (헤더, 합계 등)
    exclude_keywords = [
        '합계', '총구매액', '소계', '부가세', '부 가', '부 가 세', '할부', '일시불', '승인',
        '거래일시', '카드번호', '상호명', '가맹점명', '주소', '전화',
        '품목', '상품명', '금액', '단가', '수량', '계', '총', '합',
        '총 구 매 액', '결제금액', '신용카드', '신 용 카 드', '카드회사', '승인번호',
        '과세물품가액', '증정', 'POS', 'TEL', '사업자등록번호'
    ]
    
    # 지역명 (주소 필터링용)
    region_keywords = [
        '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
        '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
        '용인', '성남', '수원', '안양', '안산', '고양', '부천', '의정부',
        '시', '도', '구', '군', '읍', '면', '동', '로', '길', '번지'
    ]
    
    # 금액 패턴 (숫자 + 원 또는 숫자만) - 개선: 더 유연한 패턴
    price_pattern = r'([\d,]+)\s*원?'
    # 한 줄에서 품목명과 가격을 분리하기 위한 패턴 (품목명 뒤의 숫자)
    price_pattern_inline = r'([\d,]+)\s*(?:원|$|\n)'
    
    # 여러 줄에 걸친 품목 패턴 처리 (품목명\n수량\n가격)
    i = 0
    while i < len(lines):
        line_stripped = lines[i].strip()
        
        # 빈 줄이나 너무 짧은 줄 제외
        if len(line_stripped) < 2:
            i += 1
            continue
        
        # 제외 키워드가 포함된 줄 제외
        if any(keyword in line_stripped for keyword in exclude_keywords):
            i += 1
            continue
        
        # 품목명일 가능성이 있는 줄 (한글이나 영문 포함, 숫자만이 아님)
        # 단, 한 줄에 큰 가격이 포함되어 있으면 한 줄 패턴으로 처리해야 하므로 제외
        # 예: "품목명 3,500원" 같은 경우는 한 줄 패턴으로 처리
        # 단, "연세)복숭아요거트 300" 같은 경우는 작은 숫자(품목명 일부일 수 있음)이므로 여러 줄 패턴으로 처리
        has_price_inline = False
        if re.search(r'[\d,]+', line_stripped):
            # 끝에 큰 금액(1000원 이상)이 있으면 한 줄 패턴
            # 1000원 미만이면 품목명 일부일 가능성이 높음
            price_at_end = re.search(r'\s+([\d,]+)\s*원?\s*$', line_stripped)
            if price_at_end:
                try:
                    price_val = int(price_at_end.group(1).replace(',', '').replace(' ', ''))
                    if price_val >= 1000:  # 1000원 이상이면 가격으로 간주
                        has_price_inline = True
                except:
                    pass
        
        # 여러 줄 패턴으로 처리할지 결정
        # 품목명에 작은 숫자(1000원 미만)가 포함되어 있으면 여러 줄 패턴으로 처리
        # 또는 숫자가 없어도 여러 줄 패턴일 수 있음 (예: "연세스트로베리요거트\n1\n2,500")
        if re.search(r'[가-힣A-Za-z]', line_stripped) and not re.match(r'^[\d,\s원]+$', line_stripped) and not has_price_inline:
            # 다음 줄들이 수량과 가격일 수 있음
            item_name = line_stripped
            quantity = None
            price = None
            
            # 다음 2-5줄 확인 (더 많이 확인)
            for j in range(i + 1, min(i + 6, len(lines))):
                next_line = lines[j].strip()
                
                # 수량 추출 (숫자만, 1-99 범위)
                if not quantity and re.match(r'^\d{1,2}$', next_line):
                    try:
                        qty = int(next_line)
                        if 1 <= qty <= 99:
                            quantity = next_line
                            continue
                    except:
                        pass
                
                # 가격 추출 (숫자 + 쉼표, "원" 포함 가능, 공백 허용)
                if not price:
                    # 패턴 1: 숫자만 있는 줄 (예: "3,500" 또는 "3500" 또는 "3, 500" - 공백 포함)
                    price_match = re.search(r'^([\d,\s]+)$', next_line)
                    if not price_match:
                        # 패턴 2: 숫자 + "원" (예: "3,500원" 또는 "3500원" 또는 "3, 500원")
                        price_match = re.search(r'^([\d,\s]+)\s*원', next_line)
                    if price_match:
                        # 공백 제거 후 쉼표 제거
                        price_str = price_match.group(1).replace(' ', '').replace(',', '')
                        try:
                            price_int = int(price_str)
                            if 100 <= price_int <= 10000000:
                                price = price_str
                                print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity or 1})")
                                # 수량과 가격을 찾았으면 다음 품목으로 이동
                                i = j + 1  # 가격 줄 다음부터 시작
                                break
                        except:
                            pass
                
                # "증정" 같은 키워드면 가격이 0
                if '증정' in next_line or '무료' in next_line:
                    price = "0"
                    i = j + 1
                    break
                
                # 다음 줄이 품목명처럼 보이면
                if re.search(r'[가-힣A-Za-z]', next_line) and not re.match(r'^[\d,\s원]+$', next_line):
                    # 가격을 이미 찾았으면 다음 품목으로 넘어감
                    if price:
                        break
                    else:
                        # 가격을 찾지 못했지만 다음 품목이 나왔으므로, 한 줄 더 확인
                        # 예: "연세스트로베리요거트\n1\n2,500" 같은 경우
                        # 다음 다음 줄이 가격일 수 있음 (수량이 있을 수도 있음)
                        found_price_ahead = False
                        for k in range(j + 1, min(j + 4, len(lines))):
                            check_line = lines[k].strip()
                            # 빈 줄이면 건너뛰기
                            if not check_line:
                                continue
                            # 수량인지 확인
                            if not quantity and re.match(r'^\d{1,2}$', check_line):
                                try:
                                    qty_val = int(check_line)
                                    if 1 <= qty_val <= 99:
                                        quantity = check_line
                                        continue  # 수량이면 다음 줄 확인
                                except:
                                    pass
                            # 가격인지 확인
                            price_match_next = re.search(r'^([\d,\s]+)$', check_line)
                            if price_match_next:
                                price_str_next = price_match_next.group(1).replace(' ', '').replace(',', '')
                                try:
                                    price_int_next = int(price_str_next)
                                    if 100 <= price_int_next <= 10000000:
                                        # 가격을 찾았으므로 현재 품목에 추가하고 다음 품목으로
                                        price = price_str_next
                                        print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity or 1}) [지연 추출]")
                                        i = k + 1  # 가격 줄 다음부터 시작
                                        found_price_ahead = True
                                        break
                                except:
                                    pass
                            # 다음 품목명이 나오면 중단 (단, 가격을 찾지 못했을 때만)
                            if not price and re.search(r'[가-힣A-Za-z]', check_line) and not re.match(r'^[\d,\s원]+$', check_line):
                                # 한 줄 더 확인 (수량이 있을 수 있음)
                                if k + 1 < len(lines):
                                    next_check = lines[k + 1].strip()
                                    price_match_final = re.search(r'^([\d,\s]+)$', next_check)
                                    if price_match_final:
                                        price_str_final = price_match_final.group(1).replace(' ', '').replace(',', '')
                                        try:
                                            price_int_final = int(price_str_final)
                                            if 100 <= price_int_final <= 10000000:
                                                price = price_str_final
                                                print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity or 1}) [지연 추출]")
                                                i = k + 2  # 가격 줄 다음부터 시작
                                                found_price_ahead = True
                                                break
                                        except:
                                            pass
                                break
                        if found_price_ahead:
                            break
                        # 가격을 찾지 못했으면 현재 품목은 건너뜀
                        i += 1
                        break
            
            # 품목명 필터링
            is_address = any(region in item_name for region in region_keywords)
            if is_address and ('로' in item_name or '길' in item_name or '동' in item_name or '구' in item_name):
                i += 1
                continue
            
            # 품목명 끝에 붙은 숫자 제거 (예: "WOW새우진짬뽕0" -> "WOW새우진짬뽕")
            if item_name and re.search(r'[가-힣A-Za-z]', item_name):
                item_name = re.sub(r'(\d+)$', '', item_name).strip()
            
            # 품목명과 가격이 모두 있으면 추가
            if price and len(item_name) > 1:
                items.append({
                    "name": item_name,
                    "price": price,
                    "quantity": quantity
                })
                print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity or 1})")
            # 가격을 찾지 못했으면 i만 증가 (다음 줄로)
            i += 1
            continue
        
        # 기존 로직: 한 줄에 품목명과 가격이 함께 있는 경우
        # 패턴 개선: "품목명 3,500원" 또는 "품목명 3500" 또는 "품목명 3, 500" 형식
        # 오른쪽 끝에서 가격 찾기 (품목명 뒤의 마지막 숫자 패턴)
        # 단, 작은 숫자(1000원 미만)는 품목명 일부일 수 있으므로 제외
        price_match = None
        # 패턴 1: 끝에 "원"이 있는 경우 (공백 포함 가능: "3, 500원")
        price_match = re.search(r'([\d,\s]+)\s*원\s*$', line_stripped)
        if not price_match:
            # 패턴 2: 끝에 숫자만 있는 경우 (공백으로 구분, 공백 포함 가능: "3, 500")
            price_match = re.search(r'\s+([\d,\s]+)\s*$', line_stripped)
        if not price_match:
            # 패턴 3: 기존 패턴 (어디든 숫자, 공백 포함 가능)
            price_match = re.search(r'([\d,\s]+)\s*원?', line_stripped)
        
        if price_match:
            # 공백 제거 후 쉼표 제거
            price = price_match.group(1).replace(' ', '').replace(',', '').strip()
            
            # 금액이 너무 작거나 크면 제외 (헤더나 오류 가능성)
            # 1000원 미만이면 품목명 일부일 가능성이 높으므로 여러 줄 패턴으로 처리해야 함
            try:
                price_int = int(price)
                if price_int < 1000 or price_int > 10000000:
                    # 숫자만 있는 줄이면 여러 줄 패턴의 가격일 수 있으므로 건너뛰기
                    # 예: "2,500" 같은 경우는 앞의 품목명과 연결되어야 함
                    i += 1
                    continue
            except:
                i += 1
                continue
            
            # 품목명 추출 (금액 앞의 텍스트)
            item_name = line_stripped[:price_match.start()].strip()
            
            # 품목명이 비어있으면 여러 줄 패턴의 가격일 수 있음
            # 예: "2,500" 같은 경우는 앞의 품목명과 연결되어야 함
            if len(item_name) < 1:
                i += 1
                continue
            
            # 품목명 끝에 작은 숫자 제거 (예: "연세)복숭아요거트 300" -> "연세)복숭아요거트")
            # 단, 숫자가 1000 이상이면 가격일 수 있으므로 제거하지 않음
            if item_name:
                # 끝에 붙은 작은 숫자(1000 미만) 제거
                small_num_match = re.search(r'\s+(\d{1,3})\s*$', item_name)
                if small_num_match:
                    num_val = int(small_num_match.group(1))
                    if num_val < 1000:  # 1000 미만이면 품목명 일부로 간주하고 제거
                        item_name = item_name[:small_num_match.start()].strip()
            
            # 품목명이 비어있거나 너무 짧으면 제외
            if len(item_name) < 1:
                i += 1
                continue
            
            # 숫자만 있는 줄 제외 (금액 줄일 수 있음)
            if re.match(r'^[\d,\s원]+$', item_name):
                # 숫자만 있는 줄이면 품목명이 없으므로 여러 줄 패턴으로 처리해야 할 수도 있음
                # 하지만 이미 한 줄 패턴으로 처리했으므로 건너뜀
                i += 1
                continue
            
            # 제외 키워드가 포함된 줄 제외 (한 줄 패턴에서도)
            if any(keyword in item_name for keyword in exclude_keywords):
                i += 1
                continue
            
            # 주소 패턴 제외 (지역명 + 도로명이 포함된 경우)
            is_address = any(region in item_name for region in region_keywords)
            if is_address and ('로' in item_name or '길' in item_name or '동' in item_name or '구' in item_name):
                i += 1
                continue
            
            # 전화번호 패턴 제외 (TEL:, 전화: 등과 함께 숫자)
            if re.search(r'(?:TEL|전화|tel|Tel)[\s:]*\d', line_stripped, re.IGNORECASE):
                i += 1
                continue
            
            # 사업자번호 패턴 제외
            if re.search(r'사업자등록번호|사업자\s*번호', line_stripped):
                i += 1
                continue
            
            # 카드번호 패턴 제외
            if re.search(r'카드번호|카드\s*번호', line_stripped):
                i += 1
                continue
            
            # 주소에 특수문자(괄호) 포함 시 제외
            if '(' in item_name and any(region in item_name for region in region_keywords):
                i += 1
                continue
            
            # 수량 추출 시도 (품목명과 금액 사이에 숫자가 있는 경우)
            quantity = None
            name_price_part = item_name
            quantity_match = re.search(r'(\d+)\s*(?:개|EA|ea|장|병|팩)', item_name)
            if quantity_match:
                quantity = quantity_match.group(1)
                name_price_part = item_name[:quantity_match.start()].strip()
            
            # 최종 품목명 (수량 제거 후)
            item_name_clean = name_price_part
            
            # 품목명 끝에 붙은 숫자 제거 (예: "WOW새우진짬뽕0" -> "WOW새우진짬뽕")
            # 단, 품목명이 숫자로 끝나는 경우에만 제거 (한글/영문이 포함된 경우)
            if re.search(r'[가-힣A-Za-z]', item_name_clean):
                # 끝에 붙은 숫자 패턴 제거 (예: "품목명0", "품목명123" 등)
                item_name_clean = re.sub(r'(\d+)$', '', item_name_clean).strip()
            
            # 품목명이 비어있으면 다음 줄로
            if len(item_name_clean) < 1:
                i += 1
                continue
            
            # 중복 체크 (같은 이름과 가격이면 제외)
            is_duplicate = False
            for existing_item in items:
                if existing_item.get("name") == item_name_clean and existing_item.get("price") == price:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                items.append({
                    "name": item_name_clean,
                    "price": price,
                    "quantity": quantity
                })
                print(f"[품목 추출] {item_name_clean} - {price}원 (수량: {quantity or 1})")
        
        i += 1
    
    print(f"[품목 추출 완료] 총 {len(items)}개 품목")
    return items


def parse_receipt(text: str) -> Dict[str, Optional[str]]:
    """
    영수증 텍스트에서 구조화된 정보를 모두 추출하는 메인 함수
    
    Args:
        text: OCR로 추출된 영수증 텍스트
    
    Returns:
        추출된 정보를 담은 딕셔너리:
        {
            "total_price": 총 금액 (문자열),
            "purchase_date": 구매 날짜 (원본 형식),
            "normalized_date": 정규화된 날짜 (YYYY-MM-DD),
            "store_name": 상호명,
            "items": 품목 리스트 (리스트)
        }
    """
    total_price = extract_total_price(text)
    purchase_date = extract_purchase_date(text)
    normalized_date = normalize_date(purchase_date)
    store_name = extract_store_name(text)
    items = extract_items(text)
    
    return {
        "total_price": total_price,
        "purchase_date": purchase_date,
        "normalized_date": normalized_date,
        "store_name": store_name,
        "items": items
    }
