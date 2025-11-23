"""
영수증 텍스트에서 구조화된 정보를 추출하는 파서 모듈
"""
import logging
import os
import re
import sys
from collections import defaultdict
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# KoNLPy는 지연 로딩으로 처리 (서버 시작 시 Java 크래시 방지)
# Python 3.13 이상에서는 KoNLPy/JPype 조합이 불안정하므로 비활성화
_okt = None
_okt_initialized = False
_okt_available = False

def _init_okt():
    """KoNLPy Okt를 지연 초기화하는 함수"""
    global _okt, _okt_initialized, _okt_available
    
    if _okt_initialized:
        return _okt_available
    
    _okt_initialized = True
    
    # 환경 변수로 KoNLPy 비활성화 가능
    if os.environ.get("DISABLE_KONLPY", "").lower() in ("1", "true", "yes"):
        logger.info("ℹ️ 환경 변수 DISABLE_KONLPY로 인해 KoNLPy가 비활성화되었습니다.")
        _okt = None
        _okt_available = False
        return False
    
    # Python 3.13 이상에서는 KoNLPy 비활성화 (Java 크래시 방지)
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 13:
        logger.warning("⚠️ Python 3.13+에서는 KoNLPy가 안정적으로 동작하지 않습니다.")
        logger.warning("   기본 키워드 기반 분류를 사용합니다. (Python 3.11 권장)")
        logger.warning("   KoNLPy를 강제로 사용하려면 환경 변수 DISABLE_KONLPY=0을 설정하세요.")
        _okt = None
        _okt_available = False
        return False
    
    try:
        from konlpy.tag import Okt
        _okt = Okt()
        _okt_available = True
        logger.info("KoNLPy Okt 형태소 분석기를 사용하여 카테고리 분류를 강화합니다.")
    except Exception as e:  # pragma: no cover - 환경에 따라 실패 가능
        _okt = None
        _okt_available = False
        error_text = str(e).lower()
        if "java" in error_text or "jvm" in error_text:
            guidance = "Java(JDK) 미설치 또는 JAVA_HOME 미설정으로 인해 KoNLPy Okt 로딩에 실패했습니다."
        else:
            guidance = "KoNLPy 또는 JPype1 설치가 누락되었습니다. `pip install konlpy JPype1` 후 다시 시도하세요."
        logger.warning("⚠️ KoNLPy Okt 초기화 실패: %s", e)
        logger.warning("%s 기본 키워드 기반 분류로 대체합니다.", guidance)
    
    return _okt_available


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

    # KoNLPy 지연 초기화 및 사용
    if _init_okt() and _okt:
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
        '거래일시', '카드번호', '상호명', '가맹점명', '주소', '전화', '전화번호',
        '품목', '상품명', '금액', '단가', '수량', '계', '총', '합',
        '총 구 매 액', '결제금액', '신용카드', '신 용 카 드', '카드회사', '승인번호',
        '과세물품가액', '증정', 'POS', 'TEL', '사업자등록번호', '사업자',
        '주문번호', '주문일시', '업소명', '대표자', '받을금액', '받은금액',
        '단말기', '카드종류', '가맹번호', '영수증', '주문서', '고객용', '매장식사',
        '신용승인정보', '거래금액', '결제', '승인정보', '공급가액', '부가세액',
        '카드', '주문합계', '결제금액', '내실금액', '내 실 금', '총구매액',
        '신용액', '부가세면세물품가액', '부가세과세물품가액'
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
    
    # 표 형식 영수증 처리 (품명 | 단가 | 수량 | 금액)
    # 먼저 "품명", "단가", "수량", "금액" 헤더가 있는지 확인
    # 한 줄에 모두 있거나, 연속된 몇 줄에 나뉘어 있을 수 있음
    table_format_detected = False
    table_start_idx = -1
    
    # 패턴 1: 한 줄에 모든 헤더가 있는 경우
    for idx, line in enumerate(lines):
        line_lower = line.strip().replace(' ', '').replace('|', '').replace(':', '').replace('(', '').replace(')', '')
        # "품명" 또는 "상품"이 있고, "단가", "수량", "금액" 중 하나라도 있으면 표 형식
        if ('품명' in line_lower or '상품' in line_lower) and ('단가' in line_lower or '수량' in line_lower or '금액' in line_lower):
            table_format_detected = True
            table_start_idx = idx
            print(f"[디버그] 표 형식 감지 (한 줄): Line {idx} - {line.strip()}")
            break
    
    # 패턴 2: 여러 줄에 헤더가 나뉘어 있는 경우 (예: Line 11: '품명', Line 12: '단가', Line 13: '수량', Line 14: '금액')
    if not table_format_detected:
        for idx in range(len(lines) - 3):
            # 연속된 4줄에서 "품명"/"상품", "단가"/"할인", "수량", "금액"이 있는지 확인
            next_lines = [lines[idx + i].strip().replace(' ', '').replace('|', '').replace(':', '').replace('(', '').replace(')', '') for i in range(4)]
            has_pumyeong = any('품명' in line or '상품' in line for line in next_lines)
            has_danga = any('단가' in line or '할인' in line for line in next_lines)  # "할인"도 허용
            has_suryang = any('수량' in line for line in next_lines)
            has_geumak = any('금액' in line for line in next_lines)
            
            # "품명"/"상품", "수량", "금액"이 있으면 표 형식 (단가는 선택적)
            if has_pumyeong and has_suryang and has_geumak:
                table_format_detected = True
                # 헤더가 끝나는 줄 다음부터 시작 (마지막 헤더 줄 다음)
                table_start_idx = idx + 4
                print(f"[디버그] 표 형식 감지 (여러 줄): Line {idx}-{idx+3} - 헤더 발견")
                print(f"[디버그] 표 파싱 시작 위치: Line {table_start_idx}")
                break
    
    # 표 형식이 감지된 경우 표 형식으로 파싱
    if table_format_detected and table_start_idx >= 0:
        print(f"[디버그] 표 형식 파싱 시작 (Line {table_start_idx}부터)")
        # 헤더 다음 줄부터 파싱 시작
        idx = table_start_idx
        while idx < len(lines):
            line = lines[idx].strip()
            if len(line) < 2:
                idx += 1
                continue
            
            # 제외 키워드 확인 (합계, 소계 등이 나오면 종료)
            line_no_spaces = line.replace(' ', '').replace(':', '')
            if any(keyword.replace(' ', '') in line_no_spaces for keyword in ['합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액']):
                break
            
            # 품명 확인 (001 P, 002 P 등으로 시작하는 패턴 우선)
            is_item_name = False
            line_clean = line.strip()
            
            # 제외 키워드 확인 (부가세, 합계 등이 포함된 줄은 품목명이 아님)
            line_no_spaces = line_clean.replace(' ', '').replace(':', '')
            if any(keyword.replace(' ', '') in line_no_spaces for keyword in 
                   ['부가세', '과세', '물품가액', '합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액', '금액']):
                idx += 1
                continue
            
            # 품목명 패턴 확인
            # 패턴 1: 001 P, 002 P 등으로 시작하는 경우
            if re.match(r'^\d{3}\s*P', line_clean):
                is_item_name = True
            # 패턴 2: 000001, 000002 등 6자리 숫자로 시작하고 한글이 포함된 경우
            elif re.match(r'^\d{6}\s+[가-힣A-Za-z]', line_clean):
                is_item_name = True
            # 패턴 3: 숫자로 시작하고 한글이 포함된 경우 (일반 패턴)
            elif len(line_clean) >= 2 and re.search(r'[가-힣A-Za-z]', line) and not re.match(r'^[\d,\s원]+$', line):
                # 이름 같은 짧은 한글만 있는 경우 제외 (2-3자 한글, 숫자나 영문 없음)
                # "세 :", "가 :" 같은 패턴도 제외
                if not (re.match(r'^[가-힣]{1,2}\s*[:：]\s*$', line_clean) or 
                       (re.match(r'^[가-힣]{2,3}$', line_clean) and not re.search(r'[0-9A-Za-z]', line_clean))):
                    # 숫자로만 시작하거나 끝나는 경우도 제외 (예: "4079538")
                    if not (re.match(r'^\d+$', line_clean) or (re.match(r'^\d+', line_clean) and len(re.sub(r'^\d+', '', line_clean).strip()) < 2)):
                        is_item_name = True
            
            if is_item_name:
                item_name = line_clean
                print(f"[디버그] 품목명 발견: '{item_name}' (Line {idx})")
                unit_price = None
                quantity = None
                total_price = None
                barcode_found = False
                
                # 다음 몇 줄에서 바코드, 단가, 수량, 금액 찾기
                # 표 형식: 품명 -> 바코드(선택) -> 단가 -> 수량 -> 금액
                j = idx + 1
                found_numbers = []  # (line_idx, num_str, num_val) 튜플 리스트
                next_item_line = None
                
                while j < min(idx + 20, len(lines)):
                    next_line = lines[j].strip()
                    if len(next_line) < 1:
                        j += 1
                        continue
                    
                    # 제외 키워드 확인
                    next_line_no_spaces = next_line.replace(' ', '').replace(':', '')
                    if any(keyword.replace(' ', '') in next_line_no_spaces for keyword in ['합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액', '부가세', '과세', '물품가액']):
                        print(f"[디버그]   제외 키워드 발견, 숫자 수집 중단 (Line {j}): {next_line}")
                        break
                    
                    # 다음 품목명이 나오면 기록하고 중단
                    if re.search(r'[가-힣A-Za-z]', next_line) and not re.match(r'^[\d,\s원]+$', next_line):
                        # 품목명 패턴 확인
                        # 패턴 1: 001 P, 002 P 등으로 시작하는 경우
                        # 패턴 2: 000001, 000002 등 6자리 숫자로 시작하는 경우
                        # 패턴 3: 숫자로 시작하고 한글이 포함된 경우
                        is_next_item = (re.match(r'^\d{3}\s*P', next_line) or 
                                       re.match(r'^\d{6}\s+[가-힣A-Za-z]', next_line) or
                                       (re.match(r'^\d+\s+[가-힣A-Za-z]', next_line) and len(next_line) > 5))
                        
                        if is_next_item:
                            if next_item_line is None:
                                next_item_line = j
                            # 바코드를 찾았으면 바코드 이후 최소 5줄은 더 확인 (바코드 다음에 단가, 수량, 금액이 올 수 있음)
                            if barcode_found:
                                # 바코드 위치 확인
                                barcode_pos = None
                                for check_pos in range(idx + 1, j):
                                    if check_pos < len(lines) and re.match(r'^\d{10,}$', lines[check_pos].strip()):
                                        barcode_pos = check_pos
                                        break
                                if barcode_pos is not None:
                                    # 바코드 이후 5줄 이내에 다음 품목명이 나왔으면, 바코드 이후 숫자를 더 찾기 위해 계속 진행
                                    if j <= barcode_pos + 5:
                                        print(f"[디버그]   바코드(Line {barcode_pos}) 이후 5줄 이내에 다음 품목명 발견, 계속 진행하여 숫자 수집")
                                        j += 1
                                        continue
                                    else:
                                        # 바코드 이후 5줄 이상 지났으면 중단
                                        break
                                else:
                                    break
                            else:
                                # 바코드가 없으면 다음 품목명이 나왔을 때
                                # 품목명 이후 몇 줄 더 확인하여 금액을 찾기
                                # 품목명 이후 8줄 이내에 다음 품목명이 나오면 계속 진행
                                if j <= idx + 8:
                                    print(f"[디버그]   품목명 이후 8줄 이내에 다음 품목명 발견, 금액을 찾기 위해 계속 진행 (Line {j})")
                                    j += 1
                                    continue
                                else:
                                    # 품목명 이후 8줄 이상 지났으면 중단
                                    break
                    
                    # 바코드 확인 (10자리 이상 숫자만)
                    if re.match(r'^\d{10,}$', next_line):
                        barcode_found = True
                        print(f"[디버그]   바코드 발견 (Line {j}): {next_line}")
                        j += 1
                        continue
                    
                    # 숫자만 있는 줄 확인 (쉼표, 점 포함 숫자)
                    # 또는 수량이 "3개"처럼 "개"가 붙은 경우 (OCR 오류로 "1가" 같은 경우도 처리)
                    is_number_line = re.match(r'^[\d,.\s]+$', next_line)  # 점(.)도 포함
                    is_quantity_line = re.match(r'^(\d+)\s*[개가]\s*$', next_line)  # "개" 또는 "가" (OCR 오류)
                    
                    if is_number_line or is_quantity_line:
                        try:
                            if is_quantity_line:
                                # 수량 줄 처리 (예: "3개" -> 3)
                                num_str_clean = is_quantity_line.group(1)
                                num_val = int(num_str_clean)
                                # 수량 범위 확인 (1-99)
                                if 1 <= num_val <= 99:
                                    # 수량으로 기록
                                    if quantity is None:
                                        quantity = num_str_clean
                                        print(f"[디버그]   수량 발견 (Line {j}): {next_line} (값: {num_val})")
                                        j += 1
                                        continue
                            else:
                                # 점(.)을 제거하여 처리 (예: "35.000" -> "35000")
                                num_str_clean = next_line.replace('.', '').replace(',', '').replace(' ', '')
                                if num_str_clean:
                                    num_val = int(num_str_clean)
                                
                                # 이전 줄이나 다음 줄에 제외 키워드가 있는지 확인
                                exclude_context = False
                                # 이전 줄 확인
                                if j > 0:
                                    prev_line = lines[j - 1].strip() if j - 1 < len(lines) else ""
                                    prev_line_no_spaces = prev_line.replace(' ', '').replace(':', '')
                                    if any(keyword.replace(' ', '') in prev_line_no_spaces for keyword in 
                                           ['부가세', '과세', '물품가액', '합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액']):
                                        exclude_context = True
                                        print(f"[디버그]   제외 키워드가 포함된 줄의 숫자 무시 (Line {j}): {next_line} (이전 줄: '{prev_line}')")
                                # 다음 줄 확인
                                if not exclude_context and j + 1 < len(lines):
                                    next_next_line = lines[j + 1].strip()
                                    next_next_line_no_spaces = next_next_line.replace(' ', '').replace(':', '')
                                    if any(keyword.replace(' ', '') in next_next_line_no_spaces for keyword in 
                                           ['부가세', '과세', '물품가액', '합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액']):
                                        exclude_context = True
                                        print(f"[디버그]   제외 키워드가 포함된 줄의 숫자 무시 (Line {j}): {next_line} (다음 줄: '{next_next_line}')")
                                
                                if exclude_context:
                                    j += 1
                                    continue
                                
                                # 표 형식에서는 품목명 바로 다음에 단가가 올 수 있으므로, 이 로직은 적용하지 않음
                                # (표 형식이 아닌 경우에만 이전 품목 금액 필터링 적용)
                                # 표 형식에서는 품목명 다음 줄이 단가일 가능성이 높음
                                # 할인 줄(0 또는 작은 숫자)은 건너뛰기
                                if num_val == 0 or (num_val < 100 and quantity is not None):
                                    print(f"[디버그]   할인 또는 작은 숫자 무시 (Line {j}): {next_line}")
                                    j += 1
                                    continue
                                
                                # 점(.) 처리: 점이 포함된 경우
                                # "5.000" -> 5000 (천 단위 구분자)
                                # "5.00" -> 500 (소수점일 수도 있지만, 영수증에서는 보통 천 단위 구분자)
                                # 하지만 작은 숫자(1000 미만)에서 점이 포함되어 있으면, 점을 제거하고 숫자로 해석
                                # 예: "5.00" -> 500, "5.000" -> 5000
                                num_str_for_display = next_line.replace('.', ',')
                                
                                # 점이 포함된 경우, 점을 제거한 숫자가 1000 미만이면 점을 소수점으로 해석할 수도 있음
                                # 하지만 영수증에서는 보통 천 단위 구분자이므로 그대로 처리
                                found_numbers.append((j, num_str_for_display, num_val))
                                print(f"[디버그]   숫자 발견 (Line {j}): {next_line} -> {num_str_for_display} (값: {num_val})")
                        except:
                            pass
                    
                    j += 1
                
                # 바코드가 있으면 바코드 이후의 숫자만 사용
                barcode_line = None
                if barcode_found:
                    # 바코드가 발견된 줄 번호 찾기 (이미 찾은 바코드 위치 사용)
                    for check_j in range(idx + 1, min(idx + 20, len(lines))):
                        if check_j < len(lines) and re.match(r'^\d{10,}$', lines[check_j].strip()):
                            barcode_line = check_j
                            break
                    if barcode_line is not None:
                        before_filter = len(found_numbers)
                        found_numbers = [(line_idx, num_str, num_val) for line_idx, num_str, num_val in found_numbers if line_idx > barcode_line]
                        print(f"[디버그]   바코드(Line {barcode_line}) 이후 숫자만 사용: {len(found_numbers)}개 (필터링 전: {before_filter}개)")
                        if len(found_numbers) == 0:
                            print(f"[디버그]   경고: 바코드 이후 숫자를 찾지 못했습니다! 바코드 위치: Line {barcode_line}, 품목명: {item_name}")
                            # 바코드 이후 몇 줄 더 확인
                            for debug_j in range(barcode_line + 1, min(barcode_line + 10, len(lines))):
                                if debug_j < len(lines):
                                    print(f"[디버그]     Line {debug_j}: '{lines[debug_j].strip()}'")
                
                # 다음 품목명 이전의 숫자만 사용
                # 단, 바코드가 있는 경우 바코드 이후 숫자는 항상 포함 (바코드 이후 숫자는 현재 품목의 데이터)
                # 바코드가 없는 경우, 다음 품목명 이전 숫자만 사용 (다음 품목명 이후 숫자는 다음 품목의 데이터이므로 제외)
                if next_item_line is not None:
                    if barcode_line is not None:
                        # 바코드 이후 숫자는 항상 포함, 바코드 이전 숫자는 다음 품목명 이전만 포함
                        found_numbers = [(line_idx, num_str, num_val) for line_idx, num_str, num_val in found_numbers 
                                       if line_idx > barcode_line or line_idx < next_item_line]
                        print(f"[디버그]   다음 품목명 이전 숫자만 사용 (바코드 이후 숫자는 항상 포함): {len(found_numbers)}개")
                    else:
                        # 바코드가 없는 경우, 다음 품목명 이전 숫자만 사용
                        # 다음 품목명 이후 숫자는 다음 품목의 데이터이므로 제외
                        found_numbers = [(line_idx, num_str, num_val) for line_idx, num_str, num_val in found_numbers if line_idx < next_item_line]
                        print(f"[디버그]   다음 품목명 이전 숫자만 사용: {len(found_numbers)}개")
                
                if not found_numbers:
                    print(f"[디버그]   총 {len(found_numbers)}개 숫자 발견")
                
                # 찾은 숫자들을 순서대로 단가, 수량, 금액으로 분류
                # 표 형식: 단가 -> 수량 -> 금액 순서 (바코드 이후)
                # 숫자들을 줄 번호 순서대로 정렬하고 중복 제거 (같은 줄 번호는 하나만)
                seen_line_indices = set()
                found_numbers_unique = []
                for num_line_idx, num_str, num_val in sorted(found_numbers, key=lambda x: x[0]):
                    if num_line_idx not in seen_line_indices:
                        seen_line_indices.add(num_line_idx)
                        found_numbers_unique.append((num_line_idx, num_str, num_val))
                found_numbers_sorted = found_numbers_unique
                
                # 숫자들을 순서대로 분류
                # 표 형식: 단가 -> 수량 -> 금액 순서
                # 수량은 이미 추출되었을 수 있으므로, 숫자들 중에서 수량을 제외하고 단가와 금액을 찾음
                for num_line_idx, num_str, num_val in found_numbers_sorted:
                    # 수량: 1-99 범위 (작은 숫자) - 이미 수량이 추출되지 않은 경우만
                    if quantity is None and 1 <= num_val <= 99:
                        quantity = num_str
                        print(f"[디버그]   수량: {quantity} (Line {num_line_idx})")
                    # 단가 또는 금액: 100원 이상, 10,000,000원 이하
                    elif 100 <= num_val <= 10000000:
                        if unit_price is None:
                            # 첫 번째 큰 숫자는 단가
                            unit_price = num_str
                            print(f"[디버그]   단가: {unit_price} (Line {num_line_idx})")
                        elif total_price is None:
                            # 두 번째 큰 숫자는 금액
                            total_price = num_str
                            print(f"[디버그]   금액: {total_price} (Line {num_line_idx})")
                
                # 품명과 가격 정보가 있으면 추가
                if item_name and (unit_price or total_price):
                    # 수량이 없으면 1로 설정
                    if not quantity:
                        quantity = "1"
                    
                    # 총액이 있으면 총액/수량으로 단가 계산 (가장 확실한 방법)
                    if total_price and quantity:
                        try:
                            total_int = int(total_price.replace(',', ''))
                            qty_int = int(quantity)
                            if qty_int > 0:
                                calculated_unit_price = total_int // qty_int
                                # 계산된 단가가 합리적인 범위인지 확인
                                if 100 <= calculated_unit_price <= 10000000:
                                    # 기존 단가가 있으면, 계산된 단가와 비교 (50% 이상 차이면 무시)
                                    if unit_price:
                                        existing_unit_price = int(unit_price.replace(',', ''))
                                        if abs(calculated_unit_price - existing_unit_price) / existing_unit_price > 0.5:
                                            print(f"[디버그] {item_name} 총액/수량 계산 단가({calculated_unit_price}원)가 기존 단가({existing_unit_price}원)와 너무 다름, 기존 단가 유지")
                                        else:
                                            unit_price = f"{calculated_unit_price:,}"
                                            print(f"[디버그] {item_name} 단가 계산: {unit_price}원 (총액 {total_price}원 / 수량 {quantity})")
                                    else:
                                        unit_price = f"{calculated_unit_price:,}"
                                        print(f"[디버그] {item_name} 단가 계산: {unit_price}원 (총액 {total_price}원 / 수량 {quantity})")
                        except:
                            pass
                    
                    # 단가가 없으면 총액을 단가로 사용 (수량이 1인 경우)
                    if not unit_price and total_price:
                        try:
                            total_int = int(total_price.replace(',', ''))
                            qty_int = int(quantity)
                            if qty_int > 0:
                                unit_price_int = total_int // qty_int
                                unit_price = f"{unit_price_int:,}"
                        except:
                            unit_price = total_price
                    
                    # 단가와 총액이 모두 있으면 검증
                    if unit_price and total_price and quantity:
                        try:
                            unit_int = int(unit_price.replace(',', ''))
                            qty_int = int(quantity)
                            total_int = int(total_price.replace(',', ''))
                            expected_total = unit_int * qty_int
                            # 총액이 예상 총액과 50% 이상 차이나면 총액을 무시 (다음 품목의 숫자일 가능성)
                            if abs(total_int - expected_total) / max(expected_total, 1) > 0.5:
                                print(f"[디버그] {item_name} 총액({total_price}원)이 예상 총액({expected_total:,}원)과 너무 다름, 총액 무시")
                                total_price = None
                            elif abs(total_int - expected_total) > 100:
                                # 불일치하면 총액/수량으로 단가 재조정
                                if qty_int > 0:
                                    unit_price = f"{total_int // qty_int:,}"
                                    print(f"[디버그] {item_name} 단가 재조정: {unit_price}원 (총액 {total_price}원 / 수량 {quantity})")
                        except:
                            pass
                    
                    # 금액이 없고 단가와 수량이 있으면, 다음 품목명 이후의 숫자를 확인
                    if not total_price and unit_price and quantity and next_item_line is not None:
                        try:
                            unit_int = int(unit_price.replace(',', ''))
                            qty_int = int(quantity)
                            expected_total = unit_int * qty_int
                            # 다음 품목명 이후 몇 줄의 숫자를 확인
                            for check_j in range(next_item_line + 1, min(next_item_line + 3, len(lines))):
                                check_line = lines[check_j].strip()
                                # 숫자만 있는 줄 확인
                                if re.match(r'^[\d,.\s]+$', check_line):
                                    try:
                                        num_str_clean = check_line.replace('.', '').replace(',', '').replace(' ', '')
                                        if num_str_clean:
                                            num_val = int(num_str_clean)
                                            # 예상 금액과 일치하는지 확인 (100원 이내 오차 허용)
                                            if abs(num_val - expected_total) <= 100:
                                                num_str_for_display = check_line.replace('.', ',')
                                                total_price = num_str_for_display
                                                print(f"[디버그] {item_name} 다음 품목명 이후에서 금액 발견: {total_price}원 (예상: {expected_total:,}원)")
                                                break
                                    except:
                                        pass
                        except:
                            pass
                    
                    # 단가가 있으면 단가를 가격으로 사용
                    price_to_use = unit_price if unit_price else total_price
                    
                    if price_to_use:
                        print(f"[품목 추출] {item_name} - {price_to_use}원 (수량: {quantity}) [표 형식]")
                        items.append({
                            "name": item_name,
                            "price": price_to_use,
                            "quantity": quantity
                        })
                        # 다음 품목으로 이동
                        if next_item_line is not None:
                            # 다음 품목명이 발견되었으면 그 위치로 이동
                            idx = next_item_line
                        elif found_numbers:
                            # 찾은 숫자 중 마지막 줄 다음으로
                            last_num_line = max(num_line_idx for num_line_idx, _, _ in found_numbers)
                            idx = last_num_line + 1
                        else:
                            # 숫자를 찾지 못했으면 기본적으로 다음 줄로
                            idx += 1
                        continue
                else:
                    # 품목명은 찾았지만 가격 정보가 없음
                    print(f"[디버그] 품목명 '{item_name}' 발견했지만 가격 정보 없음, 다음 줄로 이동")
                    idx += 1
                    continue
            
            idx += 1
        
        # 표 형식으로 파싱했으면 기존 로직 건너뛰기
        if items:
            print(f"[디버그] 표 형식으로 {len(items)}개 품목 추출 완료")
            # 표 형식 파싱 후 필터링 로직으로 이동
            # (아래 필터링 로직은 그대로 사용)
    
    # 여러 줄에 걸친 품목 패턴 처리 (품목명\n수량\n가격)
    i = 0
    # 디버깅: 처음 몇 줄 출력
    print(f"[디버그] OCR 텍스트 처음 30줄:")
    for debug_i, debug_line in enumerate(lines[:30]):
        print(f"  Line {debug_i}: '{debug_line.strip()}'")
    
    # 표 형식으로 이미 파싱했으면 기존 로직 건너뛰기
    if table_format_detected and items:
        print(f"[디버그] 표 형식 파싱 완료, 기존 로직 건너뛰기")
        i = len(lines)  # 루프 건너뛰기
    
    while i < len(lines):
        line_stripped = lines[i].strip()
        
        # 빈 줄이나 너무 짧은 줄 제외
        if len(line_stripped) < 2:
            i += 1
            continue
        
        # 제외 키워드가 포함된 줄 제외 (공백 제거 후 비교)
        line_no_spaces = line_stripped.replace(' ', '').replace(':', '')
        if any(keyword.replace(' ', '') in line_no_spaces for keyword in exclude_keywords):
            i += 1
            continue
        
        # ":" 뒤에 오는 숫자는 품목이 아닐 가능성이 높음 (예: "단말기 No: 4079538")
        if ':' in line_stripped:
            # ":" 뒤에 숫자만 있으면 제외
            parts = line_stripped.split(':', 1)
            if len(parts) == 2:
                after_colon = parts[1].strip()
                if re.match(r'^[\d,\s]+$', after_colon):
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
        # 인라인 가격이 있어도 다음 줄에 수량이 있을 수 있으므로 여러 줄 패턴으로 처리
        if re.search(r'[가-힣A-Za-z]', line_stripped) and not re.match(r'^[\d,\s원]+$', line_stripped):
            # 다음 줄들이 수량과 가격일 수 있음
            item_name = line_stripped
            quantity = None
            price = None
            
            # 인라인 가격이 있는 경우, 품목명에서 가격 추출
            if has_price_inline:
                # 품목명에서 가격 추출 (예: "덮 밥 6000" -> "덮 밥", "6000")
                price_match = re.search(r'\s+([\d,]+)\s*원?\s*$', line_stripped)
                if price_match:
                    try:
                        price_val = int(price_match.group(1).replace(',', '').replace(' ', ''))
                        if price_val >= 1000:
                            price = str(price_val)
                            # 품목명에서 가격 제거
                            item_name = re.sub(r'\s+[\d,]+\s*원?\s*$', '', line_stripped).strip()
                            print(f"[디버그] 인라인 가격 추출: 품목명='{item_name}', 가격={price}원")
                    except:
                        pass
            
            # 디버깅: 코카콜라 관련 품목명 확인
            if '007' in line_stripped or '코카콜라' in line_stripped or '콜라' in line_stripped:
                print(f"[디버그] 코카콜라 품목명 발견: '{line_stripped}' (Line {i})")
                print(f"[디버그] 다음 8줄 확인:")
                for debug_j in range(i + 1, min(i + 9, len(lines))):
                    print(f"  Line {debug_j}: '{lines[debug_j].strip()}'")
            
            # 다음 2-8줄 확인 (바코드, 단가, 수량, 총액이 각각 다른 줄에 있을 수 있음)
            unit_price_line = None
            quantity_line = None
            total_price_line = None
            found_item = False
            
            # 바코드가 있는지 먼저 확인
            barcode_line_idx = None
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                # 바코드 줄 확인 (숫자만 있고 길이가 10자 이상)
                if re.match(r'^\d{10,}$', next_line):
                    barcode_line_idx = j
                    if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                        print(f"[디버그] 코카콜라 바코드 발견: {next_line} (Line {j})")
                    break
            
            # 바코드 이후부터 단가, 수량, 금액 찾기
            start_search = barcode_line_idx + 1 if barcode_line_idx is not None else i + 1
            
            for j in range(start_search, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                
                # 바코드 줄 건너뛰기 (숫자만 있고 길이가 10자 이상)
                is_barcode = re.match(r'^\d{10,}$', next_line)
                if is_barcode:
                    continue
                
                # "증정" 확인 (가격이 0인 경우)
                if '증정' in next_line or '무료' in next_line:
                    # 수량이 이미 있으면 품목 추가
                    if quantity_line:
                        quantity = quantity_line[1]
                    else:
                        # 수량이 없으면 1로 설정
                        quantity = "1"
                    price = "0"
                    print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity}) [증정]")
                    items.append({
                        "name": item_name,
                        "price": price,
                        "quantity": quantity
                    })
                    i = j + 1
                    found_item = True
                    break
                
                # 다음 품목명이 나오면 중단
                if re.search(r'[가-힣A-Za-z]', next_line) and not re.match(r'^[\d,\s원]+$', next_line):
                    break
                
                # 수량 추출 (1-2자리 숫자만) - CU 편의점처럼 수량이 먼저 나올 수 있음
                if not quantity_line:
                    # 바코드가 아닌 경우에만 수량으로 인식
                    if not is_barcode:
                        if re.match(r'^\d{1,2}$', next_line):
                            try:
                                qty = int(next_line)
                                if 1 <= qty <= 99:
                                    quantity_line = (j, next_line, qty)
                                    if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                                        print(f"[디버그] 코카콜라 수량 발견: {next_line} (Line {j})")
                                    continue
                            except:
                                pass
                
                # 단가 추출 (숫자 + 쉼표, 공백 포함 가능, 100원 이상)
                # 단가는 바코드보다 작은 숫자 (일반적으로 10자리 미만)
                # 인라인 가격이 이미 추출된 경우 단가를 찾지 않음
                if not unit_price_line and not price:
                    # 공백 포함 가격 처리 (예: "2, 500")
                    price_match = re.match(r'^([\d,\s]+)$', next_line)
                    if price_match:
                        price_str = price_match.group(1).replace(' ', '').replace(',', '').strip()
                        try:
                            price_int = int(price_str)
                            # 단가는 100원 이상이고, 바코드보다 짧아야 함 (10자리 미만)
                            if 100 <= price_int <= 10000000 and len(price_str) < 10:
                                unit_price_line = (j, price_str, price_int)
                                if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                                    print(f"[디버그] 코카콜라 단가 발견: {price_str} (Line {j})")
                                continue
                        except:
                            pass
                
                # 수량이 먼저 나오고 가격이 나중에 나오는 경우 처리 (CU 편의점 패턴)
                # 예: 품목명 -> 수량 -> 가격
                if quantity_line and not unit_price_line and not price:
                    # 공백 포함 가격 처리 (예: "2, 500")
                    price_match = re.match(r'^([\d,\s]+)$', next_line)
                    if price_match:
                        price_str = price_match.group(1).replace(' ', '').replace(',', '').strip()
                        try:
                            price_int = int(price_str)
                            # 가격은 100원 이상이고, 바코드보다 짧아야 함 (10자리 미만)
                            if 100 <= price_int <= 10000000 and len(price_str) < 10:
                                unit_price_line = (j, price_str, price_int)
                                # 수량과 가격을 찾았으므로 품목 추가
                                price = price_str
                                quantity = quantity_line[1]
                                print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity}) [수량/가격 패턴]")
                                items.append({
                                    "name": item_name,
                                    "price": price,
                                    "quantity": quantity
                                })
                                i = j + 1  # 가격 줄 다음부터 시작
                                found_item = True
                                break  # for 루프 종료
                        except:
                            pass
                
                # 총액 추출 (단가와 수량이 모두 있을 때만)
                if unit_price_line and quantity_line and not total_price_line:
                    # 공백 포함 가격 처리 (예: "2, 500")
                    total_match = re.match(r'^([\d,\s]+)$', next_line)
                    if total_match:
                        total_str = total_match.group(1).replace(' ', '').replace(',', '').strip()
                        try:
                            total_int = int(total_str)
                            # 총액 = 단가 * 수량인지 확인
                            expected_total = unit_price_line[2] * quantity_line[2]
                            if total_int == expected_total or abs(total_int - expected_total) <= 100:
                                total_price_line = (j, total_str, total_int)
                                # 모든 정보를 찾았으므로 품목 추가
                                price = unit_price_line[1]
                                quantity = quantity_line[1]
                                print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity}) [단가/수량/총액 분리 패턴]")
                                items.append({
                                    "name": item_name,
                                    "price": price,
                                    "quantity": quantity
                                })
                                i = j + 1  # 총액 줄 다음부터 시작
                                found_item = True
                                break  # for 루프 종료
                        except:
                            pass
                
                # 다음 품목명이 나오면 중단
                if re.search(r'[가-힣A-Za-z]', next_line) and not re.match(r'^[\d,\s원]+$', next_line):
                    # 단가만 찾았고 수량을 찾지 못한 경우, 다음 몇 줄에서 수량을 더 찾아봐야 함
                    # 또는 인라인 가격이 있는 경우 수량을 찾아야 함
                    if (unit_price_line or price) and not quantity_line:
                        # 다음 몇 줄에서 수량 찾기
                        for k in range(j + 1, min(j + 4, len(lines))):
                            check_line = lines[k].strip()
                            if re.match(r'^\d{1,2}$', check_line):
                                try:
                                    qty = int(check_line)
                                    if 1 <= qty <= 99:
                                        quantity_line = (k, check_line, qty)
                                        if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                                            print(f"[디버그] 코카콜라 수량 발견 (지연): {check_line} (Line {k})")
                                        break
                                except:
                                    pass
                    
                    # 단가와 수량을 찾았으면 품목 추가 (총액은 없어도 됨)
                    # 또는 인라인 가격과 수량을 찾았으면 품목 추가
                    if (unit_price_line or price) and quantity_line:
                        if price:
                            # 인라인 가격 사용
                            final_price = price
                        else:
                            # 단가 사용
                            final_price = unit_price_line[1]
                        quantity = quantity_line[1]
                        print(f"[품목 추출] {item_name} - {final_price}원 (수량: {quantity}) [단가/수량 패턴]")
                        items.append({
                            "name": item_name,
                            "price": final_price,
                            "quantity": quantity
                        })
                        i = j  # 다음 품목명 줄부터 시작
                        found_item = True
                        break  # for 루프 종료
                    else:
                        # 정보를 찾지 못했으면 다음 품목으로
                        if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                            print(f"[디버그] 코카콜라 품목 추가 실패 - 단가: {unit_price_line}, 수량: {quantity_line}")
                        i += 1
                        found_item = False
                        break  # for 루프 종료
            
            # for 루프를 빠져나온 후 처리
            if found_item:
                continue  # while 루프의 다음 반복으로
            
            # 단가와 수량을 찾았지만 총액을 찾지 못한 경우
            if (unit_price_line or price) and quantity_line and not total_price_line:
                if price:
                    final_price = price
                else:
                    final_price = unit_price_line[1]
                quantity = quantity_line[1]
                # 총액 계산 (단가 * 수량)
                try:
                    price_int = int(final_price.replace(',', '').replace(' ', ''))
                    qty_int = int(quantity)
                    total_amount = price_int * qty_int
                    print(f"[품목 추출] {item_name} - {final_price}원 (수량: {quantity}, 총액: {total_amount:,}원) [단가/수량 패턴]")
                except:
                    print(f"[품목 추출] {item_name} - {final_price}원 (수량: {quantity}) [단가/수량 패턴]")
                items.append({
                    "name": item_name,
                    "price": final_price,
                    "quantity": quantity
                })
                i = (quantity_line[0] if quantity_line else (unit_price_line[0] if unit_price_line else i)) + 1
                continue
            
            # 단가만 찾고 수량을 찾지 못한 경우 (코카콜라 같은 경우)
            # 또는 인라인 가격이 있는데 수량을 찾지 못한 경우
            if (unit_price_line or price) and not quantity_line:
                # 단가 줄 이후 또는 품목명 줄 이후 몇 줄에서 수량 찾기
                if unit_price_line:
                    start_search = unit_price_line[0] + 1
                else:
                    start_search = i + 1
                for k in range(start_search, min(start_search + 5, len(lines))):
                    check_line = lines[k].strip()
                    # 바코드 건너뛰기
                    if re.match(r'^\d{10,}$', check_line):
                        continue
                    # 제외 키워드 확인
                    if any(keyword.replace(' ', '') in check_line.replace(' ', '').replace(':', '') for keyword in ['합계', '소계', '총구매액', '청구금액', '받을금액', '받은금액']):
                        break
                    # 수량 찾기
                    if re.match(r'^\d{1,2}$', check_line):
                        try:
                            qty = int(check_line)
                            if 1 <= qty <= 99:
                                quantity_line = (k, check_line, qty)
                                if price:
                                    final_price = price
                                else:
                                    final_price = unit_price_line[1]
                                quantity = quantity_line[1]
                                if '007' in item_name or '코카콜라' in item_name or '콜라' in item_name:
                                    print(f"[디버그] 코카콜라 수량 발견 (후처리): {check_line} (Line {k})")
                                print(f"[품목 추출] {item_name} - {final_price}원 (수량: {quantity}) [단가/수량 패턴 - 후처리]")
                                items.append({
                                    "name": item_name,
                                    "price": final_price,
                                    "quantity": quantity
                                })
                                i = k + 1
                                continue  # while 루프의 다음 반복으로
                        except:
                            pass
            
            # 아무것도 찾지 못한 경우 다음 줄로
            i += 1
            continue
            
            # 기존 로직: "단가 수량 총액" 패턴 확인 (한 줄에 있을 때)
            if not price:
                for j in range(i + 1, min(i + 6, len(lines))):
                    next_line = lines[j].strip()
                    
                    # 먼저 "단가 수량 총액" 패턴 확인 (최우선)
                    if not price:
                        # 패턴 1: "단가 수량 총액" 형식 (예: "2,500 2 5,000" 또는 "2500 2 5000")
                        # 여러 가지 패턴 시도
                        multi_number_match = None
                        
                        # 패턴 1: 쉼표 포함 "2,500 2 5,000"
                        multi_number_match = re.match(r'^([\d,]+)\s+(\d{1,2})\s+([\d,]+)$', next_line)
                        if not multi_number_match:
                            # 패턴 2: 공백이 여러 개일 수 있음 "2, 500  2  5, 000"
                            multi_number_match = re.match(r'^([\d,\s]+?)\s+(\d{1,2})\s+([\d,\s]+?)$', next_line)
                        if not multi_number_match:
                            # 패턴 3: 탭이나 다른 공백 문자 포함
                            multi_number_match = re.match(r'^([\d,]+)[\s\t]+(\d{1,2})[\s\t]+([\d,]+)$', next_line)
                        
                        if multi_number_match:
                            unit_price_str = multi_number_match.group(1).replace(' ', '').replace(',', '').replace('\t', '').strip()
                            qty_str = multi_number_match.group(2).strip()
                            total_price_str = multi_number_match.group(3).replace(' ', '').replace(',', '').replace('\t', '').strip()
                            try:
                                unit_price_int = int(unit_price_str)
                                qty_int = int(qty_str)
                                total_price_int = int(total_price_str)
                                # 단가가 100원 이상이고, 총액 = 단가 * 수량이면 유효한 패턴
                                if 100 <= unit_price_int <= 10000000 and 1 <= qty_int <= 99:
                                    if total_price_int == unit_price_int * qty_int or abs(total_price_int - unit_price_int * qty_int) <= 100:
                                        price = unit_price_str
                                        quantity = qty_str
                                        print(f"[품목 추출] {item_name} - {price}원 (수량: {quantity}) [단가 수량 총액 패턴 - 여러줄]")
                                        i = j + 1  # 다음 줄부터 시작
                                        break
                            except Exception as e:
                                print(f"[디버그] 단가 수량 총액 패턴 파싱 실패: {next_line}, 오류: {e}")
                                pass
                
                # 수량 추출 (숫자만, 1-99 범위) - "단가 수량 총액" 패턴이 없을 때만
                if not quantity and not price and re.match(r'^\d{1,2}$', next_line):
                    try:
                        qty = int(next_line)
                        if 1 <= qty <= 99:
                            quantity = next_line
                            continue
                    except:
                        pass
                
                # 가격 추출 (숫자 + 쉼표, "원" 포함 가능, 공백 허용) - "단가 수량 총액" 패턴이 없을 때만
                if not price:
                    
                    # 패턴 2: 숫자만 있는 줄 (예: "3,500" 또는 "3500" 또는 "3, 500" - 공백 포함)
                    price_match = re.search(r'^([\d,\s]+)$', next_line)
                    if not price_match:
                        # 패턴 3: 숫자 + "원" (예: "3,500원" 또는 "3500원" 또는 "3, 500원")
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
        
        # 먼저 다음 줄에 "단가 수량 총액" 패턴이 있는지 확인
        quantity = None
        price = None
        item_name_from_line = None
        
        if i + 1 < len(lines):
            next_line_check = lines[i + 1].strip()
            # 디버깅: 품목명과 다음 줄 출력
            if '몽쉘' in line_stripped or '바나나' in line_stripped or '해태' in line_stripped or '코카콜라' in line_stripped or '종이컵' in line_stripped:
                print(f"[디버그] 품목명: '{line_stripped}' -> 다음 줄: '{next_line_check}'")
            
            # "단가 수량 총액" 패턴 확인 (예: "2,500 2 5,000" 또는 "2500 2 5000")
            # 여러 패턴 시도
            multi_number_match = None
            
            # 패턴 1: 기본 패턴 "2,500 2 5,000"
            multi_number_match = re.match(r'^([\d,]+)\s+(\d{1,2})\s+([\d,]+)$', next_line_check)
            if not multi_number_match:
                # 패턴 2: 공백이 여러 개 "2, 500  2  5, 000"
                multi_number_match = re.match(r'^([\d,\s]+?)\s+(\d{1,2})\s+([\d,\s]+?)$', next_line_check)
            if not multi_number_match:
                # 패턴 3: 탭 문자 포함
                multi_number_match = re.match(r'^([\d,]+)[\s\t]+(\d{1,2})[\s\t]+([\d,]+)$', next_line_check)
            if not multi_number_match:
                # 패턴 4: 모든 공백 문자 허용
                multi_number_match = re.match(r'^([\d,]+)\s+(\d{1,2})\s+([\d,]+)', next_line_check)
            
            if multi_number_match:
                print(f"[디버그] 단가 수량 총액 패턴 매칭 성공: {next_line_check}")
                unit_price_str = multi_number_match.group(1).replace(' ', '').replace(',', '').replace('\t', '').strip()
                qty_str = multi_number_match.group(2).strip()
                total_price_str = multi_number_match.group(3).replace(' ', '').replace(',', '').replace('\t', '').strip()
                print(f"[디버그] 파싱 결과 - 단가: {unit_price_str}, 수량: {qty_str}, 총액: {total_price_str}")
                try:
                    unit_price_int = int(unit_price_str)
                    qty_int = int(qty_str)
                    total_price_int = int(total_price_str)
                    # 단가가 100원 이상이고, 총액 = 단가 * 수량이면 유효한 패턴
                    if 100 <= unit_price_int <= 10000000 and 1 <= qty_int <= 99:
                        if total_price_int == unit_price_int * qty_int or abs(total_price_int - unit_price_int * qty_int) <= 100:
                            # 현재 줄이 품목명인지 확인 (한글이나 영문 포함)
                            if re.search(r'[가-힣A-Za-z]', line_stripped) and not re.match(r'^[\d,\s원]+$', line_stripped):
                                # 현재 줄에서 숫자 제거하여 품목명 추출
                                # "001 P 몽쉘카카오케이크 192G" 같은 경우 "001 P" 부분도 제거
                                item_name_from_line = re.sub(r'^\d+\s*[A-Z]\s*', '', line_stripped).strip()  # "001 P " 제거
                                item_name_from_line = re.sub(r'\s*\d+[A-Z]*\s*$', '', item_name_from_line).strip()  # 끝의 숫자 제거
                                if len(item_name_from_line) >= 1:
                                    price = unit_price_str
                                    quantity = qty_str
                                    print(f"[품목 추출] {item_name_from_line} - {price}원 (수량: {quantity}) [단가 수량 총액 패턴 - 다음 줄]")
                                    items.append({
                                        "name": item_name_from_line,
                                        "price": price,
                                        "quantity": quantity
                                    })
                                    i = i + 2  # 다음 다음 줄부터 시작
                                    continue
                except Exception as e:
                    print(f"[디버그] 단가 수량 총액 패턴 파싱 실패: {next_line_check}, 오류: {e}")
                    pass
        
        # 다음 줄 패턴이 없으면 기존 한 줄 패턴 처리
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
            
            # 제외 키워드가 포함된 줄 제외 (한 줄 패턴에서도, 공백 제거 후 비교)
            item_name_no_spaces = item_name.replace(' ', '').replace(':', '')
            if any(keyword.replace(' ', '') in item_name_no_spaces for keyword in exclude_keywords):
                i += 1
                continue
            
            # ":" 뒤에 오는 숫자는 품목이 아닐 가능성이 높음 (예: "단말기 No: 4079538")
            if ':' in item_name:
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
            
            # 패턴 1: "개", "EA" 같은 단위가 있는 경우
            quantity_match = re.search(r'(\d+)\s*(?:개|EA|ea|장|병|팩)', item_name)
            if quantity_match:
                quantity = quantity_match.group(1)
                name_price_part = item_name[:quantity_match.start()].strip()
            else:
                # 패턴 2: 품목명과 가격 사이에 있는 작은 숫자(1-99)를 수량으로 인식
                # 예: "001 P 몽쉘카카오케이크 192G 2 2500" -> 수량 2
                # 가격 위치를 기준으로 그 앞의 작은 숫자를 찾음
                price_start_pos = price_match.start()
                text_before_price = line_stripped[:price_start_pos].strip()
                
                # 끝에서부터 숫자 패턴 찾기 (가격 바로 앞의 숫자)
                # 공백으로 구분된 작은 숫자(1-99)를 수량으로 간주
                # 모든 숫자 패턴을 찾되, 가격에 가장 가까운 작은 숫자를 선택
                all_numbers = list(re.finditer(r'\b(\d+)\b', text_before_price))
                if all_numbers:
                    # 마지막 숫자부터 역순으로 확인 (가격에 가장 가까운 것부터)
                    for num_match in reversed(all_numbers):
                        try:
                            num_val = int(num_match.group(1))
                            # 1-99 범위이고, 가격보다 훨씬 작으면 수량으로 간주
                            if 1 <= num_val <= 99 and num_val < price_int / 100:
                                # 해당 숫자 뒤에 큰 숫자(가격 후보)가 없으면 수량으로 확정
                                text_after_num = text_before_price[num_match.end():].strip()
                                # 큰 숫자(3자리 이상)가 없으면 수량으로 확정
                                if not re.search(r'\b\d{3,}\b', text_after_num):
                                    quantity = num_match.group(1)
                                    name_price_part = text_before_price[:num_match.start()].strip()
                                    break
                        except:
                            pass
            
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
    
    # 추가 필터링: 잘못 추출된 품목 제거
    items_filtered = []
    for item in items:
        item_name = item.get("name", "").strip()
        item_price = item.get("price", "")
        
        # 디버깅: 코카콜라 관련 품목 확인
        if '코카콜라' in item_name or '콜라' in item_name:
            print(f"[디버그] 코카콜라 품목 발견: '{item_name}', 가격: '{item_price}'")
        
        # 디버깅: 연세스트로베리요거트 관련 품목 확인
        if '연세스트로베리' in item_name or '스트로베리' in item_name:
            print(f"[디버그] 연세스트로베리요거트 품목 발견: '{item_name}', 가격: '{item_price}'")
        
        # 품목명이 비어있거나 너무 짧으면 제외
        if len(item_name) < 2:
            if '코카콜라' in item_name or '콜라' in item_name:
                print(f"[디버그] 코카콜라 제외: 품목명이 너무 짧음")
            print(f"[디버그] 품목 제외: 품목명이 너무 짧음 - '{item_name}'")
            continue
        
        # 품목명이 숫자만 있으면 제외
        if re.match(r'^[\d,\s]+$', item_name):
            print(f"[디버그] 품목 제외: 품목명이 숫자만 - '{item_name}'")
            continue
        
        # 품목명에 제외 키워드가 포함되어 있으면 제외 (공백 제거 후 비교)
        item_name_no_spaces = item_name.replace(' ', '').replace(':', '')
        if any(keyword.replace(' ', '') in item_name_no_spaces for keyword in exclude_keywords):
            if '코카콜라' in item_name or '콜라' in item_name:
                print(f"[디버그] 코카콜라 제외: 제외 키워드 포함")
            print(f"[디버그] 품목 제외: 제외 키워드 포함 - '{item_name}'")
            continue
        
        # 품목명에 ":"가 포함되어 있으면 제외 (예: "단말기 No:", "카드번호:")
        if ':' in item_name:
            print(f"[디버그] 품목 제외: 품목명에 ':' 포함 - '{item_name}'")
            continue
        
        # 가격이 없으면 제외 (가격이 0인 경우는 증정 항목일 수 있으므로 포함)
        if not item_price:
            if '코카콜라' in item_name or '콜라' in item_name:
                print(f"[디버그] 코카콜라 제외: 가격이 없음")
            continue
        
        # 가격 파싱
        try:
            price_num = int(str(item_price).replace(",", "").replace(" ", ""))
            # 가격이 0원 미만이거나 10,000,000원 초과면 제외 (0원은 증정 항목이므로 포함)
            if price_num < 0 or price_num > 10000000:
                if '코카콜라' in item_name or '콜라' in item_name:
                    print(f"[디버그] 코카콜라 제외: 가격 범위 초과 ({price_num})")
                if '연세스트로베리' in item_name or '스트로베리' in item_name:
                    print(f"[디버그] 연세스트로베리요거트 제외: 가격 범위 초과 ({price_num})")
                continue
            # 가격이 1원 이상 100원 미만이면 비정상적인 값으로 간주 (단, 0원은 증정 항목이므로 허용)
            if 0 < price_num < 100:
                print(f"[디버그] 품목 제외: 가격이 비정상적으로 낮음 - {item_name} ({price_num}원)")
                if '연세스트로베리' in item_name or '스트로베리' in item_name:
                    print(f"[디버그] 연세스트로베리요거트 제외: 가격이 비정상적으로 낮음 ({price_num}원)")
                continue
        except Exception as e:
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 가격 파싱 실패 - {item_name}, 가격: {item_price}, 오류: {e}")
            continue
        
        # 품목명에 한글이나 영문이 포함되어 있어야 함 (의미 있는 품목명)
        if not re.search(r'[가-힣A-Za-z]', item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 한글/영문 없음 - '{item_name}'")
            continue
        
        # 주소 패턴 제외 (지역명 + 도로명/번지)
        # 더 엄격한 주소 패턴: 실제 지역명(서울, 부산 등)이 포함되고 주소 관련 키워드도 함께 있는 경우만 제외
        # 단일 문자('시', '도', '구' 등)만으로는 판단하지 않음 (품목명에 포함될 수 있음)
        major_regions = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', 
                        '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
                        '용인', '성남', '수원', '안양', '안산', '고양', '부천', '의정부']
        is_address = any(region in item_name for region in major_regions)
        # 주소 관련 키워드가 함께 있는 경우만 제외 (단, '구'는 너무 일반적이므로 제외)
        if is_address and ('로' in item_name or '길' in item_name or '동' in item_name or '번지' in item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 주소 패턴 - '{item_name}'")
            continue
        
        # 전화번호 패턴 제외 (숫자-숫자-숫자 형식)
        if re.search(r'\d{2,3}-\d{3,4}-\d{4}', item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 전화번호 패턴 - '{item_name}'")
            continue
        
        # 사업자번호 패턴 제외 (숫자-숫자-숫자 형식)
        if re.search(r'\d{3}-\d{2}-\d{5}', item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 사업자번호 패턴 - '{item_name}'")
            continue
        
        # 날짜 패턴 제외 (YYYY/MM/DD 또는 YY/MM/DD)
        if re.search(r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}', item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 날짜 패턴 - '{item_name}'")
            continue
        
        # 시간 패턴 제외 (HH:MM:SS)
        if re.search(r'\d{1,2}:\d{2}:\d{2}', item_name):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 시간 패턴 - '{item_name}'")
            continue
        
        # 품목명이 너무 짧거나 의미 없는 경우 제외 (예: "세 :", "No :")
        # 한글이나 영문이 2자 이상 포함되어야 함
        meaningful_chars = re.findall(r'[가-힣A-Za-z]', item_name)
        if len(meaningful_chars) < 2:
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 의미 있는 문자 부족 - '{item_name}' (의미 있는 문자: {len(meaningful_chars)}개)")
            continue
        
        # 특정 패턴 제외 (공백 제거 후 체크)
        item_name_normalized = item_name.replace(' ', '').replace(':', '').replace(' ', '')
        excluded_patterns = [
            '부가세', '단말기', '카드번호', '가맹번호', '승인번호', '주문번호',
            '거래일시', '주문일시', '전화번호', '사업자번호', '업소명', '대표자',
            '받을금액', '받은금액', '합계', '총구매액', '소계', '결제금액',
            '내실금액', '내실금', '내실', '신용액', '신용', '공급가액', '부가세액',
            '부가세면세물품가액', '부가세과세물품가액', '주문합계', '신용카드', '신용승인'
        ]
        if any(pattern in item_name_normalized for pattern in excluded_patterns):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 제외 패턴 포함 - '{item_name}'")
            continue
        
        # "세 :", "내 실 금", "신용" 같은 짧은 패턴도 제외
        item_name_stripped = item_name.strip()
        if item_name_stripped in ['세 :', '세:', '내 실 금', '내실금', '내 실', '신용', '신용:']:
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 짧은 패턴 - '{item_name}'")
            continue
        
        # "신용"으로 시작하거나 끝나는 항목 제외
        if item_name_stripped.startswith('신용') or item_name_stripped.endswith('신용'):
            if '연세스트로베리' in item_name or '스트로베리' in item_name:
                print(f"[디버그] 연세스트로베리요거트 제외: 신용 패턴 - '{item_name}'")
            continue
        
        # 품목명이 숫자로 시작하거나 끝나면 제외 (예: "4079538", "949094")
        if re.match(r'^\d+', item_name) or re.match(r'.*\d+$', item_name):
            # 단, 품목명에 한글이나 영문이 포함되어 있으면 허용 (예: "제육덮밥 1")
            if not re.search(r'[가-힣A-Za-z]{2,}', item_name):
                if '연세스트로베리' in item_name or '스트로베리' in item_name:
                    print(f"[디버그] 연세스트로베리요거트 제외: 숫자로만 구성 - '{item_name}'")
                continue
        
        items_filtered.append(item)
    
    print(f"[품목 추출 완료] 총 {len(items_filtered)}개 품목 (필터링 전: {len(items)}개)")
    return items_filtered


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
