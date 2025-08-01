from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta

# Khởi tạo Flask app
app = Flask(__name__)


# Đường dẫn cố định đến file Excel trên máy bạn
# Sau này phải thay đổi vị trí của ổ đĩa để trả kết quả
EXCEL_PATH = r"C:\Users\Duy To\Inventory_control\Khuon_duc.xlsx"

@app.route("/")
def home():
    return redirect("/login")

# Đặt khóa bí mật để dùng session (bắt buộc)
app.secret_key = "bat-ky-chuoi-bi-mat"
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None  # Biến lưu thông báo lỗi nếu có

    if request.method == "POST":
        # 🔍 Lấy mã nhân viên từ form
        ma_nhan_vien = request.form.get("employee_code").strip()

        # 📄 Đọc danh sách nhân viên từ Excel
        df_nv = pd.read_excel("Danh_sach_nhan_vien.xlsx", sheet_name="Sheet1")

        # Kiểm tra cột "Number" tồn tại và mã hợp lệ
        if ma_nhan_vien in df_nv["Number"].astype(str).values:
            # ✅ Nếu mã hợp lệ → lấy tên tương ứng
            ten = df_nv.loc[df_nv["Number"].astype(str) == ma_nhan_vien, "Tên nhân viên"].values[0]

            # 💾 Lưu mã và tên vào session để dùng toàn bộ phiên làm việc
            session["ma_nhan_vien"] = ma_nhan_vien
            session["ten_nhan_vien"] = ten

            # 👉 Chuyển sang trang dashboard (trang chính sau đăng nhập)
            return redirect(url_for("dashboard"))
        else:
            # ❌ Mã không hợp lệ
            error = "Mã nhân viên không tồn tại!"

    # 🖼 Hiển thị form login (hoặc lỗi nếu có)
    return render_template("login.html", error=error)




@app.route("/dashboard")
def dashboard():
    # 🔒 Kiểm tra nếu chưa đăng nhập, quay lại /login
    if "ma_nhan_vien" not in session:
        return redirect("/login")

    # ✅ Đã đăng nhập → truyền mã + tên nhân viên vào HTML
    return render_template(
        "dashboard.html",
        ma_nhan_vien=session.get("ma_nhan_vien"),
        ten_nhan_vien=session.get("ten_nhan_vien")
    )





# Sửa lại route /borrow trong app.py
# Cập nhật route /borrow để hiển thị thông tin người mượn
@app.route("/borrow", methods=["GET", "POST"])
def muon_hang():
    # 🔒 Kiểm tra nếu chưa đăng nhập → quay lại trang login
    if "ma_nhan_vien" not in session:
        return redirect("/login")

    thong_tin = None
    thong_bao = ""
    mau_trang_thai = ""
    icon = ""
    trang_thai = ""
    tile = ""
    
    # 🔍 XỬ LÝ KHI NGƯỜI DÙNG TÌM KIẾM SẢN PHẨM
    if request.method == "GET" and request.args.get("code"):
        code = request.args.get("code")
        df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")

        if code in df["Code"].astype(str).values:
            # ✅ Nếu code tồn tại → lấy thông tin sản phẩm
            row = df[df["Code"].astype(str) == code].iloc[0].to_dict()
            thong_tin = row
            
            # 🎨 Xử lý hiển thị trạng thái
            if pd.notna(thong_tin.get("Tình trạng")) and thong_tin["Tình trạng"] == "Available":
                # ✅ Khả dụng - cho phép mượn
                mau_trang_thai = "green"
                icon = "✅"
                trang_thai = "Khả dụng"
                tile = "100"
                
            elif pd.notna(thong_tin.get("Tình trạng")) and thong_tin["Tình trạng"] == "Unavailable":
                # ❌ Không khả dụng - kiểm tra người mượn
                mau_trang_thai = "red"
                icon = "❌"
                tile = "0"
                
                # Kiểm tra có thông tin người mượn không
                nguoi_muon = thong_tin.get("Người mượn", "")
                ngay_lay_hang = thong_tin.get("Ngày lấy hàng", "")
                
                if pd.notna(nguoi_muon) and str(nguoi_muon).strip() and str(nguoi_muon) != "nan":
                    # Có người mượn
                    if pd.notna(ngay_lay_hang) and str(ngay_lay_hang) != "nan":
                        trang_thai = f"Sản phẩm không khả dụng - {nguoi_muon} đã mượn hàng ngày {ngay_lay_hang}"
                    else:
                        trang_thai = f"Sản phẩm không khả dụng - {nguoi_muon} đã mượn hàng"
                else:
                    # Không có thông tin người mượn
                    trang_thai = "Không có mẫu trong kho"
            else:
                # Trạng thái không xác định
                mau_trang_thai = "orange"
                icon = "⚠️"
                trang_thai = "Trạng thái không xác định"
                tile = "50"
        else:
            # ❌ Không tìm thấy sản phẩm
            thong_bao = "❌ Mã sản phẩm không tồn tại!"

    # 📤 Trả về trang HTML
    return render_template("borrow.html", 
                         thong_tin=thong_tin, 
                         thong_bao=thong_bao,
                         mau_trang_thai=mau_trang_thai,
                         icon=icon,
                         trang_thai=trang_thai,
                         tile=tile)







