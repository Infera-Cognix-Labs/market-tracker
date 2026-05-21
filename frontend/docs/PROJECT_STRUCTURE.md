# Cấu trúc dự án (Project Structure)

Tài liệu này giải thích cấu trúc thư mục của phần Frontend để giúp các lập trình viên mới dễ dàng làm quen và điều hướng trong mã nguồn.

Dự án được xây dựng trên nền tảng **Next.js** với cơ chế App Router (`app/`).

## Sơ đồ cấu trúc thư mục

```text
frontend/
├── app/                  # Thư mục chính chứa các trang (Pages & Routing) của Next.js
│   ├── layout.tsx        # Layout tổng của toàn bộ ứng dụng
│   ├── page.tsx          # Trang chủ (Homepage)
│   └── ...               # Các route khác (ví dụ: login, dashboard, v.v.)
│
├── components/           # Các reusable components (chia theo tính năng hoặc UI element)
│   ├── dashboard/        # Components dành riêng cho trang Dashboard
│   ├── shared/           # Components dùng chung (Sidebar, Navbar, Buttons...)
│   └── ... 
│
├── docs/                 # (Thư mục này) Chứa tài liệu hướng dẫn về Frontend
│   ├── API_INTEGRATION.md
│   ├── CHANGELOG.md
│   ├── COMPONENTS.md
│   ├── SETUP.md
│   └── PROJECT_STRUCTURE.md
│
├── public/               # Chứa các tài sản (assets) tĩnh như hình ảnh, favicon, fonts
│
├── package.json          # Danh sách thư viện và các script chạy dự án (npm run ...)
├── tailwind.config.*     #/ postcss / eslint # Các cấu hình công cụ (TailwindCSS, ESLint, PostCSS)
└── Dockerfile            # Cấu hình để dockerize Frontend
```

## Quy tắc tổ chức mã nguồn (Convention)

1. **Routing (`app/`)**: Mọi file đóng vai trò là một trang (page) phải được đặt trong thư mục `app/` theo chuẩn App Router của Next.js, đặt tên là `page.tsx`.
2. **Component (`components/`)**: Bất kỳ UI nào được dùng lại ở 2 nơi trở lên hoặc quá phức tạp để đặt chung trong 1 logic page nên được tách ra thành Component.
   - Thư mục components cần được chia nhỏ theo luồng (features) hoặc loại UI.
   - Tránh việc ghép chung mọi components vào một thư mục gốc.
3. **Gọi API**: Được định nghĩa rõ trong `API_INTEGRATION.md`, thường khuyến nghị tạo các module phục vụ việc fetch data riêng (ví dụ thư mục `services/` hoặc `utils/api.ts`).

## Công nghệ sử dụng chính

- **Framework**: Next.js 16
- **UI & Styling**: React 19, TailwindCSS v4
- **Biểu đồ**: Recharts
- **Icon**: Lucide-React
- **Ngôn ngữ**: TypeScript
