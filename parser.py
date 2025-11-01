"""
영수증 텍스트에서 구조화된 정보를 추출하는 파서 모듈
"""
import re
from typing import Optional, Dict


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
    text_lower = text.lower()
    combined_text = (text + " " + (store_name or "")).lower()
    
    # 우체국 관련 (기타로 분류) - 최우선
    if any(keyword in combined_text for keyword in ['우체국', '우편', '등기', '택배', 'ems', 'epost', '취급국']):
        return "기타"
    
    # 교육 관련 (학원, 교습소 등) - 새 카테고리
    if any(keyword in combined_text for keyword in ['학원', '교습소', '미술교습소', '미술', '음악', '체육', '영어', '수학', '교육', '강의', '레슨', '학습', '아트풀']):
        return "교육"
    
    # 쇼핑 관련 (롯데, 백화점 등 우선 체크) - 음식보다 먼저!
    if any(keyword in combined_text for keyword in ['롯데', '리치몬트', '백화점', '보석세트', '보석', '까르띠에', '상품권', '롯데상품권', '마트', '편의점', '마켓', '슈퍼', '쇼핑', '하나로마트']):
        return "쇼핑"
    
    # 의료 관련 키워드 (약국, 병원 등)
    if any(keyword in combined_text for keyword in ['약국', '병원', '의원', '치과', '오팜페이', 'phampay', '남시약국', '조제의약품', '일반의약품']):
        return "의료"
    
    # 교통 관련 (주유소 등) - 우선순위 높임
    if any(keyword in combined_text for keyword in ['주유', '경유', '디젤', '주유소', '주유금액', '농협대전유통', '매출금액', 'NHVAN']):
        return "교통"
    
    # 음식 관련 키워드
    if any(keyword in combined_text for keyword in ['음식', '식당', '카페', '레스토랑', '초밥', '회', '맛집', '치킨', '피자', '들밥', '보리굴비', '간장게장', '진라면', '주먹밥', '교자', '활어회', '국민활어회초밥']):
        return "음식"
    
    # 기타
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
        
        # "총 구 매 액" 같은 공백 많이 포함된 키워드 처리
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
                        print(f"[DEBUG] '상호명 / 이름' 패턴으로 상호명 찾음: {store_name}")
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
                print(f"[DEBUG] 주소 발견 (Line {i}): {line_stripped}")
                
                # 주소 위쪽 몇 줄에서 상호명 찾기 (우선)
                for j in range(max(0, i - 5), i):
                    prev_line = lines[j].strip()
                    print(f"[DEBUG] 위쪽 줄 (Line {j}): {prev_line}")
                    
                    # "(주)..." 패턴 먼저 확인
                    if prev_line.startswith('(주)'):
                        store_name = prev_line
                        print(f"[DEBUG] '(주)' 패턴으로 상호명 찾음 (주소 위): {store_name}")
                        break
                    
                    # 한글이 포함된 상호명만 선택
                    if re.match(r'.*[가-힣].*', prev_line) and re.match(r'^[가-힣A-Za-z0-9\s\(\)]{2,30}$', prev_line):
                        exclude_words = ['승인', '거래', '금액', '합계', '부가세', '할부', '일시불', '알림', '제출', 
                                        '이성문', '서울', '부산', '강서구', '수', '영', '팜', '페이', 'www']
                        if prev_line not in exclude_words and '팜' not in prev_line and '페이' not in prev_line:
                            store_name = prev_line
                            print(f"[DEBUG] 상호명 찾음 (주소 위): {store_name}")
                            break
                if store_name:
                    break
                
                # 주소 다음 줄도 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    print(f"[DEBUG] 다음 줄 (Line {i+1}): {next_line}")
                    
                    # 다음 줄이 "대표:", "전화:" 등이 아닌 경우만 확인
                    if not ('대표' in next_line or '전화' in next_line or '사업자번호' in next_line):
                        # 한글이 포함된 상호명만 선택
                        if re.match(r'.*[가-힣].*', next_line) and re.match(r'^[가-힣A-Za-z0-9\s]{2,20}$', next_line):
                            exclude_words = ['승인', '거래', '금액', '합계', '부가세', '할부', '일시불', '알림', '제출', 
                                            '이성문', '서울', '부산', '강서구', '팜', '페이']
                            if next_line not in exclude_words and '팜' not in next_line and '페이' not in next_line:
                                store_name = next_line
                                print(f"[DEBUG] 상호명 찾음 (주소 아래): {store_name}")
                                break
    
    # 3. "상호명:" 또는 "가맹점명:" 패턴 시도
    if not store_name:
        store_pattern = r"(?:상호명|가맹점명)\s*:?\s*([가-힣A-Za-z0-9\s\(\)]+?)(?=\n|$|/|사업자|대표|전화)"
        store_name_match = re.search(store_pattern, text, re.IGNORECASE)
        if store_name_match:
            store_name = store_name_match.group(1).strip()
            print(f"[DEBUG] '상호명/가맹점명:' 패턴으로 상호명 찾음: {store_name}")
    
    # 4. "(주)..." 패턴 시도 (주소 기반 검색에서 못 찾은 경우)
    if not store_name:
        # "(주)회사명(부가설명)" 형식 포함
        store_pattern = r"\(주\)([가-힣A-Za-z0-9\s]+(?:\([가-힣A-Za-z0-9\s]+\))?)"
        store_name_match = re.search(store_pattern, text, re.IGNORECASE)
        if store_name_match:
            extracted = store_name_match.group(1).strip()
            if len(extracted) >= 2:
                store_name = "(주)" + extracted
                print(f"[DEBUG] '(주)...' 패턴으로 상호명 찾음: {store_name}")
    
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
                    print(f"[DEBUG] 상단 줄에서 상호명 찾음 (Line {i}): {store_name}")
                    break
    
    # 상호명이 추출되지 않았을 경우 디버깅 정보 출력
    if not store_name:
        print("⚠️ 상호명 추출 실패 - 텍스트 상단 일부:")
        lines_debug = text.split('\n')
        for i_debug, line_debug in enumerate(lines_debug[:20]):  # 상단 20줄만 출력
            print(f"   Line {i_debug}: {line_debug.strip()}")
    
    return store_name


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
            "store_name": 상호명
        }
    """
    total_price = extract_total_price(text)
    purchase_date = extract_purchase_date(text)
    normalized_date = normalize_date(purchase_date)
    store_name = extract_store_name(text)
    
    return {
        "total_price": total_price,
        "purchase_date": purchase_date,
        "normalized_date": normalized_date,
        "store_name": store_name
    }
