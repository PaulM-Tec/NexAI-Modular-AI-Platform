FROM python:3.11-slim
WORKDIR /app
 
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy application files
COPY app.py ./
COPY nlp_engine.py ./
COPY orm_models.py ./
 
# Expose port
EXPOSE 5000
 
# Environment variables (can be overridden at runtime)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
 
CMD ["python", "app.py"]