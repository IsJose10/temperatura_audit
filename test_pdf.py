import urllib.request
import urllib.parse
import json

# ponytail: simple PDF verification script using standard library urllib with JSON
def test_pdf():
    try:
        # Login to get token (using JSON)
        login_url = "http://127.0.0.1:8000/api/auth/login"
        payload = json.dumps({
            "username": "admin",
            "password": "admin123"
        }).encode('utf-8')
        
        req = urllib.request.Request(login_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req) as response:
            login_res = json.loads(response.read().decode())
            token = login_res["access_token"]
            
        # Download PDF
        pdf_url = "http://127.0.0.1:8000/api/verificaciones/1/pdf"
        pdf_req = urllib.request.Request(pdf_url, method="GET")
        pdf_req.add_header("Authorization", f"Bearer {token}")
        
        with urllib.request.urlopen(pdf_req) as pdf_response:
            pdf_data = pdf_response.read()
            if pdf_data.startswith(b"%PDF"):
                print("[OK] PDF generado correctamente y comienza con cabecera %PDF")
                # Save the PDF to verification
                with open("FR-CAL-037_test.pdf", "wb") as f:
                    f.write(pdf_data)
                print("[+] PDF guardado como FR-CAL-037_test.pdf")
            else:
                print(f"[ERROR] La respuesta no es un PDF válido. Empieza con: {pdf_data[:20]}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_pdf()
