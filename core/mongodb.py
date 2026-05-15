# Core/mongodb.py
import motor.motor_asyncio
import sys
import logging

class MongoDB:
    def __init__(self, uri: str):
        """
        Khởi tạo lớp quản lý MongoDB Atlas.
        Tiêu chuẩn: Industrial Grade với cơ chế Connection Pooling.
        """
        self.uri = uri
        self.client = None
        self.db = None
        
        # --- CÁC NGĂN CHỨA (COLLECTIONS) ---
        self.embeds = None      # Chứa các thiết kế Embed
        self.configs = None     # Chứa cấu hình Greet/Leave/Booster/Wellcome
        self.identities = None  # Chứa danh tính Webhook (Identities)
        self.tickets = None     # [CẬP NHẬT] Ngăn chứa hệ thống Ticket
        self.forms = None       # [CẬP NHẬT] Ngăn chứa hệ thống Form

    def __getattr__(self, name):
        """
        [ATK - FUTURE PROOF] Proxy tự động kết nối Collection.
        Nếu gọi một collection chưa khai báo (vd: db.logs), bot sẽ tự động trỏ vào DB.
        """
        if self.db is not None:
            return self.db[name]
        raise AttributeError(f"MongoDB layer chưa được kết nối hoặc không có thuộc tính '{name}'")

    async def connect(self):
        """Thiết lập kết nối bất đồng bộ với Cloud Atlas"""
        try:
            # Thiết lập Connection Pool để cân được tải cao (Multi-server)
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=100,      # Giới hạn 100 kết nối đồng thời
                minPoolSize=10,       # Duy trì ít nhất 10 kết nối chờ
                retryWrites=True,
                retryReads=True
            )
            
            # Tên Database chính của hệ thống
            self.db = self.client["peiD_production"]

            # Ánh xạ các ngăn (Collections)
            self.embeds = self.db["embeds"]
            self.configs = self.db["guild_configs"]
            self.identities = self.db["identities"]
            self.tickets = self.db["tickets"]
            self.forms = self.db["forms"]

            # Kiểm tra kết nối bằng lệnh Ping
            await self.client.admin.command('ping')
            print("[DB] Industrial MongoDB Layer: Connected & Ready.", flush=True)

            # Tự động khởi tạo Index để đạt tốc độ truy vấn Max Ping
            await self._create_indexes()

        except Exception as e:
            print(f"[DB FATAL] Không thể kết nối MongoDB: {e}", flush=True)
            # Dừng Bot ngay lập tức nếu DB chết để tránh sai lệch dữ liệu
            sys.exit(1)

    async def _create_indexes(self):
        """
        Tạo Index (Chỉ mục) - Bước sống còn để Bot không bị treo ở server 100k+.
        Giúp tìm kiếm dữ liệu theo Guild ID và Name trong 0.001s.
        """
        try:
            # Index cho Embeds: Tìm theo Server + Tên Embed
            await self.embeds.create_index([("guild_id", 1), ("name", 1)], unique=True)
            
            # Index cho Configs: Tìm theo Server + Module (booster/greet/...)
            await self.configs.create_index([("guild_id", 1), ("module", 1)], unique=True)
            
            # Index cho Identities: Tìm theo Server + Tên gợi nhớ
            await self.identities.create_index([("guild_id", 1), ("name", 1)], unique=True)

            # [DEF - GIA CỐ TICKET/FORM] 
            # Quan trọng: Tạo Index cho embed_name để lệnh dọn dẹp liên hoàn chạy xé gió
            await self.tickets.create_index([("guild_id", 1), ("embed_name", 1)])
            await self.forms.create_index([("guild_id", 1), ("embed_name", 1)])
            
            print("[DB] All indexes synchronized successfully.", flush=True)
        except Exception as e:
            print(f"[DB WARNING] Lỗi khi tạo Index: {e}", flush=True)
