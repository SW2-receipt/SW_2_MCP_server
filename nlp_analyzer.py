"""
Azure Text Analytics를 사용한 NLP 분석 모듈
"""
from typing import Dict, List, Optional
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


def analyze_text_with_nlp(
    text: str,
    text_analytics_client: Optional[TextAnalyticsClient]
) -> Dict:
    """
    텍스트를 Azure Text Analytics로 NLP 분석
    
    Args:
        text: 분석할 텍스트
        text_analytics_client: Text Analytics 클라이언트 (None이면 NLP 분석 건너뜀)
    
    Returns:
        NLP 분석 결과 딕셔너리:
        {
            "sentiment": "positive|neutral|negative",
            "key_phrases": ["키워드1", "키워드2", ...],
            "entities": [{"text": "엔티티", "category": "카테고리"}, ...],
            "confidence_scores": {...}
        }
    """
    if not text_analytics_client or not text:
        return {
            "sentiment": None,
            "key_phrases": [],
            "entities": [],
            "confidence_scores": {}
        }
    
    try:
        # 텍스트 길이 제한 (Text Analytics는 5120자 제한)
        max_length = 5120
        text_to_analyze = text[:max_length] if len(text) > max_length else text
        
        # 감정 분석 + 키워드 추출 + 엔티티 추출
        response = text_analytics_client.analyze_sentiment(
            documents=[text_to_analyze],
            show_opinion_mining=True
        )
        
        # 키워드 추출
        key_phrases_response = text_analytics_client.extract_key_phrases(
            documents=[text_to_analyze]
        )
        
        # 엔티티 추출
        entities_response = text_analytics_client.recognize_entities(
            documents=[text_to_analyze]
        )
        
        result = response[0]
        key_phrases_result = key_phrases_response[0]
        entities_result = entities_response[0]
        
        # 엔티티 리스트 변환
        entities = []
        if not entities_result.is_error:
            for entity in entities_result.entities:
                entities.append({
                    "text": entity.text,
                    "category": entity.category,
                    "confidence_score": entity.confidence_score
                })
        
        return {
            "sentiment": result.sentiment if not result.is_error else None,
            "key_phrases": key_phrases_result.key_phrases if not key_phrases_result.is_error else [],
            "entities": entities,
            "confidence_scores": {
                "positive": result.confidence_scores.positive if not result.is_error else 0.0,
                "neutral": result.confidence_scores.neutral if not result.is_error else 0.0,
                "negative": result.confidence_scores.negative if not result.is_error else 0.0
            }
        }
        
    except Exception as e:
        print(f"⚠️ NLP 분석 중 오류 발생: {e}")
        return {
            "sentiment": None,
            "key_phrases": [],
            "entities": [],
            "confidence_scores": {},
            "error": str(e)
        }


def extract_receipt_insights(nlp_result: Dict, parsed_data: Dict) -> Dict:
    """
    NLP 분석 결과와 파싱 데이터를 결합하여 인사이트 추출
    
    Args:
        nlp_result: NLP 분석 결과
        parsed_data: 정규식 파싱 결과
    
    Returns:
        인사이트 딕셔너리
    """
    insights = {
        "summary": "",
        "detected_categories": [],
        "important_keywords": []
    }
    
    # 키워드에서 중요한 것만 필터링
    key_phrases = nlp_result.get("key_phrases", [])
    important_keywords = []
    
    # 영수증 관련 중요한 키워드만 추출
    receipt_keywords = [
        "할인", "세일", "쿠폰", "적립", "포인트", "마일리지",
        "카드", "현금", "영수증", "거래", "구매"
    ]
    
    for phrase in key_phrases:
        if any(kw in phrase.lower() for kw in receipt_keywords):
            important_keywords.append(phrase)
    
    insights["important_keywords"] = important_keywords[:5]  # 상위 5개만
    
    # 카테고리 관련 키워드 감지
    store_name = parsed_data.get("store_name", "")
    if store_name:
        insights["detected_categories"].append(f"매장: {store_name}")
    
    # 요약 생성
    if insights["important_keywords"]:
        insights["summary"] = f"주요 키워드: {', '.join(insights['important_keywords'][:3])}"
    
    return insights

