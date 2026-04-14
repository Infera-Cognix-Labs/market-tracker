# Hướng dẫn Cài đặt & Khởi chạy (Setup Guide)

Tài liệu này hướng dẫn cách cài đặt, cấu hình và khởi chạy ứng dụng Frontend trên môi trường phát triển cục bộ (Local Development).

## 1. Yêu cầu hệ thống (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo hệ thống của bạn đã cài đặt các công cụ sau:
- **Node.js**: Phiên bản 20.x trở lên (khuyên dùng bản LTS mới nhất).
- **npm** (được cài sẵn cùng Node.js) hoặc **yarn** / **pnpm**.
- **Git** để quản lý mã nguồn.

## 2. Cài đặt dự án

**Bước 1**: Clone dự án về máy (nếu chưa có).
```bash
# Ví dụ về lệnh clone (thay thế bằng URL repo của bạn)
git clone <repository_url>
cd frontend
```

**Bước 2**: Cài đặt các thư viện (Dependencies).
```bash
npm install
```
*(Dự án sử dụng React 19, Next.js 16, TailwindCSS 4, Recharts, Lucide-react).*

## 3. Cấu hình Biến môi trường (Environment Variables)

Nếu dự án yêu cầu kết nối với Backend API hoặc có các cấu hình cụ thể, bạn có thể cần thiết lập file biến môi trường:
1. Tạo một file tên là `.env.local` ở thư mục gốc của frontend.
2. Cấu hình các biến (ví dụ):
   ```env
   # Địa chỉ của API Backend
   NEXT_PUBLIC_API_URL=http://localhost:5000/api
   ```
*(Hãy kiểm tra mã nguồn hoặc thảo luận với team Backend để biết chính xác các biến cần thiết).*

## 4. Chạy dự án (Local Development)

Sau khi đã cài đặt xong, bạn khởi động server phát triển bằng lệnh:

```bash
npm run dev
```

- Trình duyệt sẽ tự động chạy ứng dụng tại địa chỉ: [http://localhost:3000](http://localhost:3000)
- Mọi thay đổi trong mã nguồn sẽ được tự động cập nhật trên trình duyệt (Hot Reloading).

## 5. Build dự án cho Production

Để tối ưu hóa mã nguồn và chạy ứng dụng ở chế độ Production:

**Bước 1: Build mã nguồn**
```bash
npm run build
```

**Bước 2: Chạy server Production**
```bash
npm run start
```
Ứng dụng sẽ chạy với phiên bản được tối ưu hóa tốn ít dung lượng và mang lại hiệu năng cao nhất.

## 6. Sử dụng Docker (Tùy chọn)

Dự án có đi kèm một file `Dockerfile`, cho phép bạn chạy frontend bên trong container:
```bash
# Build Docker image
docker build -t infera-frontend .

# Chạy container
docker run -p 3000:3000 infera-frontend
```

## 7. Các lệnh hữu ích khác

- `npm run lint`: Tìm và báo lỗi cú pháp / coding style bằng ESLint.
