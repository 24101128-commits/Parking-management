# -*- coding: utf-8 -*-
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import uuid
import hashlib
import threading
import cv2
from ultralytics import YOLO
import easyocr
from PIL import Image, ImageTk, ImageDraw, ImageFont
import qrcode
import winsound  # Âm thanh thông báo (Windows)

# ========================== TẢI MODEL ==========================
print("Đang tải AI nhận diện biển số & loại xe... (chỉ lần đầu)")
yolo_model = YOLO("yolov8n.pt")
ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)

# ========================== DỮ LIỆU ==========================
class TrangThai:
    CHO_DUYET = "Chờ duyệt"
    DA_DUYET = "Đã duyệt"
    BI_KHOA = "Bị khóa"

class NguoiDung:
    def __init__(self, ten, mk, email, vai_tro="KHACH"):
        self.id = len(danh_sach_nguoi_dung) + 1
        self.ten_dang_nhap = ten
        self.mat_khau_hash = hashlib.sha256(mk.encode()).hexdigest()
        self.email = email
        self.vai_tro = vai_tro  # ADMIN, NHANVIEN, KHACH
        self.trang_thai = TrangThai.CHO_DUYET if vai_tro in ["KHACH", "NHANVIEN"] else TrangThai.DA_DUYET
        self.bien_so_mac_dinh = ""

