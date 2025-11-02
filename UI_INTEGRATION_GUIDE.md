# React에서 백엔드 API 사용하기

## 📁 코드를 어디에 입력하나요?

### React 프로젝트 구조 (일반적인 경우)
```
my-react-app/
├── src/
│   ├── components/          ← 여기에 컴포넌트 파일 생성
│   │   └── ReceiptAnalyzer.jsx
│   ├── hooks/              ← 여기에 커스텀 훅 생성 (선택)
│   │   └── useReceiptAnalyzer.js
│   ├── App.js             ← 메인 컴포넌트
│   └── index.js
└── package.json
```

### 방법 1: 새 컴포넌트 파일 만들기 (권장)

1. React 프로젝트의 `src/components/` 폴더에 새 파일 생성:
   - 파일명: `ReceiptAnalyzer.jsx` 또는 `ReceiptAnalyzer.js`

2. 위의 **"2. React 컴포넌트 예제"** 코드를 그대로 복사해서 붙여넣기

3. 다른 컴포넌트에서 사용:
```jsx
// App.js 또는 다른 파일에서
import ReceiptAnalyzer from './components/ReceiptAnalyzer';

function App() {
  return (
    <div>
      <ReceiptAnalyzer />
    </div>
  );
}
```

### 방법 2: 기존 컴포넌트에 코드 추가하기

기존 컴포넌트 파일에 위의 예제 코드를 복사해서 넣고, 함수명만 원하는 이름으로 변경하면 됩니다.

---

## ⚠️ 중요: React 코드는 별도 UI 프로젝트에서 작성하세요!

이 가이드의 코드는 **별도의 React 프로젝트**(예: `my-react-app`)에서 사용하세요.
이 백엔드 폴더(`Receipt-AI-Analyzer-MCP`)에 React 코드를 작성하지 마세요!

---

## 1. 백엔드 서버 실행 및 포트 확인

### 기본 실행 (8000 포트)

**Windows + Python 3.13 사용자 주의**: `--reload` 옵션으로 오류가 발생하면 아래처럼 `--reload` 없이 실행하세요.

```bash
cd Receipt-AI-Analyzer-MCP
uvicorn main:app --reload
```

**오류 발생 시** (multiprocessing 에러):
```bash
uvicorn main:app
```

서버를 재시작하려면 `Ctrl+C`로 중지한 후 다시 실행하세요.

### 특정 포트로 실행하기
만약 8000 포트가 이미 사용 중이거나 다른 포트를 사용하고 싶다면:
```bash
uvicorn main:app --reload --port 3001
```

### 서버 포트 확인 방법
서버를 실행하면 터미널에 아래와 같은 메시지가 표시됩니다:
```
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
여기서 **8000** 부분이 실제 사용 중인 포트입니다.

### React 코드에서 포트 변경하기
실제 사용 중인 포트에 맞춰 아래 코드의 포트 번호를 변경하세요:

## 2. React 컴포넌트 예제

```jsx
import { useState } from 'react';

function ReceiptAnalyzer() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const fileInput = e.target.image_file;
    const userIdInput = e.target.user_id;
    
    if (!fileInput.files[0]) {
      alert('파일을 선택해주세요');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('image_file', fileInput.files[0]);
    formData.append('user_id', userIdInput.value || 'anonymous');

    try {
      // ⚠️ 실제 서버가 실행 중인 포트로 변경하세요! (기본값: 8000)
      const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${API_URL}/analyze_receipt`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`오류: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input type="file" name="image_file" accept="image/*" required />
        <input type="text" name="user_id" placeholder="사용자 ID (선택)" />
        <button type="submit" disabled={loading}>
          {loading ? '분석 중...' : '분석하기'}
        </button>
      </form>

      {error && <div style={{ color: 'red' }}>오류: {error}</div>}

      {result && (
        <div>
          <h3>분석 결과</h3>
          <p>카테고리: {result.category}</p>
          <p>금액: {result.amount}원</p>
          <p>날짜: {result.date}</p>
          <p>상호명: {result.store_name}</p>
          
          {/* 품목 리스트 표시 */}
          {result.items && result.items.length > 0 && (
            <div>
              <h4>품목 목록</h4>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {result.items.map((item, index) => (
                  <li key={index} style={{ marginBottom: '8px' }}>
                    <strong>{item.name}</strong> {item.price}원
                    {item.quantity && <span style={{ color: '#666' }}> (수량: {item.quantity})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ReceiptAnalyzer;
```

## 3. API 응답 형식

```json
{
  "category": "음식",
  "amount": "45000",
  "date": "2024-01-15",
  "status_code": 200,
  "user_id": "user123",
  "store_name": "맛있는 식당",
  "items": [
    {
      "name": "짜장면",
      "price": "8000",
      "quantity": "2"
    },
    {
      "name": "탕수육",
      "price": "25000",
      "quantity": "1"
    }
  ],
  "nlp_analysis": {
    "sentiment": "neutral",
    "key_phrases": ["할인", "쿠폰"],
    "entities": [...],
    "insights": {...}
  }
}
```

## 4. 커스텀 훅으로 분리하기 (선택사항)

```jsx
// useReceiptAnalyzer.js
import { useState } from 'react';

export function useReceiptAnalyzer() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeReceipt = async (imageFile, userId = 'anonymous') => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('image_file', imageFile);
    formData.append('user_id', userId);

    try {
      // ⚠️ 실제 서버가 실행 중인 포트로 변경하세요!
      const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${API_URL}/analyze_receipt`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`서버 오류: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, analyzeReceipt };
}

// 컴포넌트에서 사용
import { useReceiptAnalyzer } from './useReceiptAnalyzer';

function ReceiptAnalyzer() {
  const { result, loading, error, analyzeReceipt } = useReceiptAnalyzer();

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      await analyzeReceipt(file, 'user123');
    }
  };

  return (
    <div>
      <input type="file" onChange={handleFileChange} disabled={loading} />
      {loading && <p>분석 중...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && (
        <div>
          <p>카테고리: {result.category}</p>
          <p>금액: {result.amount}원</p>
          <p>날짜: {result.date}</p>
          {result.items && result.items.length > 0 && (
            <div>
              <h4>품목 목록</h4>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {result.items.map((item, index) => (
                  <li key={index} style={{ marginBottom: '8px' }}>
                    <strong>{item.name}</strong> {item.price}원
                    {item.quantity && <span style={{ color: '#666' }}> (수량: {item.quantity})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## 5. 환경 변수로 포트 관리하기 (권장)

React 프로젝트 루트에 `.env` 파일을 만들고 백엔드 URL 설정:

```
REACT_APP_API_URL=http://127.0.0.1:8000
```

**실제 사용 중인 포트로 변경하세요!** (예: 3001, 5000 등)

이렇게 하면 코드를 수정하지 않고도 포트를 변경할 수 있습니다.

코드에서 사용:

```jsx
const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const response = await fetch(`${API_URL}/analyze_receipt`, {
  method: 'POST',
  body: formData,
});
```

## 핵심 포인트

- **FormData 사용**: 이미지 파일은 `FormData`로 전송
- **POST 요청**: `/analyze_receipt` 엔드포인트는 POST 메서드
- **필수 파라미터**: `image_file` (파일)
- **선택 파라미터**: `user_id` (문자열)

