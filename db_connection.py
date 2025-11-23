"""
Azure SQL Database 연결 및 데이터베이스 작업 모듈
"""
import os
import pyodbc
from typing import Optional, Dict, List
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Azure SQL Database 연결 및 관리 클래스"""
    
    def __init__(self):
        """데이터베이스 연결 정보를 환경 변수에서 로드"""
        self.server = os.environ.get("AZURE_SQL_SERVER")
        self.database = os.environ.get("AZURE_SQL_DATABASE")
        self.username = os.environ.get("AZURE_SQL_USERNAME")
        self.password = os.environ.get("AZURE_SQL_PASSWORD")
        self.driver = os.environ.get("AZURE_SQL_DRIVER", "{ODBC Driver 18 for SQL Server}")
        
        # 연결 문자열 구성
        self.connection_string = None
        if all([self.server, self.database, self.username, self.password]):
            self.connection_string = (
                f"Driver={self.driver};"
                f"Server={self.server};"
                f"Database={self.database};"
                f"Uid={self.username};"
                f"Pwd={self.password};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
                f"Connection Timeout=30;"
            )
        else:
            logger.warning("⚠️ Azure SQL Database 연결 정보가 .env 파일에 설정되지 않았습니다.")
            logger.warning("   데이터베이스 저장 기능이 비활성화됩니다.")
    
    def get_connection(self):
        """데이터베이스 연결 객체 반환"""
        if not self.connection_string:
            return None
        
        try:
            conn = pyodbc.connect(self.connection_string)
            logger.info("✅ Azure SQL Database 연결 성공")
            return conn
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
            return None
    
    def create_tables(self):
        """필요한 테이블들을 생성하는 함수"""
        conn = self.get_connection()
        if not conn:
            logger.warning("⚠️ 데이터베이스 연결 실패로 테이블 생성 건너뜀")
            return False
        
        try:
            cursor = conn.cursor()
            
            # 영수증 메인 테이블
            create_receipts_table = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[receipts]') AND type in (N'U'))
            CREATE TABLE [dbo].[receipts] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [user_id] NVARCHAR(255) NOT NULL,
                [store_name] NVARCHAR(255),
                [category] NVARCHAR(50),
                [total_amount] DECIMAL(18,2),
                [purchase_date] DATE,
                [normalized_date] DATE,
                [status_code] INT,
                [items_count] INT,
                [image_filename] NVARCHAR(500),
                [extracted_text] NVARCHAR(MAX),
                [created_at] DATETIME2 DEFAULT GETDATE(),
                [updated_at] DATETIME2 DEFAULT GETDATE()
            );
            """
            
            # 영수증 품목 테이블
            create_items_table = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[receipt_items]') AND type in (N'U'))
            CREATE TABLE [dbo].[receipt_items] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [receipt_id] INT NOT NULL,
                [item_name] NVARCHAR(500) NOT NULL,
                [price] DECIMAL(18,2),
                [quantity] INT,
                [created_at] DATETIME2 DEFAULT GETDATE(),
                FOREIGN KEY ([receipt_id]) REFERENCES [dbo].[receipts]([id]) ON DELETE CASCADE
            );
            """
            
            # NLP 분석 결과 테이블
            create_nlp_table = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[receipt_nlp_analysis]') AND type in (N'U'))
            CREATE TABLE [dbo].[receipt_nlp_analysis] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [receipt_id] INT NOT NULL,
                [sentiment] NVARCHAR(50),
                [key_phrases] NVARCHAR(MAX),
                [entities] NVARCHAR(MAX),
                [insights] NVARCHAR(MAX),
                [created_at] DATETIME2 DEFAULT GETDATE(),
                FOREIGN KEY ([receipt_id]) REFERENCES [dbo].[receipts]([id]) ON DELETE CASCADE
            );
            """
            
            # 인덱스 생성
            create_indexes = """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_receipts_user_id' AND object_id = OBJECT_ID('receipts'))
            CREATE INDEX IX_receipts_user_id ON [dbo].[receipts]([user_id]);
            
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_receipts_purchase_date' AND object_id = OBJECT_ID('receipts'))
            CREATE INDEX IX_receipts_purchase_date ON [dbo].[receipts]([purchase_date]);
            
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_receipts_category' AND object_id = OBJECT_ID('receipts'))
            CREATE INDEX IX_receipts_category ON [dbo].[receipts]([category]);
            """
            
            cursor.execute(create_receipts_table)
            cursor.execute(create_items_table)
            cursor.execute(create_nlp_table)
            cursor.execute(create_indexes)
            conn.commit()
            
            logger.info("✅ 데이터베이스 테이블 생성 완료")
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ 테이블 생성 실패: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    def save_receipt(self, receipt_data: Dict) -> Optional[int]:
        """
        영수증 분석 결과를 데이터베이스에 저장
        
        Args:
            receipt_data: 영수증 분석 결과 딕셔너리
                {
                    "user_id": str,
                    "store_name": str,
                    "category": str,
                    "amount": str,
                    "date": str (YYYY-MM-DD),
                    "status_code": int,
                    "items": List[Dict],
                    "items_count": int,
                    "image_filename": str,
                    "extracted_text": str,
                    "nlp_analysis": Dict (optional)
                }
        
        Returns:
            저장된 영수증의 ID 또는 None
        """
        conn = self.get_connection()
        if not conn:
            logger.warning("⚠️ 데이터베이스 연결 실패로 저장 건너뜀")
            return None
        
        try:
            cursor = conn.cursor()
            
            # 날짜 변환
            purchase_date = None
            normalized_date = None
            if receipt_data.get("date"):
                try:
                    normalized_date = datetime.strptime(receipt_data["date"], "%Y-%m-%d").date()
                    purchase_date = normalized_date
                except:
                    pass
            
            # 금액 변환
            total_amount = None
            if receipt_data.get("amount"):
                try:
                    total_amount = float(receipt_data["amount"].replace(",", ""))
                except:
                    pass
            
            # 영수증 메인 정보 삽입
            insert_receipt = """
            INSERT INTO [dbo].[receipts] 
            (user_id, store_name, category, total_amount, purchase_date, normalized_date, 
             status_code, items_count, image_filename, extracted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            SELECT SCOPE_IDENTITY();
            """
            
            cursor.execute(
                insert_receipt,
                (
                    receipt_data.get("user_id", "anonymous"),
                    receipt_data.get("store_name"),
                    receipt_data.get("category"),
                    total_amount,
                    purchase_date,
                    normalized_date,
                    receipt_data.get("status_code", 200),
                    receipt_data.get("items_count", 0),
                    receipt_data.get("image_filename"),
                    receipt_data.get("extracted_text", "")[:4000]  # NVARCHAR(MAX)지만 안전을 위해 제한
                )
            )
            
            receipt_id = cursor.fetchone()[0]
            
            # 품목 정보 삽입
            items = receipt_data.get("items", [])
            if items:
                insert_item = """
                INSERT INTO [dbo].[receipt_items] (receipt_id, item_name, price, quantity)
                VALUES (?, ?, ?, ?);
                """
                
                for item in items:
                    item_price = None
                    if item.get("price"):
                        try:
                            item_price = float(str(item["price"]).replace(",", ""))
                        except:
                            pass
                    
                    quantity = None
                    if item.get("quantity"):
                        try:
                            quantity = int(item["quantity"])
                        except:
                            pass
                    
                    cursor.execute(
                        insert_item,
                        (
                            receipt_id,
                            item.get("name", ""),
                            item_price,
                            quantity
                        )
                    )
            
            # NLP 분석 결과 삽입 (있는 경우)
            nlp_analysis = receipt_data.get("nlp_analysis")
            if nlp_analysis:
                import json
                insert_nlp = """
                INSERT INTO [dbo].[receipt_nlp_analysis] 
                (receipt_id, sentiment, key_phrases, entities, insights)
                VALUES (?, ?, ?, ?, ?);
                """
                
                key_phrases_str = None
                entities_str = None
                insights_str = None
                
                if nlp_analysis.get("key_phrases"):
                    key_phrases_str = json.dumps(nlp_analysis["key_phrases"], ensure_ascii=False)
                if nlp_analysis.get("entities"):
                    entities_str = json.dumps(nlp_analysis["entities"], ensure_ascii=False)
                if nlp_analysis.get("insights"):
                    insights_str = json.dumps(nlp_analysis["insights"], ensure_ascii=False)
                
                cursor.execute(
                    insert_nlp,
                    (
                        receipt_id,
                        nlp_analysis.get("sentiment"),
                        key_phrases_str,
                        entities_str,
                        insights_str
                    )
                )
            
            conn.commit()
            logger.info(f"✅ 영수증 데이터 저장 완료 (ID: {receipt_id})")
            
            cursor.close()
            conn.close()
            return receipt_id
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 저장 실패: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
                conn.close()
            return None
    
    def get_receipts_by_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """
        사용자 ID로 영수증 목록 조회
        
        Args:
            user_id: 사용자 ID
            limit: 최대 조회 개수
        
        Returns:
            영수증 목록 리스트
        """
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            query = """
            SELECT TOP (?) 
                id, user_id, store_name, category, total_amount, 
                purchase_date, normalized_date, status_code, items_count, 
                image_filename, created_at
            FROM [dbo].[receipts]
            WHERE user_id = ?
            ORDER BY created_at DESC;
            """
            
            cursor.execute(query, (limit, user_id))
            rows = cursor.fetchall()
            
            receipts = []
            for row in rows:
                receipts.append({
                    "id": row[0],
                    "user_id": row[1],
                    "store_name": row[2],
                    "category": row[3],
                    "total_amount": float(row[4]) if row[4] else None,
                    "purchase_date": row[5].isoformat() if row[5] else None,
                    "normalized_date": row[6].isoformat() if row[6] else None,
                    "status_code": row[7],
                    "items_count": row[8],
                    "image_filename": row[9],
                    "created_at": row[10].isoformat() if row[10] else None
                })
            
            cursor.close()
            conn.close()
            return receipts
            
        except Exception as e:
            logger.error(f"❌ 영수증 조회 실패: {e}")
            if conn:
                conn.close()
            return []


# 전역 데이터베이스 연결 인스턴스
db = DatabaseConnection()

