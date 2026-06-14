# ⚡ NexAI – Modular AI-Powered Execution Platform
 
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-black)
![OpenAI](https://img.shields.io/badge/AI-OpenAI-green)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red)
![React](https://img.shields.io/badge/Frontend-React-lightblue)
![Status](https://img.shields.io/badge/Status-Active--Development-orange)
 
---
 
NexAI is a modular AI-powered platform designed to combine **conversational intelligence** with **real-world task execution**.
 
The platform separates **AI reasoning** from **operational workflows**, enabling scalable, domain-specific modules that integrate with enterprise systems.

## 📸 Demo
 
<table>
<tr>
<td width="50%">
 
<h3>🔎 Assist Module (Enterprise IT Support)</h3>
<p>This example demonstrates NexAI Assist providing support for Exchange Online scenarios.</p>
 
<img src="assets/assist-demo.png" width="100%" />
 
</td>
 
<td width="50%">
 
<h3>⚙️ Ops Module (Workflow Execution)</h3>
<p>This demonstrates NexAI Ops executing a complete service booking workflow.</p>
 
<img src="assets/ops-demo.png" width="100%" />
 
</td>
</tr>
</table>
 
---
 
## 🚀 Key Features
 
✅ Modular architecture (plug-and-play AI modules)
✅ Conversational AI (OpenAI integration)
✅ Workflow automation engine
✅ Enterprise-ready design (REST APIs, DB-backed)
✅ Real-world use cases (IT support, service operations)
✅ Clean separation of concerns (Assist vs Ops) 
 
---
 
## 🏗️ System Architecture
 
The system is designed using a modular backend architecture:

Each component is loosely coupled to allow future migration into microservices.
 
---
 
## 🔌 API Endpoints
 
### 🟢 `/chat`

Handles conversational interaction  

- Input: user message + session ID  

- Output: AI-generated response  
 
---
 
### 🟢 `/recommend`

Generates personalized recommendations  

- Input: user ID  

- Output: suggested items/services  
 
---
 
### 🟢 `/health`

Service health check endpoint  
 
---
 
## 🗄️ Data & Persistence
 
- SQLAlchemy ORM used for database abstraction  

- Interaction logging enables conversation tracking  

- Designed to support session-based context handling  

- Compatible with PostgreSQL and SQLite  
 
---
 
## 🧩 Core Components
 
| Component        | Responsibility |
|-----------------|--------------|
| **NLP Engine**   | Processes user input and generates responses |
| **API Layer**    | Handles HTTP requests and responses |
| **Recommender**  | Produces data-driven suggestions |
| **ORM Models**   | Manages database interaction |
| **Logging Layer**| Tracks conversational sessions |
 
---
 
## 🛠️ Tech Stack
 
**Backend:** Python, Flask  

**AI/NLP:** HuggingFace Transformers (DialoGPT)  

**Database:** PostgreSQL / SQLite  

**ORM:** SQLAlchemy  

**Environment Management:** python-dotenv  

**Communication:** REST APIs  
 
---
 
## 🔐 Security & Best Practices
 
- Sensitive data stored in `.env` (not committed to GitHub)  

- No hardcoded credentials in code  

- Clean separation of concerns across components  

- Structured for scalability and maintainability  
 
---
 
## ⚙️ Local Setup
 
1. Clone the repository  

2. Create a `.env` file:
 
3. Install dependencies:

4. Run the application:
 
---
 
## 🎯 Use Cases
 
- Customer service automation  

- Intelligent booking systems  

- Enterprise AI assistants  

- Backend-integrated chatbots  

- Recommendation-driven platforms  
 
---

🧠 Design Philosophy
> **NexAI is built on the principle that**:
AI should not just respond — it should act.
By separating reasoning from execution:
AI remains flexible and reusable
Workflows remain deterministic and auditable

---

🤝 Contributing
Contributions are welcome!
Fork the repo
Create a feature branch
Commit changes
Submit a Pull Request

---

## 📌 Status
 
✅ Fully functional modular AI platform 
🚧 Continuous refinement towards enterprise-scale readiness

---
 
## 💡 Vision
 
NexAI is designed as a:
 
> **Modular AI-powered execution platform**
 
capable of integrating intelligent decision-making directly into operational workflows across multiple domains.
 
The goal is to enable AI systems that not only provide insight, but actively participate in and automate real-world processes. 

---
 
## 👨‍💻 Author
 
**Paul Munhamo**  

Full Stack Software Engineer | AI Systems Developer
 