# Thêm route xử lý xác nhận mượn hàng (từ form POST trong borrow.html)

# Phương án đơn giản hơn - chỉ dùng redirect (không có alert)
@app.route("/muon-xac-nhan", methods=["POST"])
def muon_xac_nhan():
    if "ma_nhan_vien" not in session:
        return redirect("/login")
    
    code = request.form.get("code")
    anh_muon = request.files.get("anh_muon")
    
    try:
        # Đọc file Excel sản phẩm và nhân viên
        df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
        mask = df["Code"].astype(str) == str(code)
        
        df_nv = pd.read_excel("Danh_sach_nhan_vien.xlsx", sheet_name="Sheet1")
        ma_nhan_vien = session.get("ma_nhan_vien")
        ten_nguoi_muon = df_nv.loc[df_nv["Number"].astype(str) == ma_nhan_vien, "Tên nhân viên"].values[0]
        
        if mask.any():
            # Cập nhật thông tin
            df.loc[mask, "Tình trạng"] = "Unavailable"
            df.loc[mask, "Ngày lấy hàng"] = datetime.now().strftime("%Y-%m-%d")
            df.loc[mask, "Người mượn"] = ten_nguoi_muon
            
            # Tăng số lần đã sử dụng
            so_lan_cu = df.loc[mask, "Số lần đã sử dụng"].values[0] if "Số lần đã sử dụng" in df.columns else 0
            if pd.isna(so_lan_cu) or str(so_lan_cu) == "nan":
                df.loc[mask, "Số lần đã sử dụng"] = 1
            else:
                df.loc[mask, "Số lần đã sử dụng"] = int(so_lan_cu) + 1
            
            # Xử lý ảnh MƯỢN
            if anh_muon and anh_muon.filename:
                # Lưu vào đúng thư mục borrow
                upload_folder = "static/images/borrow"
                os.makedirs(upload_folder, exist_ok=True)
                # Đặt tên file: CODE_HoTenNguoiMuon.jpg
                ten_nguoi_muon = session.get("ten_nhan_vien", "Unknown")
                safe_ten = ''.join(c for c in ten_nguoi_muon if c.isalnum() or c in [' ', '_']).replace(" ", "_")
                filename = f"{code}_{safe_ten}.jpg"
                filepath = os.path.join(upload_folder, filename)
                # Xóa ảnh cũ nếu có
                old_img = df.loc[mask, "Ảnh mượn"].values[0] if "Ảnh mượn" in df.columns else ""
                if pd.notna(old_img) and old_img and old_img != filename:
                    old_path = os.path.join(upload_folder, str(old_img))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                # Lưu ảnh mới
                anh_muon.save(filepath)
                df.loc[mask, "Ảnh mượn"] = filename
            else:
                df.loc[mask, "Ảnh mượn"] = ""
            
            # Lưu file
            df.to_excel(EXCEL_PATH, sheet_name="Sheet1", index=False)
            
        return redirect("/dashboard")  # Đơn giản chỉ redirect về dashboard
            
    except Exception as e:
        print(f"Lỗi: {e}")  # In lỗi ra console
        return redirect("/borrow")






