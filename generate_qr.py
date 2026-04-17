import qrcode

user_id = "student_001"

img = qrcode.make(user_id)
img.save("qr_login.png")

print("QR Code generated successfully")