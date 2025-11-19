"""KoNLPy 상태 확인 스크립트"""
import requests
import json

try:
    response = requests.get('http://127.0.0.1:8000/status/konlpy')
    data = response.json()
    
    print("=" * 50)
    print("KoNLPy 상태 확인")
    print("=" * 50)
    print(f"활성화 여부: {data['konlpy_active']}")
    print(f"메시지: {data['message']}")
    print(f"불용어 개수: {data['stopwords_count']}")
    
    if data.get('test_result'):
        print("\n" + "-" * 50)
        print("테스트 결과")
        print("-" * 50)
        test = data['test_result']
        print(f"테스트 문장: {test['test_text']}")
        print(f"상태: {test['status']}")
        if 'extracted_nouns' in test:
            nouns = test['extracted_nouns']
            print(f"추출된 명사: {', '.join(nouns)}")
            print(f"명사 개수: {len(nouns)}개")
    
    print("=" * 50)
    
except Exception as e:
    print(f"오류 발생: {e}")


