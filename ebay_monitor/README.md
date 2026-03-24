# eBay & BestBuy Monitor Bot

Bot tự động theo dõi giá và tình trạng hàng trên eBay và BestBuy, gửi thông báo qua Telegram.

## Tính năng

- ✅ Theo dõi giá sản phẩm
- ✅ Thông báo khi có hàng/hết hàng
- ✅ Cảnh báo khi sản phẩm bán chạy (eBay)
- ✅ Hỗ trợ eBay (luồng cũ - Playwright headless)
- ✅ Hỗ trợ BestBuy (Omnilogin profile đầu tiên)

## Cài đặt

### 1. Cài đặt Python dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Cài đặt Omnilogin

- Tải và cài đặt Omnilogin từ trang chủ
- Tạo ít nhất 1 profile trong Omnilogin
- Đảm bảo Omnilogin đang chạy (API endpoint: http://localhost:35353)

### 3. Cấu hình Telegram Bot

Tạo file `.env` với nội dung:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 4. Cấu hình URLs cần theo dõi

Tạo file `config.txt` với danh sách URLs (xem `config_example.txt`):

```txt
# eBay URLs
https://www.ebay.com/itm/123456789

# BestBuy URLs
https://www.bestbuy.com/site/product-name/1234567.p
```

## Sử dụng

### Test Omnilogin connection

```bash
python test_omnilogin.py
```

### Test BestBuy scraper

```bash
# Test với visible mode (mặc định - khuyến nghị)
python test_bestbuy.py

# Test với headless mode (BestBuy có thể chặn)
python test_bestbuy.py --headless
```

### Chạy bot

```bash
python bot.py
```

### Cách hoạt động

- **eBay**: Sử dụng Playwright headless (luồng cũ), check mỗi 150 giây (2.5 phút)
- **BestBuy**: Sử dụng profile đầu tiên từ Omnilogin (visible mode), check mỗi 3600 giây (1 giờ)
- Bot tự động phát hiện domain và chọn scraper phù hợp
- Mỗi URL có thời gian check riêng dựa trên platform

### Thông báo Telegram

- **eBay**: Hiển thị số lượt bán, cảnh báo khi bán chạy
- **BestBuy**: Hiển thị số reviews, không có lượt bán
- Tự động hiển thị đúng tên platform (eBay/BestBuy) trong link

## Lưu ý

- Đảm bảo Omnilogin đang chạy trước khi start bot
- Profile đầu tiên trong Omnilogin sẽ được sử dụng cho BestBuy
- eBay vẫn sử dụng luồng cũ (không cần Omnilogin)
- BestBuy yêu cầu browser visible (không thể chạy headless)

## Cấu trúc dự án
