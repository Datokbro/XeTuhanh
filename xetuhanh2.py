import network
import socket
from machine import Pin, PWM, time_pulse_us
import time

# =====================  THONG SO DIEU KHIEN  =====================
TOC_DO_MAX  = 45
TOC_DO_MIN  = 30
TOC_DO_QUAY = 45

KC_BAT_DAU_CHAM = 55.0
KC_DUNG = 16.0
SO_LAN_XAC_NHAN = 2       
DEBUG = True              

T_LUI      = 0.3
T_LUI_KET  = 0.6          
T_RE       = 0.4
T_QUAY_DAU = 0.7

KC_THOANG_TRUOC = 40.0    
GIOI_HAN_XOAY = 1.0
tich_luy_xoay = 0.0       

DAO_MOTOR_TRAI = True     
DAO_MOTOR_PHAI = True     
HOAN_DOI_TRAI_PHAI = False 
DAO_HUONG_RE = False      

# =====================  CHAN NOI ESP32  =====================
CHAN_TRAI = {"in": (2, 4, 16, 17), "ena": 15, "enb": 5}
CHAN_PHAI = {"in": (12, 14, 27, 26), "ena": 13, "enb": 25}

TRIG_PIN = 33
ECHO_PIN = 32

# =====================  KHOI TAO DONG CO  =====================
class BenDongCo:
    def __init__(self, cau_hinh):
        self.i = [Pin(p, Pin.OUT, value=0) for p in cau_hinh["in"]]
        self.pwm_a = PWM(Pin(cau_hinh["ena"]), freq=1000)
        self.pwm_b = PWM(Pin(cau_hinh["enb"]), freq=1000)
        self.pwm_a.duty_u16(0); self.pwm_b.duty_u16(0)
        self.dao = False

    def chay(self, toc_do):
        toc_do = max(-100, min(100, toc_do))
        if self.dao: toc_do = -toc_do
        thuan = 1 if toc_do > 0 else 0
        nguoc = 1 if toc_do < 0 else 0

        self.i[0].value(thuan); self.i[1].value(nguoc)
        self.i[2].value(thuan); self.i[3].value(nguoc)

        xung = int(abs(toc_do) * 65535 / 100)
        self.pwm_a.duty_u16(xung); self.pwm_b.duty_u16(xung)

trai = BenDongCo(CHAN_TRAI)
phai = BenDongCo(CHAN_PHAI)
if HOAN_DOI_TRAI_PHAI: trai, phai = phai, trai
trai.dao = DAO_MOTOR_TRAI
phai.dao = DAO_MOTOR_PHAI

trig = Pin(TRIG_PIN, Pin.OUT, value=0)
echo = Pin(ECHO_PIN, Pin.IN)

# =====================  DO KHOANG CACH  =====================
kc_truoc_do = 100.0
def _do_mot_lan():
    trig.value(0); time.sleep_us(2)
    trig.value(1); time.sleep_us(10)
    trig.value(0)
    t = time_pulse_us(echo, 1, 15000)
    return 200.0 if t < 0 else (t / 58.0)

def do_khoang_cach():
    global kc_truoc_do
    d = _do_mot_lan()
    if abs(d - kc_truoc_do) > 35.0:
        time.sleep_ms(30)
        d = _do_mot_lan()
    kc_truoc_do = d
    return d

def do_khoang_cach_chinh_xac():
    global kc_truoc_do
    ds = [_do_mot_lan() for _ in range(3)]
    ds.sort()
    kc_truoc_do = ds[1]
    return ds[1]

# =====================  DIEU KHIEN DI CHUYEN  =====================
dang_dung_im = True

def dung():
    global dang_dung_im
    trai.chay(0); phai.chay(0)
    dang_dung_im = True

def phanh_chong_troi():
    if not dang_dung_im:
        trai.chay(-TOC_DO_QUAY); phai.chay(-TOC_DO_QUAY)
        time.sleep_ms(80)
    dung()

def chay_thang(toc_do):
    global dang_dung_im
    if dang_dung_im and toc_do > 0:
        trai.chay(65); phai.chay(65)
        time.sleep_ms(40)
        dang_dung_im = False
    trai.chay(toc_do); phai.chay(toc_do)

def lui(giay=0):
    trai.chay(-TOC_DO_QUAY); phai.chay(-TOC_DO_QUAY)
    if giay > 0:
        time.sleep(giay)
        dung()

def xoay_phai(giay=0):
    global tich_luy_xoay
    h = -1 if DAO_HUONG_RE else 1
    trai.chay(h * TOC_DO_QUAY); phai.chay(-h * TOC_DO_QUAY)
    if giay > 0:
        time.sleep(giay)
        dung()
        tich_luy_xoay += giay

def xoay_trai(giay=0):
    global tich_luy_xoay
    h = -1 if DAO_HUONG_RE else 1
    trai.chay(-h * TOC_DO_QUAY); phai.chay(h * TOC_DO_QUAY)
    if giay > 0:
        time.sleep(giay)
        dung()
        tich_luy_xoay -= giay

def xoay_co_gioi_han(huong, giay):
    moi = tich_luy_xoay + (giay if huong == "phai" else -giay)
    if abs(moi) > GIOI_HAN_XOAY: return False
    if huong == "phai": xoay_phai(giay)
    else: xoay_trai(giay)
    return True

def tinh_toc_do(khoang_cach):
    if khoang_cach >= KC_BAT_DAU_CHAM: return TOC_DO_MAX
    elif khoang_cach <= KC_DUNG: return 0
    ty_le = (khoang_cach - KC_DUNG) / (KC_BAT_DAU_CHAM - KC_DUNG)
    return int(TOC_DO_MIN + (ty_le * ty_le) * (TOC_DO_MAX - TOC_DO_MIN))

