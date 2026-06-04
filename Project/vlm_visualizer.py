import re
from PIL import Image, ImageDraw

def process_vlm_grounding(image_path, vlm_output_string, output_path="output.jpg"):
    """
    VLM çıktısındaki <box> koordinatlarını ayrıştırır, orijinal resim boyutuna göre
    ölçeklendirir ve köşelere belirgin kırmızı noktalar çizerek kaydeder.
    """
    try:
        # 1. Resmi aç ve boyutlarını al
        img = Image.open(image_path).convert("RGB")
        width, height = img.size
        draw = ImageDraw.Draw(img)

        # 2. Regex ile koordinatları ayrıştır: <box>(x1,y1),(x2,y2)</box>
        # Bu pattern (x1, y1), (x2, y2) formatındaki sayıları yakalar
        bbox_pattern = r"<box>\((\d+),(\d+)\),\((\d+),(\d+)\)</box>"
        match = re.search(bbox_pattern, vlm_output_string)

        if not match:
            print(f"HATA: VLM çıktısında geçerli bir <box> formatı bulunamadı! Çıktı: {vlm_output_string}")
            return False

        # Koordinatları integer olarak al (VLM 0-1000 arası normalize değer verir)
        x1_norm, y1_norm, x2_norm, y2_norm = map(int, match.groups())

        # 3. Ölçeklendirme (Scaling): 0-1000 -> Gerçek Piksel
        # Formül: (Normalize_X / 1000) * Resim_Genişliği
        real_x1 = int((x1_norm / 1000) * width)
        real_y1 = int((y1_norm / 1000) * height)
        real_x2 = int((x2_norm / 1000) * width)
        real_y2 = int((y2_norm / 1000) * height)

        print(f"Tespit Edildi: ({real_x1}, {real_y1}) ve ({real_x2}, {real_y2})")

        # 4. Çizim (Drawing)
        # İnce bir dikdörtgen çiz (isteğe bağlı)
        draw.rectangle([real_x1, real_y1, real_x2, real_y2], outline="red", width=2)

        # Köşelere belirgin kırmızı noktalar (dolu daireler) çiz
        point_radius = 8  # Noktaların büyüklüğü
        
        # Sol üst nokta (x1, y1)
        draw.ellipse([real_x1 - point_radius, real_y1 - point_radius, 
                      real_x1 + point_radius, real_y1 + point_radius], fill="red")
        
        # Sağ alt nokta (x2, y2)
        draw.ellipse([real_x2 - point_radius, real_y2 - point_radius, 
                      real_x2 + point_radius, real_y2 + point_radius], fill="red")

        # 5. Kaydet
        img.save(output_path)
        print(f"Başarılı: İşlenmiş görsel '{output_path}' olarak kaydedildi.")
        return True

    except FileNotFoundError:
        print(f"HATA: '{image_path}' dosyası bulunamadı.")
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")
    return False

# Örnek Kullanım:
if __name__ == "__main__":
    test_image = "input.jpg"  # Test etmek istediğiniz resmin yolu
    test_output = "<box>(458,306),(790,999)</box>" # Örnek VLM çıktısı
    
    # Not: Çalıştırmak için dizinde 'input.jpg' olmalıdır.
    process_vlm_grounding(test_image, test_output)