class VeDoXe:
    def __init__(self, bien_so, loai_xe, khach=None):
        self.id = str(uuid.uuid4())[-8:]
        self.bien_so = bien_so.upper().replace(" ", "")
        self.loai_xe = loai_xe
        self.khach = khach
        self.thoi_gian_vao = datetime.now()
        self.thoi_gian_ra = None
        self.qr_code = self.tao_qr()

    def tao_qr(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"VE:{self.id}|BIEN:{self.bien_so}|VAO:{self.thoi_gian_vao}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(f"qr_{self.id}.png")
        return f"qr_{self.id}.png"

    def tinh_tien(self):
        if not self.thoi_gian_ra: return 0
        gio = (self.thoi_gian_ra - self.thoi_gian_vao).total_seconds() / 3600
        gia = {"Xe máy": 5000, "Ô tô 4 chỗ": 20000, "Ô tô 7 chỗ": 30000}
        base = gia.get(self.loai_xe, 5000)
        return max(base, base * int(gio))

# Danh sách
danh_sach_nguoi_dung = []
danh_sach_ve = []
tong_cho = 200
cho_trong = tong_cho

# Tạo admin mặc định
if not any(u.vai_tro == "ADMIN" for u in danh_sach_nguoi_dung):
    danh_sach_nguoi_dung.append(NguoiDung("admin", "admin123", "admin@baidoxe.vn", "ADMIN"))

current_user = None

# ========================== NHẬN DIỆN ==========================
def nhan_dien(frame):
    small = cv2.resize(frame, (640, 480))
    results = yolo_model(small, classes=[2,3,5,7], verbose=False)
    loai = "Xe máy"
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if cls == 3: loai = "Xe máy"
            elif cls == 7: loai = "Ô tô 7 chỗ"
            else: loai = "Ô tô 4 chỗ"

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    ocr = ocr_reader.readtext(gray, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ- ')
    bien = ""
    for (_, text, conf) in ocr:
        t = text.replace(" ", "").upper()
        if len(t) >= 6 and conf > 0.5:
            bien = t
            break
    return bien if len(bien) >= 6 else "KHÔNG ĐỌC ĐƯỢC", loai

# ========================== GIAO DIỆN CHÍNH ==========================
class SmartParkingPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMART PARKING PRO - BÃI ĐỖ XE THÔNG MINH 2025")
        self.geometry("1400x900")
        self.configure(bg="#1a1a1a")
        self.current_user = None
        self.cap = cv2.VideoCapture(0)

        self.trang_dang_nhap()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def trang_dang_nhap(self):
        self.clear()
        tk.Label(self, text="SMART PARKING PRO", font=("Arial", 30, "bold"), fg="#00ff00", bg="#1a1a1a").pack(pady=50)
        tk.Label(self, text=f"Chỗ trống: {cho_trong}/{tong_cho}", font=("Arial", 24), fg="cyan", bg="#1a1a1a").pack(pady=20)

        frame = ttk.Frame(self)
        frame.pack(pady=30)

        ttk.Button(frame, text="ĐĂNG KÝ TÀI KHOẢN", width=40, command=self.trang_dang_ky).grid(row=0, column=0, pady=15)
        ttk.Button(frame, text="ĐĂNG NHẬP NHÂN VIÊN", width=40, command=self.dang_nhap_nhan_vien).grid(row=1, column=0, pady=15)
        ttk.Button(frame, text="ĐĂNG NHẬP ADMIN", width=40, command=self.dang_nhap_admin).grid(row=2, column=0, pady=15)
        ttk.Button(frame, text="XEM CAMERA (Khách vãng lai)", width=40, command=self.trang_camera_khach).grid(row=3, column=0, pady=15)

    def trang_dang_ky(self):
        self.clear()
        tk.Label(self, text="ĐĂNG KÝ TÀI KHOẢN NHÂN VIÊN / KHÁCH", font=("Arial", 20), fg="yellow", bg="#1a1a1a").pack(pady=30)

        form = ttk.Frame(self)
        form.pack(pady=20)

        ttk.Label(form, text="Tên đăng nhập:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        e1 = ttk.Entry(form, width=40); e1.grid(row=0, column=1)
        ttk.Label(form, text="Mật khẩu:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        e2 = ttk.Entry(form, width=40, show="*"); e2.grid(row=1, column=1)
        ttk.Label(form, text="Email:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        e3 = ttk.Entry(form, width=40); e3.grid(row=2, column=1)
        ttk.Label(form, text="Vai trò:").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        role = ttk.Combobox(form, values=["KHACH", "NHANVIEN"], width=37); role.set("KHACH"); role.grid(row=3, column=1)

        def dang_ky():
            if not all([e1.get(), e2.get(), e3.get()]):
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ!")
                return
            user = NguoiDung(e1.get(), e2.get(), e3.get(), role.get())
            danh_sach_nguoi_dung.append(user)
            messagebox.showinfo("Thành công", "Đăng ký thành công! Chờ Admin phê duyệt.")
            self.trang_dang_nhap()

        ttk.Button(self, text="ĐĂNG KÝ", command=dang_ky).pack(pady=30)
        ttk.Button(self, text="Quay lại", command=self.trang_dang_nhap).pack()

    def dang_nhap_nhan_vien(self):
        ten = simpledialog.askstring("Nhân viên", "Tên đăng nhập:")
        mk = simpledialog.askstring("Nhân viên", "Mật khẩu:", show="*")
        user = next((u for u in danh_sach_nguoi_dung if u.ten_dang_nhap == ten and u.mat_khau_hash == hashlib.sha256(mk.encode()).hexdigest()), None)
        if user and user.trang_thai == TrangThai.DA_DUYET and user.vai_tro in ["NHANVIEN", "ADMIN"]:
            self.current_user = user
            self.trang_nhan_vien()
        else:
            messagebox.showerror("Lỗi", "Sai thông tin hoặc tài khoản chưa được duyệt!")

    def dang_nhap_admin(self):
        mk = simpledialog.askstring("ADMIN", "Mật khẩu Admin:", show="*")
        if hashlib.sha256(mk.encode()).hexdigest() == hashlib.sha256("admin123".encode()).hexdigest():
            self.current_user = next(u for u in danh_sach_nguoi_dung if u.vai_tro == "ADMIN")
            self.trang_admin()

    def trang_admin(self):
        self.clear()
        tk.Label(self, text="TRANG QUẢN TRỊ ADMIN", font=("Arial", 24, "bold"), fg="red", bg="#1a1a1a").pack(pady=30)

        tree = ttk.Treeview(self, columns=("ID", "Tên", "Email", "Vai trò", "Trạng thái"), show="headings", height=15)
        for col in tree["columns"]:
            tree.heading(col, text=col); tree.column(col, width=150, anchor="center")
        tree.pack(pady=20)

        def load():
            for i in tree.get_children(): tree.delete(i)
            for u in danh_sach_nguoi_dung:
                tree.insert("", "end", values=(u.id, u.ten_dang_nhap, u.email, u.vai_tro, u.trang_thai))

        def phe_duyet():
            sel = tree.selection()
            if sel:
                uid = int(tree.item(sel[0])["values"][0])
                for u in danh_sach_nguoi_dung:
                    if u.id == uid:
                        u.trang_thai = TrangThai.DA_DUYET
                        messagebox.showinfo("OK", f"Đã duyệt: {u.ten_dang_nhap}")
                        load()

        load()
        ttk.Button(self, text="Phê duyệt", command=phe_duyet).pack(pady=10)
        ttk.Button(self, text="Quay lại", command=self.trang_dang_nhap).pack(pady=10)

    def thong_bao_xe_ra(self, ve):
        winsound.Beep(1000, 500)  # Âm thanh thông báo
        msg = f"XIN MỜI XE BIỂN SỐ\n{ve.bien_so}\nRA CỔNG!\nTỔNG TIỀN: {ve.tinh_tien():,} VNĐ"
        messagebox.showwarning("XE RA!", msg)
        # Có thể thêm gửi SMS qua Viettel SMS API ở đây

    def trang_camera_khach(self):
        self.clear()
        self.lbl_video = tk.Label(self, bg="black")
        self.lbl_video.pack(pady=20)
        self.lbl_info = tk.Label(self, text="Đang nhận diện...", font=("Arial", 20), fg="yellow", bg="#1a1a1a")
        self.lbl_info.pack(pady=10)

        def cap_thread():
            while True:
                ret, frame = self.cap.read()
                if ret:
                    bien, loai = nhan_dien(frame)
                    self.lbl_info.config(text=f"Biển: {bien} | Loại: {loai}")
                    cv2.putText(frame, bien, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 4)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(img)
                    self.lbl_video.imgtk = imgtk
                    self.lbl_video.config(image=imgtk)
        threading.Thread(target=cap_thread, daemon=True).start()

        ttk.Button(self, text="XE VÀO", command=lambda: self.xe_vao(bien), width=30).pack(side="left", padx=50, pady=50)
        ttk.Button(self, text="XE RA", command=lambda: self.xe_ra(bien), width=30).pack(side="right", padx=50, pady=50)
        ttk.Button(self, text="Quay lại", command=self.trang_dang_nhap).pack(pady=20)

    def xe_vao(self, bien):
        global cho_trong
        if cho_trong <= 0:
            messagebox.showwarning("Hết chỗ", "Bãi đã đầy!")
            return
        if bien == "KHÔNG ĐỌC ĐƯỢC":
            messagebox.showerror("Lỗi", "Không đọc được biển số!")
            return
        ve = VeDoXe(bien, "Ô tô 4 chỗ")
        danh_sach_ve.append(ve)
        cho_trong -= 1
        messagebox.showinfo("THÀNH CÔNG", f"Xe {bien} đã vào bãi!\nMã vé: {ve.id}\nVé QR đã lưu!")

    def xe_ra(self, bien):
        global cho_trong
        ve = next((v for v in danh_sach_ve if v.bien_so == bien and v.thoi_gian_ra is None), None)
        if not ve:
            messagebox.showerror("Lỗi", "Không tìm thấy xe trong bãi!")
            return
        ve.thoi_gian_ra = datetime.now()
        cho_trong += 1
        self.thong_bao_xe_ra(ve)

if __name__ == "__main__":
    app = SmartParkingPro()
    app.mainloop()