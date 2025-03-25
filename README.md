# 🔍 SwaggerScan

**SwaggerScan** is an automated API specification analyzer and testing tool that streamlines the process of parsing, storing, and testing Swagger/OpenAPI files. Whether you're a security tester, developer, or QA engineer, SwaggerScan gives you a full-featured dashboard to visualize endpoints, inspect parameters, and launch live or bulk testing of your API documentation.

---

## 📸 Screenshots

### 1. Upload Spec and Set API Target
![Select File and Host](https://github.com/fdzdev/SwaggerScan/blob/main/screenshots/select.png)

### 2. Successful Upload and Parsing
![Upload Success](https://github.com/fdzdev/SwaggerScan/blob/main/screenshots/success.png)

### 3. Explore & Test Endpoints
![Main Dashboard](https://github.com/fdzdev/SwaggerScan/blob/main/screenshots/main.png)

---


## ⚙️ Features

- ✅ Upload Swagger/OpenAPI specs (`.json`, `.yaml`)
- 📁 Store parsed endpoints in PostgreSQL with SQLAlchemy
- 🧠 Auto-detect path/query/body parameters
- 🖥️ Dashboard for exploring and testing endpoints
- 🧪 Live single and massive endpoint testing
- 📊 Grouped endpoint display and test configuration panel

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL (e.g., via Docker or local setup)
- `pip` installed

### Clone the Repo

```bash
git clone https://github.com/fdzdev/SwaggerScan.git
cd SwaggerScan
```
Install Dependencies
```
pip install -r requirements.txt
```
Run the Server
```
python app.py

```
Navigate to:
```
http://localhost:5000

```
## 🧪 How to Use

1. **Upload** your Swagger/OpenAPI specification file (`.json` or `.yaml`) on the homepage.
2. **Enter** the API host or base URL (e.g., `https://api.example.com`).
3. **Click** the **Upload** button. The system will automatically:
   - Parse the file
   - Extract and store all available endpoints
   - Analyze parameters (path, query, body)
4. **Explore and Test**:
   - Use the interactive dashboard to send custom requests
   - Filter and group endpoints
   - Run massive tests across multiple endpoints with real-time feedback

---

## 🧰 Tech Stack

- **Backend:** Flask, SQLAlchemy  
- **Frontend:** Jinja2 templates, HTML, CSS (Apple-style UI)  
- **Database:** PostgreSQL  
- **Parsers:** YAML, JSON  

