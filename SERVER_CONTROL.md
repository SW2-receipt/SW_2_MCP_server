# 서버 제어 명령어 가이드

## 🚀 서버 시작 방법

### 방법 1: 배치 파일 사용 (가장 간단)
```powershell
# 네트워크 접근 가능 모드 (다른 기기에서도 접근 가능)
.\start_server.bat

# 로컬 전용 모드 (127.0.0.1에서만 접근)
.\start_server_local.bat
```

### 방법 2: PowerShell에서 직접 실행
```powershell
# 가상환경 활성화 후 실행
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 또는 한 줄로
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 방법 3: 새 창에서 실행 (백그라운드처럼)
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\fdrk0\Desktop\SW_2_MCP_server'; .\venv\Scripts\Activate.ps1; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"
```

---

## 🛑 서버 중지 방법

### 방법 1: 서버 실행 창에서 직접 중지
- 서버가 실행 중인 PowerShell 창에서 **`Ctrl + C`** 키를 누릅니다.
- 가장 안전하고 권장되는 방법입니다.

### 방법 2: 프로세스 강제 종료 (PowerShell)
```powershell
# Python 프로세스 찾기
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*venv*"}

# 특정 포트(8000)를 사용하는 프로세스 찾기
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess

# 프로세스 강제 종료 (PID 확인 후)
Stop-Process -Id <PID> -Force

# 또는 한 번에 종료
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*venv*"} | Stop-Process -Force
```

### 방법 3: 포트 기반 종료
```powershell
# 포트 8000을 사용하는 프로세스 찾기 및 종료
$port = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port) {
    $pid = $port.OwningProcess
    Stop-Process -Id $pid -Force
    Write-Host "포트 8000의 프로세스(PID: $pid)를 종료했습니다."
} else {
    Write-Host "포트 8000을 사용하는 프로세스가 없습니다."
}
```

### 방법 4: 모든 Python 프로세스 종료 (주의!)
```powershell
# ⚠️ 주의: 모든 Python 프로세스를 종료합니다 (다른 Python 프로그램도 종료될 수 있음)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 🔍 서버 상태 확인

### 서버가 실행 중인지 확인
```powershell
# 방법 1: 프로세스 확인
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*venv*"}

# 방법 2: 포트 확인
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

# 방법 3: HTTP 요청으로 확인
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 2
    Write-Host "✅ 서버가 실행 중입니다! (상태 코드: $($response.StatusCode))"
} catch {
    Write-Host "❌ 서버가 실행되지 않았습니다."
}
```

---

## 📝 빠른 참조 명령어

### 서버 시작 (한 줄)
```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 서버 중지 (한 줄)
```powershell
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*venv*"} | Stop-Process -Force
```

### 서버 재시작 (한 줄)
```powershell
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*venv*"} | Stop-Process -Force; Start-Sleep -Seconds 2; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 💡 팁

1. **가장 안전한 방법**: 서버 실행 창에서 `Ctrl + C`로 종료
2. **배치 파일 사용**: `start_server.bat` 파일을 더블클릭하면 가장 간단
3. **포트 충돌**: 포트 8000이 이미 사용 중이면 다른 포트 사용
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
   ```
4. **로그 확인**: 서버 실행 창에서 실시간 로그를 확인할 수 있습니다.