# THÊM VÀO APP.PY - TÍNH NĂNG MƯỢN HÀNG BẰNG QR

# Import thêm
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta

# Route tạo QR code cho mượn hàng
@app.route('/create_borrow_qr/<ma_khuon>')
def create_borrow_qr(ma_khuon):
    try:
        # Tìm thông tin khuôn đúc
        khuon_info = df_khuon_duc[df_khuon_duc['Mã khuôn'] == ma_khuon].iloc[0]
        
        # Tạo QR data với thông tin mượn hàng
        qr_data = {
            'action': 'borrow',
            'ma_khuon': ma_khuon,
            'ten_khuon': khuon_info['Tên khuôn'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Chuyển thành JSON string
        qr_text = f"BORROW:{ma_khuon}:{khuon_info['Tên khuôn']}"
        
        # Tạo QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        # Tạo hình ảnh QR
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert sang base64 để hiển thị
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return render_template('qr_borrow.html', 
                             qr_code=qr_base64,
                             ma_khuon=ma_khuon,
                             ten_khuon=khuon_info['Tên khuôn'],
                             so_luong=khuon_info['Số lượng'])
                             
    except Exception as e:
        return f"Lỗi tạo QR: {str(e)}"

# Route xử lý scan QR để mượn
@app.route('/scan_borrow', methods=['GET', 'POST'])
def scan_borrow():
    if request.method == 'POST':
        qr_data = request.form.get('qr_data')
        nguoi_muon = request.form.get('nguoi_muon')
        so_luong_muon = int(request.form.get('so_luong_muon', 1))
        
        try:
            # Parse QR data: "BORROW:MA001:Tên khuôn"
            parts = qr_data.split(':')
            if parts[0] != 'BORROW':
                return "QR code không hợp lệ!"
                
            ma_khuon = parts[1]
            
            # Kiểm tra khuôn tồn tại
            khuon_idx = df_khuon_duc[df_khuon_duc['Mã khuôn'] == ma_khuon].index
            if len(khuon_idx) == 0:
                return "Không tìm thấy khuôn!"
                
            # Kiểm tra số lượng có đủ không
            current_qty = df_khuon_duc.loc[khuon_idx[0], 'Số lượng']
            if current_qty < so_luong_muon:
                return f"Không đủ số lượng! Hiện có: {current_qty}"
            
            # Cập nhật số lượng khuôn
            df_khuon_duc.loc[khuon_idx[0], 'Số lượng'] -= so_luong_muon
            
            # Lưu lại file Excel
            df_khuon_duc.to_excel('Khuon_duc.xlsx', index=False)
            
            # Ghi log mượn hàng
            log_muon = {
                'Thời gian': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Mã khuôn': ma_khuon,
                'Tên khuôn': parts[2],
                'Người mượn': nguoi_muon,
                'Số lượng mượn': so_luong_muon,
                'Trạng thái': 'Đang mượn'
            }
            
            # Thêm vào file log (tạo mới nếu chưa có)
            try:
                df_log = pd.read_excel('Log_muon_hang.xlsx')
                df_log = pd.concat([df_log, pd.DataFrame([log_muon])], ignore_index=True)
            except:
                df_log = pd.DataFrame([log_muon])
            
            df_log.to_excel('Log_muon_hang.xlsx', index=False)
            
            return render_template('borrow_success.html', 
                                 ma_khuon=ma_khuon,
                                 ten_khuon=parts[2],
                                 nguoi_muon=nguoi_muon,
                                 so_luong=so_luong_muon)
                                 
        except Exception as e:
            return f"Lỗi xử lý mượn hàng: {str(e)}"
    
    return render_template('scan_borrow.html')

# Route xem lịch sử mượn hàng
@app.route('/borrow_history')
def borrow_history():
    try:
        df_log = pd.read_excel('Log_muon_hang.xlsx')
        records = df_log.to_dict('records')
        return render_template('borrow_history.html', records=records)
    except:
        return render_template('borrow_history.html', records=[])







@app.route("/return", methods=["GET", "POST"])
def return_item():
    thong_bao = ""
    thong_tin = None
    image_path = None
    available_positions = []
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        df = pd.read_excel(EXCEL_PATH)
        if code not in df["Code"].astype(str).values:
            thong_bao = "❌ Mã không tồn tại"
        else:
            row = df[df["Code"].astype(str) == code].iloc[0]
            if row["Tình trạng"] == "Available":
                thong_bao = "❌ Sản phẩm đang tồn tại trong kho"
            else:
                thong_tin = row.to_dict()
                image_path = row.get("Ảnh mượn", None)
                used_pos = df[df["Vị trí"].notna()]["Vị trí"].tolist()
                all_pos = [f"{i}{chr(c)}{j}" for i in range(1, 10) for c in range(ord("A"), ord("Z")+1) for j in range(1, 10)]
                available_positions = [pos for pos in all_pos if pos not in used_pos]
    return render_template("return.html", thong_bao=thong_bao, thong_tin=thong_tin, image_path=image_path, available_positions=available_positions)





@app.route("/return/confirm", methods=["POST"])
def return_confirm():
    code = request.form.get("code")
    vi_tri = request.form.get("vi_tri").strip().upper()
    anh_tra = request.files.get("anh_tra")
    df = pd.read_excel(EXCEL_PATH)
    # Kiểm tra vị trí
    if vi_tri in df["Vị trí"].astype(str).values:
        return "❌ Đã hết chỗ"  # Có thể render ra template lỗi tùy ý
    mask = df["Code"].astype(str) == code
    if not mask.any():
        return "❌ Mã không tồn tại"
    # Lưu ảnh
    folder = "static/images_return"
    os.makedirs(folder, exist_ok=True)
    img_name = f"{code}_{vi_tri}.jpg"
    img_path = os.path.join(folder, img_name)
    anh_tra.save(img_path)
    # Cập nhật Excel
    now = datetime.now().strftime("%Y-%m-%d")
    df.loc[mask, "Tình trạng"] = "Available"
    df.loc[mask, "Vị trí"] = vi_tri
    df.loc[mask, "Ngày trả"] = now
    df.loc[mask, "Người trả"] = session.get("ten_nhan_vien")  # Nếu dùng session login
    df.loc[mask, "Ảnh trả"] = img_name
    df.to_excel(EXCEL_PATH, index=False)
    # Hiện chi tiết sản phẩm đã trả
    thong_tin = df[mask].iloc[0].to_dict()
    return render_template("return_success.html", thong_tin=thong_tin)








@app.route("/inventory")
def show_inventory():
    # 🔒 Kiểm tra nếu chưa đăng nhập thì chuyển về trang login
    if "ma_nhan_vien" not in session:
        return redirect("/login")

    # 📄 Đọc dữ liệu từ Excel
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")




# Lấy thông tin phân trang từ URL (?page=1, 2, ...)
    page = int(request.args.get("page", 1))
    per_page = 15
    start = (page - 1) * per_page
    end = start + per_page

    # Cắt dữ liệu theo trang
    df_page = df.iloc[start:end]

    # Chuyển thành list dict để truyền sang HTML
    data = df_page.to_dict(orient="records")
    columns = df.columns.tolist()

    # Tính tổng số trang
    total_pages = (len(df) + per_page - 1) // per_page

    return render_template(
        "inventory.html",
        data=data,
        columns=columns,
        current_page=page,
        total_pages=total_pages
    )








# 📦 ROUTE mới để cập nhật "Ngày nhập kho" theo mã hàng
#        @app.route("/nhap-ngay", methods=["GET", "POST"])
#       def nhap_ngay_nhap_kho():
#            # Biến điều khiển hiển thị form nhập ngày
#           hien_form = False
#           ma_tim_duoc = None
#           thong_bao = ""
#
#           # 📁 Đường dẫn tới file Excel cố định
#           # Sau này phải thay đổi vị trí của ổ đĩa để trả kết quả
#            EXCEL_PATH = r"C:\Users\Duy To\Inventory_control\Khuon_duc.xlsx"
#
#            # Khi có thao tác POST (nhấn nút)
#            if request.method == "POST":
#                action = request.form.get("action")  # Xác định nút bấm là "tim" hay "capnhat"
#                code = request.form.get("Code")  # Lấy mã hàng từ ô nhập

                # Đọc dữ liệu từ Excel
#                df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")

                # 🔍 Nếu nhấn "Tìm" mã hàng
#                if action == "tim":
#                   if code in df["Code"].astype(str).values:
#                      hien_form = True  # Cho hiển thị form nhập ngày nếu tìm thấy
#                     ma_tim_duoc = code
#                else:
#                        thong_bao = f"Không tìm thấy mã hàng: {code}"

#                # 💾 Nếu nhấn "Lưu" để cập nhật ngày
#                elif action == "capnhat":
#                    ngay_nhap = request.form.get("ngay_nhap")  # Lấy ngày nhập từ form
#                    # Tìm dòng có mã hàng trùng khớp
#                    mask = df["Code"].astype(str) == str(code)
#                    if mask.any():
#                        # ✅ Ghi đè cột "Ngày nhập kho" tại dòng tương ứng
#                        df.loc[mask, "Ngày nhập kho"] = ngay_nhap
#                        # 💾 Ghi lại vào file Excel
#                        df.to_excel(EXCEL_PATH, sheet_name="Sheet1", index=False)
#                        thong_bao = f"✅ Đã cập nhật ngày nhập kho cho Code {code}"
#                    else:
#                        thong_bao = f"Không tìm thấy mã hàng: {code}"

            # Render HTML, truyền biến điều khiển (form, mã, thông báo)
#            return render_template("nhap_ngay.html",
#                                hien_form=hien_form,
#                                ma_tim_duoc=ma_tim_duoc,
#                                thong_bao=thong_bao)






            #  THỂ HIỆN ngày nhập kho, lấy hàng, trả hàng theo mã code
@app.route("/update-ngay", methods=["POST"])
def update_ngay_bat_ky():
    code = request.form.get("Code")
    cot = request.form.get("cot")  # Tên cột: "Ngày nhập kho", "Ngày lấy hàng", "Ngày trả hàng"
    ngay = request.form.get("ngay")

    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    mask = df["Code"].astype(str) == str(code)

    if mask.any() and cot in df.columns:
        df.loc[mask, cot] = ngay
        df.to_excel(EXCEL_PATH, sheet_name="Sheet1", index=False)

    return redirect("/inventory")  # Quay về trang danh sách hàng tồn kho





# Thể hiện việc thêm sản phẩm trên website
@app.route("/them-san-pham", methods=["POST"])
def them_san_pham():
    hinh_dang = request.form.get("hinh_dang")
    code = request.form.get("code")
    tuoi_tho = request.form.get("tuoi_tho")

    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")

    # ✅ Kiểm tra trùng Code
    if code in df["Code"].astype(str).values:
        print(f"❌ Code {code} đã tồn tại.")
        return redirect("/inventory")  # Có thể xử lý lỗi tốt hơn sau

    # 📦 Tạo dòng mới (các trường còn lại để trống hoặc mặc định)
    new_row = {
        "STT": len(df) + 1,
        "Hình dạng": hinh_dang,
        "Code": code,
        "Ngày nhập kho": "",
        "Ngày lấy hàng": "",
        "Ngày trả hàng": "",
        "Số ngày trong kho": "",
        "Tuổi thọ": tuoi_tho,
        "Số lần đã sử dụng": ""
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_PATH, sheet_name="Sheet1", index=False)
    return redirect("/")




# route đăng xuất
@app.route("/logout")
def logout():
    # 🔄 Xoá toàn bộ session hiện tại (xoá mã và tên nhân viên)
    session.clear()

    # 🔁 Chuyển về trang đăng nhập
    return redirect("/login")





# 🚀 Chạy Flask app
if __name__ == "__main__":
    app.run(debug=True, port=5000)