# =====================  XU LY VAT CAN KHONG SERVO  =====================
quay_dau_ben_phai = True
def xu_ly_vat_can():
    global quay_dau_ben_phai
    phanh_chong_troi(); time.sleep(0.3)
    lan = 0
    while True:
        lan += 1
        can_lui = (lan == 1 or lan % 3 == 0)
        if can_lui: lui(T_LUI_KET if lan >= 2 else T_LUI)
        
        if tich_luy_xoay > 0.3: huong = "trai"
        elif tich_luy_xoay < -0.3: huong = "phai"
        else:
            huong = "phai" if quay_dau_ben_phai else "trai"
            quay_dau_ben_phai = not quay_dau_ben_phai

        da_re = xoay_co_gioi_han(huong, T_RE)
        if not da_re:
            huong_nguoc = "trai" if huong == "phai" else "phai"
            xoay_co_gioi_han(huong_nguoc, T_QUAY_DAU)
        
        time.sleep(0.2)
        d_truoc = do_khoang_cach_chinh_xac()
        if d_truoc > KC_THOANG_TRUOC: return

# =====================  WIFI AP & WEB SERVER  =====================
ap = network.WLAN(network.AP_IF)
ap.config(essid="Xe_Tu_Hanh_ESP32", password="12345678", authmode=3)
ap.active(True)
print("Wi-Fi IP:", ap.ifconfig()[0])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
s.setblocking(False)

HTML = """<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { text-align: center; font-family: sans-serif; user-select: none; }
  .btn { width: 80px; height: 80px; font-size: 18px; margin: 5px; border-radius: 10px; background: #007bff; color: white; border: none; }
  .btn-stop { background: #dc3545; }
  .row { display: flex; justify-content: center; }
  #khoang_cach { color: #555; }
</style>
<script>
  function c(cmd) { fetch('/?cmd=' + cmd); }
  // Tu dong lay khoang cach moi 0.5 giay ma khong reload trang
  setInterval(function() {
    fetch('/?cmd=DIST')
      .then(response => response.text())
      .then(text => { document.getElementById('khoang_cach').innerText = 'Khoảng cách: ' + text + ' cm'; })
      .catch(err => console.log(err));
  }, 500);
</script>
</head><body>
  <h2>Xe ESP32</h2>
  <h3 id="khoang_cach">Khoảng cách: -- cm</h3>
  <button class="btn" style="width:120px; background:#28a745" onclick="c('AUTO')">Tự động</button>
  <button class="btn" style="width:120px; background:#ffc107; color:black" onclick="c('MANUAL')">Chỉnh tay</button>
  <hr>
  <div class="row"><button class="btn" onmousedown="c('F')" onmouseup="c('S')" ontouchstart="c('F')" ontouchend="c('S')">Lên</button></div>
  <div class="row">
    <button class="btn" onmousedown="c('L')" onmouseup="c('S')" ontouchstart="c('L')" ontouchend="c('S')">Trái</button>
    <button class="btn btn-stop" onclick="c('S')">DỪNG</button>
    <button class="btn" onmousedown="c('R')" onmouseup="c('S')" ontouchstart="c('R')" ontouchend="c('S')">Phải</button>
  </div>
  <div class="row"><button class="btn" onmousedown="c('B')" onmouseup="c('S')" ontouchstart="c('B')" ontouchend="c('S')">Xuống</button></div>
</body></html>"""

# =====================  CHUONG TRINH CHINH  =====================
che_do = "AUTO"  
dem_gan = 0

try:
    print("San sang! Che do hien tai:", che_do)
    time.sleep(1)

    while True:
        # 1. Kiem tra Web Server co lenh moi khong
        try:
            conn, addr = s.accept()
            req = conn.recv(1024).decode('utf-8')
            
            # Neu App/Web hoi khoang cach, tra ve so roi ngat ket noi luon
            if '/?cmd=DIST' in req:
                conn.send('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n' + "{:.1f}".format(kc_truoc_do))
                conn.close()
                continue
                
            if '/?cmd=AUTO' in req: che_do = "AUTO"; dung()
            elif '/?cmd=MANUAL' in req: che_do = "MANUAL"; dung()
            elif che_do == "MANUAL":
                if '/?cmd=F' in req: chay_thang(TOC_DO_MAX)
                elif '/?cmd=B' in req: lui(0)       
                elif '/?cmd=L' in req: xoay_trai(0) 
                elif '/?cmd=R' in req: xoay_phai(0) 
                elif '/?cmd=S' in req: dung()
            
            # Tra ve giao dien HTML chinh neu khong phai lenh lay khoang cach
            conn.send('HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n' + HTML)
            conn.close()
        except OSError:
            pass # Khong co request tu dien thoai thi bo qua

        # 2. Xu ly di chuyen theo Che do
        if che_do == "AUTO":
            d = do_khoang_cach()
            v = tinh_toc_do(d)
            if DEBUG:
                print("d={:.1f}cm  v={}%".format(d, v)) # Van in ra may tinh binh thuong
                
            if v == 0:
                dem_gan += 1
                if dem_gan >= SO_LAN_XAC_NHAN:
                    xu_ly_vat_can()
                    dem_gan = 0
                else:
                    chay_thang(TOC_DO_MIN)
            else:
                dem_gan = 0
                chay_thang(v)
        else:
            # CHE DO MANUAL: Van doc cam bien de an toan va hien thi len man hinh
            d = do_khoang_cach()
            if d <= KC_DUNG and not dang_dung_im: 
                dung()
                
        time.sleep_ms(20)

except KeyboardInterrupt:
    dung()
finally:
    dung()